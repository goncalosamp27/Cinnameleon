"""Round-trip editing helpers for Cinnameleon configuration files."""

from __future__ import annotations

import copy
import os
import re
import shutil
import stat
import unicodedata
from collections.abc import Mapping, MutableMapping
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from cinnameleon.models import (
    Configuration,
    EffectiveProfile,
)
from cinnameleon.resolver import resolve_profile


class ConfigEditError(RuntimeError):
    """Raised when a configuration file cannot be safely edited."""


VARIANT_FIELDS = (
    ("gtk_theme", "gtk_theme"),
    ("cinnamon_theme", "cinnamon_theme"),
    ("window_borders", "window_borders"),
    ("icon_theme", "icon_theme"),
    ("cursor_theme", "cursor_theme"),
)

FONT_FIELDS = (
    ("interface", "interface"),
    ("document", "document"),
    ("monospace", "monospace"),
    ("window_title", "window_title"),
)


def _yaml() -> YAML:
    yaml = YAML(typ="rt")

    yaml.preserve_quotes = True
    yaml.width = 100

    yaml.indent(
        mapping=2,
        sequence=4,
        offset=2,
    )

    return yaml


def _load_document(
    path: Path,
) -> tuple[
    YAML,
    MutableMapping[str, object],
]:
    yaml = _yaml()

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as stream:
            document = yaml.load(stream)

    except OSError as error:
        raise ConfigEditError(
            f"Could not read configuration: {error}"
        ) from error

    except Exception as error:
        raise ConfigEditError(
            f"Could not parse configuration: {error}"
        ) from error

    if not isinstance(
        document,
        MutableMapping,
    ):
        raise ConfigEditError(
            "The YAML root must be a mapping."
        )

    return yaml, document


def _profiles_list(
    document: MutableMapping[str, object],
) -> list:
    profiles = document.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        list,
    ):
        raise ConfigEditError(
            "The YAML profiles field must be a list."
        )

    return profiles


def _find_profile_node(
    document: MutableMapping[str, object],
    profile_id: str,
) -> MutableMapping[str, object]:
    for item in _profiles_list(
        document
    ):
        if (
            isinstance(
                item,
                MutableMapping,
            )
            and item.get("id")
            == profile_id
        ):
            return item

    raise ConfigEditError(
        f"Profile was not found in YAML: {profile_id}"
    )


def _find_profile_index(
    document: MutableMapping[str, object],
    profile_id: str,
) -> int:
    profiles = _profiles_list(
        document
    )

    for index, item in enumerate(
        profiles
    ):
        if (
            isinstance(
                item,
                MutableMapping,
            )
            and item.get("id")
            == profile_id
        ):
            return index

    raise ConfigEditError(
        f"Profile was not found in YAML: {profile_id}"
    )


def _ensure_mapping(
    parent: MutableMapping[str, object],
    key: str,
) -> MutableMapping[str, object]:
    value = parent.get(key)

    if value is None:
        mapping = CommentedMap()

        parent[key] = mapping

        return mapping

    if isinstance(
        value,
        MutableMapping,
    ):
        return value

    raise ConfigEditError(
        f"Expected '{key}' to be a mapping."
    )


def _ensure_variant_mapping(
    profile: MutableMapping[str, object],
    key: str,
) -> MutableMapping[str, object]:
    value = profile.get(key)

    if value is None:
        mapping = CommentedMap()

        profile[key] = mapping

        return mapping

    if isinstance(
        value,
        str,
    ):
        mapping = CommentedMap()

        mapping["dark"] = value
        mapping["light"] = value

        profile[key] = mapping

        return mapping

    if isinstance(
        value,
        MutableMapping,
    ):
        return value

    raise ConfigEditError(
        f"Expected '{key}' to be a string "
        "or dark/light mapping."
    )


def _write_document(
    yaml: YAML,
    path: Path,
    document: Mapping[str, object],
) -> None:
    temporary = path.with_name(
        f".{path.name}.tmp"
    )

    try:
        original_mode = stat.S_IMODE(
            path.stat().st_mode
        )

    except OSError:
        original_mode = 0o600

    try:
        with temporary.open(
            "w",
            encoding="utf-8",
        ) as stream:
            yaml.dump(
                document,
                stream,
            )

            stream.flush()

            os.fsync(
                stream.fileno()
            )

        os.chmod(
            temporary,
            original_mode,
        )

        os.replace(
            temporary,
            path,
        )

    except OSError as error:
        try:
            temporary.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        raise ConfigEditError(
            f"Could not write configuration: {error}"
        ) from error


