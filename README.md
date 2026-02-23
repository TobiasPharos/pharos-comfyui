# ayon-comfyui
An AYON Addon for launching ComfyUI locally via TrayLauncher.

Clones `ComfyUI` from offical GitHub repo and comes with `ComfyUI-Manager` preconfigured.
`uv` is used for installing all required dependencies and environment solving in a separate terminal session. This session is used to launch a local `ComfyUI` server.

> ⚠️ This addon is Windows-only and depends on `uv` and `git` to be executable on your system.
> If `uv` is not found it will run the installation script from https://astral.sh/uv/install.ps1 for the current user.

## Plugin and Dependency Management
The addon automatically manages plugins and their dependencies to maintain a clean and reproducible ComfyUI environment.
This is achieved by tracking the currently active venv against an additional temporary `.baseline-venv` containing only core ComfyUI dependencies.
Any folder found in the `custom_nodes` directory that is not in the configured plugins list are automatically deleted.

> ⚠️ The cleanup process is automatic and cannot be disabled. Ensure your plugin configuration is correct before launching to avoid unintended plugin removal.

## Setup
This addon requires an "Additional Application" in AYON's application settings to be created.
Its `name` and `host_name` must be `comfyui`.
Use the variant names to specify an available ComfyUI branch or tag. Finally, set the windows executable path to `powershell.exe`.
This is to launch beforementioned separate terminal session. I know, it's a bit hacky.


### Settings
Use Extra Flags to add any custom launch flags to the webserver, e.g. `--use-cpu`.

#### Virtual Environment Settings
Configure the python version to use and whether to pull nightly PyTorch builds.
You can also set a specific path to `uv` if it's not in `$PATH`.

#### Repository Settings
Configure where to pull ComfyUI sources, its target directory and additional plugins.
You can specify extra dependencies to be installed as some custom nodes don't maintain a `requirements.txt`. All configured plugin dependencies will be collected and installed in a single `uv pip install`.

#### Extra Models
Toggle to define a source directory to all your custom models to consider them during launch.
All found folders will be added to the ComfyUI repo directory's `extra_model_paths.yaml`. When using `copy_to_base` the directories won't be added to the config yaml but copied into the repo base's `models/{model_type}`.

> ⚠️ `copy_to_base` currently just blindly copies every file found in the directory. No filtering for files yet.

#### Caching Settings
Configure whether `uv` should use a specific cache location to read and write to. Currently only configures `UV_CACHE_DIR` during the launch script but it seems to do the job.
Could be used in air-gapped scenarios.

