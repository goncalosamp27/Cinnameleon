#!/usr/bin/env bash

set -Eeuo pipefail

APPLICATION_ID="io.github.goncalosamp27.cinnameleon"
APPLICATION_NAME="Cinnameleon"

AUTOSTART_ENABLED=true

show_help() {
    cat <<HELP
Usage: ./scripts/install.sh [options]

Options:
  --no-autostart  Do not start Cinnameleon automatically with the session
  --help          Show this help message
HELP
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-autostart)
            AUTOSTART_ENABLED=false
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo
            show_help
            exit 2
            ;;
    esac
done

PROJECT_DIRECTORY="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
STATE_HOME="${XDG_STATE_HOME:-${HOME}/.local/state}"

INSTALL_DIRECTORY="${DATA_HOME}/cinnameleon"
VENV_DIRECTORY="${INSTALL_DIRECTORY}/venv"
EXECUTABLE="${VENV_DIRECTORY}/bin/cinnameleon"

APPLICATIONS_DIRECTORY="${DATA_HOME}/applications"
AUTOSTART_DIRECTORY="${CONFIG_HOME}/autostart"

ICON_THEME_DIRECTORY="${DATA_HOME}/icons/hicolor"
APP_ICON_DIRECTORY="${ICON_THEME_DIRECTORY}/scalable/apps"
TRAY_ICON_DIRECTORY="${ICON_THEME_DIRECTORY}/scalable/status"

APPLICATION_ENTRY="${APPLICATIONS_DIRECTORY}/${APPLICATION_ID}.desktop"
AUTOSTART_ENTRY="${AUTOSTART_DIRECTORY}/${APPLICATION_ID}.desktop"

SOURCE_APP_ICON="${PROJECT_DIRECTORY}/assets/icons/${APPLICATION_ID}.svg"
SOURCE_TRAY_ICON="${PROJECT_DIRECTORY}/assets/icons/${APPLICATION_ID}-tray-symbolic.svg"

INSTALLED_APP_ICON="${APP_ICON_DIRECTORY}/${APPLICATION_ID}.svg"
INSTALLED_TRAY_ICON="${TRAY_ICON_DIRECTORY}/${APPLICATION_ID}-tray-symbolic.svg"

CONFIG_DIRECTORY="${CONFIG_HOME}/cinnameleon"
CONFIG_FILE="${CONFIG_DIRECTORY}/config.yaml"
EXAMPLE_CONFIG="${CONFIG_DIRECTORY}/config.example.yaml"
SOURCE_EXAMPLE_CONFIG="${PROJECT_DIRECTORY}/data/config.example.yaml"

SYSTEM_PYTHON="${SYSTEM_PYTHON:-/usr/bin/python3}"

if command -v xdg-user-dir >/dev/null 2>&1; then
    PICTURES_DIRECTORY="$(xdg-user-dir PICTURES)"
else
    PICTURES_DIRECTORY="${HOME}/Pictures"
fi

if [[ -z "${PICTURES_DIRECTORY}" ]]; then
    PICTURES_DIRECTORY="${HOME}/Pictures"
fi

STARTER_WALLPAPER_DIRECTORY="${PICTURES_DIRECTORY}/Cinnameleon"

echo "Installing ${APPLICATION_NAME}"
echo "================================"
echo

if [[ ! -f "${PROJECT_DIRECTORY}/pyproject.toml" ]]; then
    echo "pyproject.toml was not found:"
    echo "  ${PROJECT_DIRECTORY}/pyproject.toml"
    exit 1
fi

if [[ ! -x "${SYSTEM_PYTHON}" ]]; then
    echo "System Python was not found:"
    echo "  ${SYSTEM_PYTHON}"
    exit 1
fi

for icon in "${SOURCE_APP_ICON}" "${SOURCE_TRAY_ICON}"; do
    if [[ ! -s "${icon}" ]]; then
        echo "Missing or empty icon:"
        echo "  ${icon}"
        exit 1
    fi
done

if ! "${SYSTEM_PYTHON}" -m venv --help >/dev/null 2>&1; then
    echo "Python venv support is unavailable."
    echo
    echo "On Linux Mint, install it with:"
    echo "  sudo apt install python3-venv"
    exit 1
fi