def _slugify(
    value: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKD",
        value,
    )

    ascii_value = (
        normalized
        .encode(
            "ascii",
            "ignore",
        )
        .decode("ascii")
        .lower()
    )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        ascii_value,
    ).strip("-")

    return slug or "profile"


def _existing_profile_ids(
    document: MutableMapping[str, object],
) -> set[str]:
    ids: set[str] = set()

    for profile in _profiles_list(
        document
    ):
        if not isinstance(
            profile,
            Mapping,
        ):
            continue

        profile_id = profile.get(
            "id"
        )

        if isinstance(
            profile_id,
            str,
        ):
            ids.add(
                profile_id
            )

    return ids


def _unique_profile_id(
    document: MutableMapping[str, object],
    name: str,
) -> str:
    existing = (
        _existing_profile_ids(
            document
        )
    )

    base = _slugify(
        name
    )

    if base not in existing:
        return base

    counter = 2

    while True:
        candidate = (
            f"{base}-{counter}"
        )

        if candidate not in existing:
            return candidate

        counter += 1


def _validate_wallpaper_source(
    source: Path,
) -> Path:
    source = (
        source
        .expanduser()
        .resolve()
    )

    if not source.exists():
        raise ConfigEditError(
            f"Wallpaper does not exist: {source}"
        )

    if not source.is_file():
        raise ConfigEditError(
            f"Wallpaper is not a file: {source}"
        )

    return source


def _copy_wallpaper(
    source: Path,
    wallpaper_directory: Path,
    profile_id: str,
) -> tuple[
    Path,
    str,
]:
    source = _validate_wallpaper_source(
        source
    )

    wallpaper_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    suffix = (
        source.suffix.lower()
        if source.suffix
        else ".img"
    )

    candidate = (
        wallpaper_directory
        / f"{profile_id}{suffix}"
    )

    counter = 2

    while candidate.exists():
        candidate = (
            wallpaper_directory
            / (
                f"{profile_id}-"
                f"{counter}{suffix}"
            )
        )

        counter += 1

    try:
        shutil.copy2(
            source,
            candidate,
        )

    except OSError as error:
        raise ConfigEditError(
            f"Could not import wallpaper: {error}"
        ) from error

    relative = (
        candidate
        .relative_to(
            wallpaper_directory
        )
        .as_posix()
    )

    return (
        candidate,
        relative,
    )


def create_profile(
    configuration: Configuration,
    *,
    name: str,
    wallpaper: Path,
) -> str:
    """Create a new profile inheriting all appearance defaults."""

    name = name.strip()

    if not name:
        raise ConfigEditError(
            "Profile name cannot be empty."
        )

    yaml, document = _load_document(
        configuration.source_path
    )

    profile_id = (
        _unique_profile_id(
            document,
            name,
        )
    )

    copied_wallpaper, relative = (
        _copy_wallpaper(
            wallpaper,
            configuration.wallpaper_directory,
            profile_id,
        )
    )

    profile = CommentedMap()

    profile["id"] = profile_id
    profile["name"] = name
    profile["wallpaper"] = relative

    profiles = _profiles_list(
        document
    )

    profiles.append(
        profile
    )

    try:
        _write_document(
            yaml,
            configuration.source_path,
            document,
        )

    except Exception:
        try:
            copied_wallpaper.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        raise

    return profile_id


def duplicate_profile(
    configuration: Configuration,
    profile_id: str,
) -> str:
    """Duplicate a profile and give it its own wallpaper file."""

    yaml, document = _load_document(
        configuration.source_path
    )

    index = _find_profile_index(
        document,
        profile_id,
    )

    profiles = _profiles_list(
        document
    )

    source = profiles[index]

    if not isinstance(
        source,
        MutableMapping,
    ):
        raise ConfigEditError(
            "Profile structure is invalid."
        )

    source_name = source.get(
        "name"
    )

    if not isinstance(
        source_name,
        str,
    ):
        source_name = profile_id

    new_name = (
        f"{source_name} Copy"
    )

    new_id = _unique_profile_id(
        document,
        new_name,
    )

    configured_profile = next(
        (
            profile
            for profile
            in configuration.profiles
            if profile.id
            == profile_id
        ),
        None,
    )

    if configured_profile is None:
        raise ConfigEditError(
            f"Profile is not loaded: {profile_id}"
        )

    copied_wallpaper, relative = (
        _copy_wallpaper(
            configured_profile.wallpaper,
            configuration.wallpaper_directory,
            new_id,
        )
    )

    duplicated = copy.deepcopy(
        source
    )

    duplicated["id"] = new_id
    duplicated["name"] = new_name
    duplicated["wallpaper"] = relative

    profiles.insert(
        index + 1,
        duplicated,
    )

    try:
        _write_document(
            yaml,
            configuration.source_path,
            document,
        )

    except Exception:
        try:
            copied_wallpaper.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        raise

    return new_id


