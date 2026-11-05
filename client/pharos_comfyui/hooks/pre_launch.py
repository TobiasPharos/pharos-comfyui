import os
import sys
import ayon_api
import subprocess
import traceback
import json
import logging
from copy import deepcopy
from pathlib import Path
from qtpy import QtWidgets, QtCore

from ayon_applications import (
    PreLaunchHook,
    LaunchTypes,
)
from ayon_core.lib import StringTemplate
from ayon_core.pipeline import Anatomy
from ayon_core.pipeline.template_data import get_template_data
from ayon_core.lib.local_settings import get_ayon_user_entity


from pharos_comfyui import ADDON_ROOT, ADDON_NAME, ADDON_VERSION
from pharos_comfyui.profile import (
    resolve_profile_directory,
    validate_existing_profile_directory,
)

LOG_LEVEL = logging.INFO
logging.basicConfig(force=True, stream=sys.stdout, level=LOG_LEVEL)
log = logging.getLogger(__name__)

class EmptyProgressCallback:
    def __call__(self, message):
        log.info(message)

EMPTY_PROGRESS_CALLBACK = EmptyProgressCallback()

class SpinnerDialog(QtWidgets.QDialog):
    def __init__(self, message="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Please wait")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(message)
        self.spinner = QtWidgets.QProgressBar(self)
        self.spinner.setRange(0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.spinner)
        self.setLayout(layout)
        self.setFixedSize(300, 80)

    def set_message(self, message):
        self.label.setText(message)
        QtWidgets.QApplication.processEvents()

class Worker(QtCore.QThread):
    finished = QtCore.Signal()
    progress = QtCore.Signal(str)
    failed = QtCore.Signal(object)

    def __init__(self, func):
        super().__init__()
        self.func = func
        self.error = None

    def run(self):
        try:
            self.func(progress_callback=self.progress.emit)
        except Exception as exc:
            self.error = (exc, traceback.format_exc())
            self.failed.emit(self.error)
        finally:
            self.finished.emit()

def ask_update_comfyui(app) -> bool:
    """Show a dialog asking whether to update ComfyUI. Returns True if the user wants to update."""
    result = QtWidgets.QMessageBox.question(
        None,
        "Update ComfyUI",
        "Do you want to update ComfyUI and its plugins?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes,
    )
    return result == QtWidgets.QMessageBox.Yes


def run_with_spinner(func, app, msg=""):

    spinner = SpinnerDialog(msg)
    worker = Worker(func)
    runtime_error = None

    aborted = False
    def abort():
        nonlocal aborted
        aborted = True
        worker.terminate()
        worker.wait()
        app.quit()

    def on_failed(error_data):
        nonlocal runtime_error
        runtime_error = error_data
        exc, tb = error_data
        spinner.set_message("Pre-launch setup failed. Check logs for details.")
        log.error(f"Pre-launch worker failed: {exc}\n{tb}")

    worker.finished.connect(spinner.accept)
    worker.progress.connect(spinner.set_message)
    worker.failed.connect(on_failed)
    spinner.rejected.connect(abort)

    worker.start()
    spinner.exec_()
    worker.wait()

    if runtime_error:
        exc, tb = runtime_error
        raise RuntimeError(f"Pre-launch setup failed: {exc}\n{tb}") from exc

    return not aborted