mkdir -p \
    "${INSTALL_DIRECTORY}" \
    "${APPLICATIONS_DIRECTORY}" \
    "${AUTOSTART_DIRECTORY}" \
    "${APP_ICON_DIRECTORY}" \
    "${TRAY_ICON_DIRECTORY}" \
    "${CONFIG_DIRECTORY}" \
    "${STARTER_WALLPAPER_DIRECTORY}"

if [[ ! -x "${VENV_DIRECTORY}/bin/python" ]]; then
    echo "Creating private Python environment..."

    "${SYSTEM_PYTHON}" -m venv \
        --system-site-packages \
        "${VENV_DIRECTORY}"
else
    echo "Reusing existing Python environment..."
fi

echo "Checking system dependencies..."

if ! "${VENV_DIRECTORY}/bin/python" - <<'PY'
import gi
import yaml

gi.require_version("Gtk", "3.0")
gi.require_version("XApp", "1.0")

from gi.repository import Gio, Gtk, XApp

print("GTK, Gio, XApp and PyYAML are available.")
PY
then
    echo
    echo "Required system dependencies are missing."
    echo
    echo "On Linux Mint, install them with:"
    echo
    echo "  sudo apt install \\"
    echo "    python3-gi \\"
    echo "    gir1.2-gtk-3.0 \\"
    echo "    gir1.2-xapp-1.0 \\"
    echo "    python3-yaml"
    exit 1
fi

echo "Installing the Python package..."

"${VENV_DIRECTORY}/bin/python" -m pip install \
    --upgrade \
    --no-deps \
    --no-build-isolation \
    "${PROJECT_DIRECTORY}"

if [[ ! -x "${EXECUTABLE}" ]]; then
    echo "Installation failed: executable was not created."
    echo "Expected:"
    echo "  ${EXECUTABLE}"
    exit 1
fi

echo "Installing application icons..."

install \
    -m 0644 \
    "${SOURCE_APP_ICON}" \
    "${INSTALLED_APP_ICON}"

install \
    -m 0644 \
    "${SOURCE_TRAY_ICON}" \
    "${INSTALLED_TRAY_ICON}"

echo "Creating application menu entry..."

cat > "${APPLICATION_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Apply appearance profiles based on your wallpaper
Exec="${EXECUTABLE}" run
TryExec=${EXECUTABLE}
Icon=${APPLICATION_ID}
Terminal=false
Categories=Settings;
Keywords=theme;wallpaper;appearance;dark;light;cinnamon;
StartupNotify=false
DESKTOP

if [[ "${AUTOSTART_ENABLED}" == true ]]; then
    echo "Creating session autostart entry..."

    cat > "${AUTOSTART_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Start Cinnameleon with the Cinnamon session
Exec="${EXECUTABLE}" run
TryExec=${EXECUTABLE}
Icon=${APPLICATION_ID}
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
DESKTOP
else
    echo "Autostart disabled."
    rm -f "${AUTOSTART_ENTRY}"
fi

chmod 0644 \
    "${APPLICATION_ENTRY}"

if [[ -f "${AUTOSTART_ENTRY}" ]]; then
    chmod 0644 "${AUTOSTART_ENTRY}"
fi

if [[ -f "${SOURCE_EXAMPLE_CONFIG}" ]]; then
    install \
        -m 0644 \
        "${SOURCE_EXAMPLE_CONFIG}" \
        "${EXAMPLE_CONFIG}"
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "Creating starter configuration from the current desktop..."

    CONFIG_FILE="${CONFIG_FILE}" \
    WALLPAPER_DIRECTORY="${STARTER_WALLPAPER_DIRECTORY}" \
    "${VENV_DIRECTORY}/bin/python" <<'PY'
from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi
import yaml

gi.require_version("Gio", "2.0")

from gi.repository import Gio


config_file = Path(os.environ["CONFIG_FILE"])
wallpaper_directory = Path(
    os.environ["WALLPAPER_DIRECTORY"]
)

wallpaper_directory.mkdir(
    parents=True,
    exist_ok=True,
)


def read_setting(
    schema: str,
    key: str,
    fallback: str,
) -> str:
    try:
        settings = Gio.Settings.new(schema)
        value = settings.get_string(key)
    except Exception:
        return fallback

    return value or fallback


gtk_theme = read_setting(
    "org.cinnamon.desktop.interface",
    "gtk-theme",
    "Mint-Y",
)

