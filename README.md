# pharos-comfyui
An AYON Addon to set up ComfyUI to be used with https://github.com/ynput/ayon-comfyui.

Clones `ComfyUI` from offical GitHub repo and sets up configurable custom nodes.
`uv` is used for installing all required dependencies and environment solving in a separate terminal session. This session is used to launch a local `ComfyUI` server.

> ⚠️ This addon is Windows-only and depends on `uv` and `git` to be executable on your system.
> uv and git executables can be configured in the addon's settings.
> If `uv` is not found it will run the installation script from https://astral.sh/uv/install.ps1 for the current user.

## Plugin and Dependency Management
The addon automatically manages plugins and their dependencies to maintain a clean and reproducible ComfyUI environment.
This is achieved by tracking the currently active venv against an additional temporary `.baseline-venv` containing only core ComfyUI dependencies.
Any folder found in the `custom_nodes` directory that is not in the configured plugins list are automatically deleted.

> ⚠️ The User may skip the entire setup. Otherwise the cleanup process is automatic and cannot be disabled. Ensure your plugin configuration is correct before launching to avoid unintended plugin removal.

## Setup
This addon requires an "Additional Application" in AYON's application settings to be created.
Its `name` and `host_name` must be `comfyui`.
The application variant no longer selects the ComfyUI version. Set the windows executable path to `powershell.exe`.
This is to launch beforementioned separate terminal session. I know, it's a bit hacky.

## Profiles
Configure a global **Root Template** and one or more profiles in the addon settings. The root template is the parent directory for all profile installations. Each profile has a name, description, ComfyUI Git ref, and its own virtual environment, repository/plugin, and caching settings.

The profile picker appears on every startup. Select a profile and use its info button to view the description. Canceling the picker cancels launch. The existing update/setup prompt appears after profile selection; choosing not to update continues to skip setup.

The ComfyUI Version field accepts a branch, tag, or commit. Leave it empty to use the ComfyUI repository's default branch. The application variant is ignored for version selection.

Profile names remain unchanged in the picker. Installation directory names use Pascal-Case, transliterate German umlauts (`ä` to `ae`, `ö` to `oe`, `ü` to `ue`, `ß` to `ss`), and remove punctuation and other special characters. For example, `Künstler Größe!` becomes `KuenstlerGroesse`. The server rejects profiles that resolve to the same installation directory. An existing ComfyUI checkout with the configured repository origin is reused; an unrelated directory at that path blocks setup.

Existing flat addon settings are not migrated automatically. Recreate them in the new profile settings and enter any former application-variant version pin in the profile's ComfyUI Version field. Old checkout directories are left untouched.

You may also add a custom User Attribute called userComfyUiPlugins. It allows you to set up user-specific ComfyUi Environments. The attribute is a list of dictionaries. Each dict requires at least a key "url" with the github URL of the plugin. Optionally it may also contain the keys "tag" (checkout specific tag), "name" (defaults to the name of the repo if not set), "extra_dependencies" (to install dependencies, that are not in the requirements.txt of the repo) - basically the structure follows the same structure as the Plugins settings in the main addon settings.
```python
[{"url": "https://github.com/....git"}, {"url": "https://github.com/....git", "tag": "v0.3", "name": "Special Plugin", "extra_dependencies": "example"}]
```

#### Profile Settings
Configure the Python version, PyTorch channel/version, `uv` and `git` paths, ComfyUI repository, SageAttention option, and custom nodes independently for each profile. The profile's ComfyUI checkout, virtual environment, and plugins are isolated in its installation directory.
You can specify extra dependencies to be installed as some custom nodes don't maintain a `requirements.txt`. All configured plugin dependencies will be collected and installed in a single `uv pip install`.

Configure whether `uv` should use a specific cache location to read and write to. Currently only configures `UV_CACHE_DIR` during the launch script but it seems to do the job.
Could be used in air-gapped scenarios.

