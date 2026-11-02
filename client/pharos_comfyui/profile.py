import re
import unicodedata
from pathlib import Path


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


def resolve_profile_directory(root: Path, profile_name: str) -> Path:
    root = root.resolve()
    profile_directory = (root / profile_directory_name(profile_name)).resolve()
    if profile_directory.parent != root:
        raise ValueError("Profile installation directory must be inside the configured root.")
    return profile_directory


def validate_existing_profile_directory(directory: Path, repository_url: str) -> None:
    if not directory.exists():
        return
    if not directory.is_dir():
        raise ValueError(f"Profile installation path is not a directory: {directory}")

    import git

    try:
        repository = git.Repo(directory, search_parent_directories=False)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
        raise ValueError(
            f"Profile installation path already exists and is not a ComfyUI checkout: {directory}"
        ) from exc

    if not repository.working_tree_dir:
        raise ValueError(f"Profile installation path is not a worktree: {directory}")
    repository_root = Path(repository.working_tree_dir).resolve()
    if repository_root != directory.resolve():
        raise ValueError(f"Profile installation path is not the Git checkout root: {directory}")

    origin_urls = [remote.url for remote in repository.remotes if remote.name == "origin"]

    def normalize_url(url):
        return url.strip().rstrip("/").removesuffix(".git").casefold()

    if not any(normalize_url(url) == normalize_url(repository_url) for url in origin_urls):
        raise ValueError(
            f"Profile installation path belongs to a different repository: {directory}"
        )