class PharosComfyUIPreLaunchHook(PreLaunchHook):
    """Inject cli arguments to shell point at launch script."""

    hosts = {"pharos_comfyui", "comfyui"}
    launch_types = {LaunchTypes.local}
    order = 15

    def execute(self):
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(sys.argv)
        anatomy = Anatomy(project_name=self.data["project_name"])
        self.tmpl_data = get_template_data(self.data["project_entity"])
        self.tmpl_data.update({"root": anatomy.roots})
        if not self.tmpl_data.get("userprofile"):
            self.tmpl_data.update({"userprofile": os.path.expanduser("~")})
        self.addon_settings = ayon_api.get_addon_project_settings(
            ADDON_NAME, ADDON_VERSION, self.tmpl_data["project"]["name"]
        )

        profiles = self.addon_settings.get("profiles", [])
        if not profiles:
            raise RuntimeError("No ComfyUI profiles are configured in the addon settings.")
        application_label = self.application.label
        selected_profile = next(
            (profile for profile in profiles if profile["name"] == application_label),
            None,
        )
        if selected_profile is None:
            available_profiles = ", ".join(profile["name"] for profile in profiles)
            message = (
                f"No ComfyUI profile matches application label '{application_label}'.\n\n"
                f"Available profiles: {available_profiles}\n\n"
                "Set the variant Label under Additional Applications > comfyui "
                "to exactly match a profile Name in the addon settings."
            )
            QtWidgets.QMessageBox.critical(None, "ComfyUI Profile Not Found", message)
            raise RuntimeError(message)
        self.profile_settings = deepcopy(selected_profile)

        if not ask_update_comfyui(app):
            log.info("User chose not to update ComfyUI. Skipping pre-launch setup.")
            return

        if not run_with_spinner(self.pre_launch_setup, app):
            raise RuntimeError("Pre-launch setup was aborted by user.")
        self.run_server()

    def pre_launch_setup(self, progress_callback=EMPTY_PROGRESS_CALLBACK):
        self.pre_process(progress_callback)
        self.clone_repositories(progress_callback)

    def pre_process(self, progress_callback=EMPTY_PROGRESS_CALLBACK):
        progress_callback("Pre-processing...")

        profile_settings = self.profile_settings
        repository_settings = profile_settings["repositories"]
        root_template = StringTemplate(self.addon_settings["root_template"])
        root_path = Path(root_template.format_strict(self.tmpl_data))
        self.comfy_root = resolve_profile_directory(
            root_path,
            profile_settings["name"],
        )
        validate_existing_profile_directory(
            self.comfy_root,
            repository_settings["base_url"],
        )
        log.debug(f"{self.comfy_root = }")

        # Addon plugins
        self.plugins = deepcopy(repository_settings["plugins"])

        # User plugins
        user = get_ayon_user_entity()
        user_plugins_str = user["attrib"].get("userComfyUiPlugins", "")
        user_plugins = []
        if user_plugins_str:
            try:
                user_plugins = json.loads(user_plugins_str)
            except (json.JSONDecodeError, ValueError):
                raise RuntimeError(f"Invalid JSON string for custom user ComfyUi plugins: {user_plugins_str}")

        for user_plugin in user_plugins:
            if not user_plugin.get("url"):
                log.warning(f"Skipping user plugin with missing URL: {user_plugin}")
                continue
            if user_plugin.get("url") not in [p["url"] for p in self.plugins]:
                new_user_plugin = {
                    "url": user_plugin["url"],
                    "tag": user_plugin.get("tag", ""),
                    "name": user_plugin.get("name", ""),
                    "extra_dependencies": user_plugin.get("extra_dependencies", []),
                }
                self.plugins.append(new_user_plugin)

        self.extra_dependencies = set()
        for plugin in self.plugins:
            if plugin.get("extra_dependencies"):
                self.extra_dependencies.update(plugin["extra_dependencies"])

        self.cache_dir = None
        if profile_settings["caching"].get("enabled"):
            cache_tmpl = profile_settings["caching"]["cache_dir_template"]
            self.cache_dir = StringTemplate(cache_tmpl).format_strict(self.tmpl_data)

        # get installed CUDA version and build correct pypi index url
        try:
            smi_version_details = subprocess.check_output(
                ["nvidia-smi", "--version"], text=True
            ).strip()
        except Exception as e:
            raise RuntimeError(
                "Failed to execute `nvidia-smi`. Ensure NVIDIA drivers are installed and on PATH."
            ) from e

        cuda_version = None
        version_lines = ["CUDA UMD version", "CUDA version"]
        for version_line in version_lines:
            for line in smi_version_details.splitlines():
                if version_line in line and "Deprecated" not in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        cuda_version = parts[1].strip()
                    break
            if cuda_version:
                break
        if not cuda_version:
            raise RuntimeError("CUDA version could not be determined from `nvidia-smi` output.")

        # Known mappings; add new ones here as they become available
        # TODO: Turn this into Ayon settings
        pypi_url_map = {
            "11.8": {
                "stable": "https://download.pytorch.org/whl/cu118",
                "nightly": None,
            },
            "12.6": {
                "stable": "https://download.pytorch.org/whl/cu126",
                "nightly": "https://download.pytorch.org/whl/nightly/cu126",
            },
            "12.8": {
                "stable": "https://download.pytorch.org/whl/cu128",
                "nightly": "https://download.pytorch.org/whl/nightly/cu128",
            },
            "12.9": {
                "stable": "https://download.pytorch.org/whl/cu129",
                "nightly": "https://download.pytorch.org/whl/nightly/cu129",
            },
            "13.0": {
                "stable": "https://download.pytorch.org/whl/cu130",
                "nightly": "https://download.pytorch.org/whl/nightly/cu130",
            },
        }

        # choose channel
        venv_settings = profile_settings["venv"]
        use_nightly = bool(venv_settings["use_torch_nightly"])
        channel = "nightly" if use_nightly else "stable"

        def _ver_tuple(s: str):
            try:
                return tuple(int(x) for x in s.split("."))
            except ValueError as err:
                raise ValueError(f"Invalid version string: {s}") from err

        # exact hit if available (and URL exists)
        if cuda_version in pypi_url_map and pypi_url_map[cuda_version][channel]:
            self.pypi_url = pypi_url_map[cuda_version][channel]
            self.used_cuda_version = cuda_version
        else:
            # graceful fallback: pick highest supported <= installed CUDA
            supported = sorted(pypi_url_map.keys(), key=_ver_tuple)
            lower_or_equal = [k for k in supported if _ver_tuple(k) <= _ver_tuple(cuda_version)]
            if lower_or_equal:
                fallback = lower_or_equal[-1]
                log.warning(
                    f"Unknown CUDA {cuda_version}; falling back to {fallback} ({channel}) for PyTorch wheels."
                )
                self.pypi_url = pypi_url_map[fallback][channel]
                self.used_cuda_version = fallback
            else:
                log.warning(
                    f"No suitable CUDA mapping for {cuda_version}; proceeding without custom PyTorch index."
                )
                self.pypi_url = None
                self.used_cuda_version = None

        log.info(f"Using PyPI URL: {self.pypi_url}")

        self.force_torch_version = bool(venv_settings["force_torch_version"])
        torch_version = venv_settings["torch_version"]
        if self.force_torch_version:
            torch_tuple = _ver_tuple(torch_version)
            if len(torch_tuple) == 2:
                self.torch_version = f"\">={torch_tuple[0]}.{torch_tuple[1]},<{torch_tuple[0]}.{torch_tuple[1]+1}\""
            else:
                self.torch_version = f"\"=={torch_version}\""

        self.py_version: str = venv_settings["python_version"]
        if not self.py_version.startswith("3.12"):
            log.warning(f"Unsupported Python version {self.py_version}. Only Python 3.12 is supported.")
        self.uv_path: str = venv_settings["uv_path"]
        self.install_sageattention: bool = repository_settings["install_sageattention"]

    def clone_repositories(self, progress_callback=EMPTY_PROGRESS_CALLBACK):
        git_path = self.profile_settings["venv"]["git_path"]
        if Path(git_path).exists():
            if os.getenv("GIT_PYTHON_GIT_EXECUTABLE"):
                log.warning(
                    f"Overriding existing GIT_PYTHON_GIT_EXECUTABLE which is already set to {os.getenv('GIT_PYTHON_GIT_EXECUTABLE')}"
                )
            os.environ["GIT_PYTHON_GIT_EXECUTABLE"] = git_path
        else:
            log.warning(f"Git executable not found at {git_path}")

        import git

        def git_clone(url: str, dest: Path, ref: str = "") -> git.Repo:
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                log.info(f"Cloning {url} to {dest}")
                repo = git.Repo.clone_from(url, dest)
            else:
                repo = git.Repo(dest)

            repo.git.fetch(tags=True)
            if repo.is_dirty(untracked_files=True):
                log.info(f"Stashing uncommitted changes in {repo}")
                repo.git.stash("save", "--include-untracked")

            if ref:
                log.info(f"Checking out ref {ref} for {repo}")
                repo.git.checkout(ref)
            else:
                repo.git.remote("set-head", "origin", "--auto")
                default_ref = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
                prefix = "refs/remotes/origin/"
                if not default_ref.startswith(prefix):
                    raise RuntimeError(f"Invalid default branch reference for {url}.")
                default_branch = default_ref.removeprefix(prefix)
                if default_branch in repo.heads:
                    repo.heads[default_branch].checkout()
                else:
                    repo.git.checkout("-b", default_branch, default_ref)
                repo.remotes.origin.pull(default_branch)
            return repo

        repository_settings = self.profile_settings["repositories"]
        git_clone(
            url=repository_settings["base_url"],
            dest=self.comfy_root,
            ref=self.profile_settings["comfyui_version"],
        )

        # clone custom nodes
        for plugin in self.plugins:
            plugin_name = Path(plugin["url"]).stem
            progress_callback(f"Setting up Plugin: {plugin_name}")
            plugin_root = self.comfy_root / "custom_nodes" / plugin_name
            git_clone(
                url=plugin["url"],
                dest=plugin_root,
                ref=plugin["tag"],
            )

    def run_server(self):
        launch_script = ADDON_ROOT / "tools" / "install_and_run_server_venv.ps1"

        _cmd: list = [
            launch_script.as_posix(),
        ]

        launch_args = []
        if self.uv_path:
            launch_args.append("-uvPath")
            launch_args.append(self.uv_path)
        if self.plugins:
            launch_args.append("-plugins")
            plugin_names = [Path(plugin["url"]).stem for plugin in self.plugins]
            launch_args.append(",".join(plugin_names))
        if self.extra_dependencies:
            launch_args.append("-extraDependencies")
            launch_args.append(",".join(self.extra_dependencies))
        if self.cache_dir:
            launch_args.append("-cacheDir")
            launch_args.append(self.cache_dir)
        if self.pypi_url:
            launch_args.append("-pypiUrl")
            launch_args.append(self.pypi_url)
        if self.py_version:
            launch_args.append("-pythonVersion")
            launch_args.append(self.py_version)
        if self.used_cuda_version:
            launch_args.append("-cudaVersion")
            launch_args.append(self.used_cuda_version)
        if self.force_torch_version:
            launch_args.append("-forcedTorchVersion")
            launch_args.append(self.torch_version)

        _cmd.extend(launch_args)
        cmd = " ".join([str(arg) for arg in _cmd])
        launch_args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", cmd,
        ]
        log.info(f"{cmd = }")
        env = self.data["env"].copy()
        if "PYTHONPATH" in env:
            del env["PYTHONPATH"]

        popen_kwargs = {
            "stdout": None,
            "stderr": None,
            "cwd": str(self.comfy_root),
            "env": env,
            "creationflags": subprocess.CREATE_NEW_CONSOLE,
        }

        self.launch_context.launch_args = launch_args
        self.launch_context.kwargs = popen_kwargs

        result = subprocess.run(launch_args, **popen_kwargs)
        log.info(f"ComfyUI launcher finished with return code: {result.returncode}")
        if result.returncode != 0:
            raise RuntimeError(
                f"ComfyUI launcher exited with non-zero return code: {result.returncode}"
            )

        if self.install_sageattention:
            launch_script = ADDON_ROOT / "tools" / "SageAttention-Multi.bat"
            _cmd = [launch_script.as_posix()]
            launch_args = []
            if self.cache_dir:
                launch_args.append("1")
            _cmd.extend(launch_args)
            cmd = " ".join([str(arg) for arg in _cmd])
            log.info("SageAttention installation.")

            result = subprocess.run(cmd, **popen_kwargs)
            log.info(f"SageAttention installation finished with return code: {result.returncode}")
            if result.returncode != 0:
                raise RuntimeError(
                    f"SageAttention installation exited with non-zero return code: {result.returncode}"
                )