def delete_profile(
    configuration: Configuration,
    profile_id: str,
) -> None:
    """Remove a profile from the configuration."""

    yaml, document = _load_document(
        configuration.source_path
    )

    profiles = _profiles_list(
        document
    )

    if len(profiles) <= 1:
        raise ConfigEditError(
            "Cinnameleon must keep at least one profile."
        )

    index = _find_profile_index(
        document,
        profile_id,
    )

    del profiles[index]

    _write_document(
        yaml,
        configuration.source_path,
        document,
    )


def change_profile_wallpaper(
    configuration: Configuration,
    profile_id: str,
    wallpaper: Path,
) -> bool:
    """Import and assign a new wallpaper to a profile."""

    configured_profile = next(
        (
            profile
            for profile
            in configuration.profiles
            if profile.id
            == profile_id
        ),
        None,
    )

    if configured_profile is None:
        raise ConfigEditError(
            f"Profile is not loaded: {profile_id}"
        )

    wallpaper = _validate_wallpaper_source(
        wallpaper
    )

    if (
        wallpaper
        == configured_profile.wallpaper.resolve()
    ):
        return False

    yaml, document = _load_document(
        configuration.source_path
    )

    profile = _find_profile_node(
        document,
        profile_id,
    )

    copied_wallpaper, relative = (
        _copy_wallpaper(
            wallpaper,
            configuration.wallpaper_directory,
            profile_id,
        )
    )

    profile["wallpaper"] = relative

    try:
        _write_document(
            yaml,
            configuration.source_path,
            document,
        )

    except Exception:
        try:
            copied_wallpaper.unlink(
                missing_ok=True
            )

        except OSError:
            pass

        raise

    return True


def save_profile_edits(
    configuration: Configuration,
    desired: EffectiveProfile,
) -> bool:
    """
    Save appearance changes made through the GUI.

    Values that still match the resolved profile are not
    unnecessarily copied into the YAML profile.
    """

    resolved = resolve_profile(
        configuration,
        desired.id,
        desired.mode,
    )

    yaml, document = _load_document(
        configuration.source_path
    )

    profile = _find_profile_node(
        document,
        desired.id,
    )

    changed = False

    desired_name = (
        desired.name.strip()
    )

    if not desired_name:
        raise ConfigEditError(
            "Profile name cannot be empty."
        )

    if desired_name != resolved.name:
        profile["name"] = (
            desired_name
        )

        changed = True

    mode_key = desired.mode.value

    for (
        yaml_key,
        attribute,
    ) in VARIANT_FIELDS:
        desired_value = getattr(
            desired.appearance,
            attribute,
        )

        resolved_value = getattr(
            resolved.appearance,
            attribute,
        )

        if desired_value is None:
            continue

        if (
            desired_value
            == resolved_value
        ):
            continue

        variants = (
            _ensure_variant_mapping(
                profile,
                yaml_key,
            )
        )

        variants[
            mode_key
        ] = desired_value

        changed = True

    desired_fonts = (
        desired.appearance.fonts
    )

    resolved_fonts = (
        resolved.appearance.fonts
    )

    changed_fonts: dict[
        str,
        str,
    ] = {}

    for (
        yaml_key,
        attribute,
    ) in FONT_FIELDS:
        desired_value = getattr(
            desired_fonts,
            attribute,
        )

        resolved_value = getattr(
            resolved_fonts,
            attribute,
        )

        if desired_value is None:
            continue

        if (
            desired_value
            == resolved_value
        ):
            continue

        changed_fonts[
            yaml_key
        ] = desired_value

    if changed_fonts:
        fonts = _ensure_mapping(
            profile,
            "fonts",
        )

        for (
            key,
            value,
        ) in changed_fonts.items():
            fonts[key] = value

        changed = True

    if not changed:
        return False

    _write_document(
        yaml,
        configuration.source_path,
        document,
    )

    return True