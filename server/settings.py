import re
import unicodedata
from pathlib import Path

from pydantic import validator

from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
)


class RepositorySettings(BaseSettingsModel):
    url: str = SettingsField(default="", description="Repository URL.", title="URL")
    tag: str = SettingsField(
        default="", description="Repository tag. Leave empty for latest."
    )
    name: str = SettingsField(default="", description="Repository name.", title="Name")

    def __init__(self, **data):
        super().__init__(**data)
        self.name = Path(self.url).stem


class VirtualEnvSettings(BaseSettingsModel):
    uv_path: str = SettingsField(
        default="",
        title="UV Executable Path",
        description="Must be the explicit path to the UV executable.",
    )
    git_path: str = SettingsField(
        default="",
        title="Git Executable Path",
        description="Optional override to git executable. Must be the explicit path.",
    )
    python_version: str = SettingsField(
        default="3.12",
        title="Python Version",
        description="Python version to use for the virtual environment.",
    )
    use_torch_nightly: bool = SettingsField(
        default=True,
        title="Use PyTorch Nightly",
        description="Use the nightly version of PyTorch.",
    )
    force_torch_version: bool = SettingsField(
        default=False,
        title="Force PyTorch Version",
        description="Force a specific version of PyTorch.",
    )
    torch_version: str = SettingsField(
        default="",
        title="PyTorch Version",
        description="Specify the PyTorch version to use if 'Force PyTorch Version' is enabled.",
    )


class CustomNodeSettings(RepositorySettings):
    extra_dependencies: list[str] = SettingsField(
        default_factory=list,
        description="Extra python dependencies to install.",
        title="Extra Dependencies",
    )


class ComfyUIRepositorySettings(BaseSettingsModel):
    base_url: str = SettingsField(
        default="",
        title="Repository URL",
        description="Where to clone the ComfyUI repository from.",
    )
    install_sageattention: bool = SettingsField(
        default=True,
        title="Install SageAttention",
        description="Install the SageAttention plugin for ComfyUI.",
    )
    plugins: list[CustomNodeSettings] = SettingsField(
        default_factory=list[CustomNodeSettings],
        description="Repository Settings for Extra Nodes.",
    )


class ComfyUICachingSettings(BaseSettingsModel):
    enabled: bool = SettingsField(
        default=False,
    )
    cache_dir_template: str = SettingsField(
        default="",
        title="Cache Directory Template",
        description="Where to load dependencies from.",
    )


def profile_directory_name(profile_name: str) -> str:
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ẞ": "Ss",
    }
    for source, replacement in replacements.items():
        profile_name = profile_name.replace(source, replacement)

    normalized = unicodedata.normalize("NFKD", profile_name)
    ascii_name = "".join(
        character
        for character in normalized
        if ord(character) < 128 and not unicodedata.combining(character)
    )
    words = re.findall(r"[a-zA-Z0-9]+", ascii_name)
    directory_name = "".join(
        word[0].upper() + word[1:].lower() for word in words
    )
    if not directory_name:
        raise ValueError("Profile name must contain letters or numbers.")
    if len(directory_name) > 255:
        raise ValueError("Profile installation directory name exceeds 255 characters.")

    reserved_names = {"CON", "PRN", "AUX", "NUL"}
    reserved_names.update(f"COM{number}" for number in range(1, 10))
    reserved_names.update(f"LPT{number}" for number in range(1, 10))
    if directory_name.upper() in reserved_names:
        raise ValueError(
            f"Profile name creates a reserved Windows directory: {directory_name}"
        )

    return directory_name


class ComfyUIProfileSettings(BaseSettingsModel):
    name: str = SettingsField(default="", title="Profile Name")
    description: str = SettingsField(default="", title="Description")
    comfyui_version: str = SettingsField(
        default="",
        title="ComfyUI Version",
        description="Git branch, tag, or commit. Leave empty to use the repository default branch.",
    )
    venv: VirtualEnvSettings = SettingsField(
        default_factory=VirtualEnvSettings,
        title="Virtual Environment Settings",
    )
    repositories: ComfyUIRepositorySettings = SettingsField(
        default_factory=ComfyUIRepositorySettings,
        title="Repository Settings",
    )
    caching: ComfyUICachingSettings = SettingsField(
        default_factory=ComfyUICachingSettings,
        title="Caching Settings",
    )

    @validator("name")
    def validate_name(cls, name):
        if not name.strip():
            raise ValueError("Profile name cannot be empty.")
        if name.endswith((".", " ")):
            raise ValueError("Profile name cannot end with a dot or space.")
        if any(ord(character) < 32 or character in '<>:"/\\|?*' for character in name):
            raise ValueError("Profile name contains characters that are invalid on Windows.")
        profile_directory_name(name)
        return name


class AddonSettings(BaseSettingsModel):
    """ComfyUI addon settings."""

    root_template: str = SettingsField(
        default="{root[work]}/{project[name]}/comfyui",
        title="Root Template",
        description=(
            "Parent directory for profile installations. Use {userprofile} to "
            "reference the user profile directory."
        ),
    )
    profiles: list[ComfyUIProfileSettings] = SettingsField(
        default_factory=list,
        title="Profiles",
    )

    @validator("profiles")
    def validate_profile_directories(cls, profiles):
        directory_names = {}
        for profile in profiles:
            directory_name = profile_directory_name(profile.name)
            if directory_name.casefold() in directory_names:
                previous_name = directory_names[directory_name.casefold()]
                raise ValueError(
                    f"Profile names '{previous_name}' and '{profile.name}' "
                    f"use the same installation directory '{directory_name}'."
                )
            directory_names[directory_name.casefold()] = profile.name
        return profiles


DEFAULT_VALUES = {
    "root_template": "{root[work]}/{project[name]}/comfyui",
    "profiles": [
        {
            "name": "Default",
            "repositories": {
                "base_url": "https://github.com/comfyanonymous/ComfyUI.git",
                "plugins": [
                    {
                        "url": "https://github.com/ltdrdata/ComfyUI-Manager.git",
                        "extra_dependencies": ["pip"],
                    }
                ],
            },
        }
    ],
}