icon_theme = read_setting(
    "org.cinnamon.desktop.interface",
    "icon-theme",
    "Mint-Y",
)

cursor_theme = read_setting(
    "org.cinnamon.desktop.interface",
    "cursor-theme",
    "default",
)

interface_font = read_setting(
    "org.cinnamon.desktop.interface",
    "font-name",
    "Sans 10",
)

cinnamon_theme = read_setting(
    "org.cinnamon.theme",
    "name",
    gtk_theme,
)

window_theme = read_setting(
    "org.cinnamon.desktop.wm.preferences",
    "theme",
    "Mint-Y",
)

window_title_font = read_setting(
    "org.cinnamon.desktop.wm.preferences",
    "titlebar-font",
    "Sans Bold 10",
)

document_font = read_setting(
    "org.gnome.desktop.interface",
    "document-font-name",
    "Sans 10",
)

monospace_font = read_setting(
    "org.gnome.desktop.interface",
    "monospace-font-name",
    "Monospace 10",
)

picture_uri = read_setting(
    "org.cinnamon.desktop.background",
    "picture-uri",
    "",
)

parsed_uri = urlparse(picture_uri)

source_wallpaper: Path | None = None

if parsed_uri.scheme == "file":
    source_wallpaper = Path(
        unquote(parsed_uri.path)
    ).expanduser()

if (
    source_wallpaper is None
    or not source_wallpaper.is_file()
):
    print(
        "Current wallpaper is not a supported local file."
    )
    print(
        "Starter config was not created. "
        "Edit config.example.yaml manually."
    )
    raise SystemExit(0)

suffix = source_wallpaper.suffix.lower() or ".jpg"
target_wallpaper = (
    wallpaper_directory / f"current{suffix}"
)

if source_wallpaper.resolve() != target_wallpaper.resolve():
    shutil.copy2(
        source_wallpaper,
        target_wallpaper,
    )

configuration = {
    "wallpaper_directory": str(
        wallpaper_directory
    ),
    "defaults": {
        "gtk_theme": {
            "dark": gtk_theme,
            "light": gtk_theme,
        },
        "cinnamon_theme": {
            "dark": cinnamon_theme,
            "light": cinnamon_theme,
        },
        "window_borders": {
            "dark": window_theme,
            "light": window_theme,
        },
        "icon_theme": {
            "dark": icon_theme,
            "light": icon_theme,
        },
        "cursor_theme": {
            "dark": cursor_theme,
            "light": cursor_theme,
        },
        "fonts": {
            "interface": interface_font,
            "document": document_font,
            "monospace": monospace_font,
            "window_title": window_title_font,
        },
    },
    "profiles": [
        {
            "id": "current",
            "name": "Current setup",
            "wallpaper": target_wallpaper.name,
        }
    ],
}

temporary_file = config_file.with_suffix(
    ".yaml.tmp"
)

with temporary_file.open(
    "w",
    encoding="utf-8",
) as output:
    yaml.safe_dump(
        configuration,
        output,
        sort_keys=False,
        allow_unicode=True,
    )

os.chmod(temporary_file, 0o600)
temporary_file.replace(config_file)

print(f"Starter configuration: {config_file}")
print(f"Starter wallpaper: {target_wallpaper}")
PY
else
    echo "Existing configuration preserved:"
    echo "  ${CONFIG_FILE}"
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache \
        --force \
        --ignore-theme-index \
        "${ICON_THEME_DIRECTORY}" \
        >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database \
        "${APPLICATIONS_DIRECTORY}" \
        >/dev/null 2>&1 || true
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "${APPLICATION_ENTRY}"

    if [[ -f "${AUTOSTART_ENTRY}" ]]; then
        desktop-file-validate "${AUTOSTART_ENTRY}"
    fi
fi

echo
echo "${APPLICATION_NAME} was installed successfully."
echo
echo "Executable:"
echo "  ${EXECUTABLE}"
echo
echo "Configuration:"
echo "  ${CONFIG_FILE}"
echo
echo "Application menu:"
echo "  ${APPLICATION_ENTRY}"
echo
echo "Autostart:"
if [[ "${AUTOSTART_ENABLED}" == true ]]; then
    echo "  ${AUTOSTART_ENTRY}"
else
    echo "  disabled"
fi
echo
echo "Open the Cinnamon application menu and search for:"
echo "  ${APPLICATION_NAME}"
