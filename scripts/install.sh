#!/usr/bin/env bash

set -Eeuo pipefail


APPLICATION_ID="io.github.goncalosamp27.cinnameleon"
APPLICATION_NAME="Cinnameleon"

AUTOSTART_ENABLED=true


show_help() {
    cat <<HELP
Usage: ./scripts/install.sh [options]

Options:
  --no-autostart  Do not start Cinnameleon automatically
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
            exit 2
            ;;
    esac
done


# =============================================================
# Paths
# =============================================================

PROJECT_DIRECTORY="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"

INSTALL_DIRECTORY="${DATA_HOME}/cinnameleon"

VENV_DIRECTORY="${INSTALL_DIRECTORY}/venv"

EXECUTABLE="${VENV_DIRECTORY}/bin/cinnameleon"

APPLICATIONS_DIRECTORY="${DATA_HOME}/applications"

AUTOSTART_DIRECTORY="${CONFIG_HOME}/autostart"

ICON_THEME_DIRECTORY="${DATA_HOME}/icons/hicolor"

APP_ICON_DIRECTORY="${ICON_THEME_DIRECTORY}/32x32/apps"

APPLICATION_ENTRY="${APPLICATIONS_DIRECTORY}/${APPLICATION_ID}.desktop"

AUTOSTART_ENTRY="${AUTOSTART_DIRECTORY}/${APPLICATION_ID}.desktop"

SOURCE_ICON="${PROJECT_DIRECTORY}/assets/icons/${APPLICATION_ID}.png"

INSTALLED_APP_ICON="${APP_ICON_DIRECTORY}/${APPLICATION_ID}.png"

TRAY_ICON_GENERATOR="${PROJECT_DIRECTORY}/scripts/generate_tray_icons.py"

SYSTEM_PYTHON="${SYSTEM_PYTHON:-/usr/bin/python3}"


echo "Installing ${APPLICATION_NAME}"
echo "================================"
echo


# =============================================================
# Validate project
# =============================================================

if [[ ! -f "${PROJECT_DIRECTORY}/pyproject.toml" ]]; then
    echo "Missing pyproject.toml:"
    echo "  ${PROJECT_DIRECTORY}/pyproject.toml"
    exit 1
fi


if [[ ! -s "${SOURCE_ICON}" ]]; then
    echo "Missing Cinnameleon icon:"
    echo "  ${SOURCE_ICON}"
    exit 1
fi


if [[ ! -f "${TRAY_ICON_GENERATOR}" ]]; then
    echo "Missing tray icon generator:"
    echo "  ${TRAY_ICON_GENERATOR}"
    exit 1
fi


if [[ ! -x "${SYSTEM_PYTHON}" ]]; then
    echo "Python was not found:"
    echo "  ${SYSTEM_PYTHON}"
    exit 1
fi


# =============================================================
# Directories
# =============================================================

mkdir -p \
    "${INSTALL_DIRECTORY}" \
    "${APPLICATIONS_DIRECTORY}" \
    "${AUTOSTART_DIRECTORY}" \
    "${APP_ICON_DIRECTORY}"


# =============================================================
# Python environment
# =============================================================

if [[ ! -x "${VENV_DIRECTORY}/bin/python" ]]; then
    echo "Creating Python environment..."

    "${SYSTEM_PYTHON}" -m venv \
        --system-site-packages \
        "${VENV_DIRECTORY}"
else
    echo "Reusing Python environment..."
fi


# =============================================================
# Native dependencies
# =============================================================

echo "Checking system dependencies..."

if ! "${VENV_DIRECTORY}/bin/python" - <<'PY'
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("XApp", "1.0")
gi.require_version("Vte", "2.91")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import (
    Gdk,
    GdkPixbuf,
    Gtk,
    Vte,
    XApp,
)

print("Native dependencies OK.")
PY
then
    echo
    echo "Required Linux Mint dependencies are missing."
    echo
    echo "Install them with:"
    echo
    echo "  sudo apt install \\"
    echo "    python3-gi \\"
    echo "    python3-venv \\"
    echo "    gir1.2-gtk-3.0 \\"
    echo "    gir1.2-xapp-1.0 \\"
    echo "    gir1.2-vte-2.91"
    exit 1
fi


# =============================================================
# Install Python package
# =============================================================

echo "Installing Cinnameleon..."

"${VENV_DIRECTORY}/bin/python" -m pip install \
    --upgrade \
    --no-build-isolation \
    "${PROJECT_DIRECTORY}"


if [[ ! -x "${EXECUTABLE}" ]]; then
    echo
    echo "Installation failed."
    echo
    echo "Expected executable:"
    echo "  ${EXECUTABLE}"
    exit 1
fi


# =============================================================
# Application icon
# =============================================================

echo "Installing application icon..."

install \
    -m 0644 \
    "${SOURCE_ICON}" \
    "${INSTALLED_APP_ICON}"


# =============================================================
# Tray icons
# =============================================================

echo "Generating optimized tray icons..."

"${VENV_DIRECTORY}/bin/python" \
    "${TRAY_ICON_GENERATOR}" \
    "${SOURCE_ICON}" \
    "${ICON_THEME_DIRECTORY}"


# =============================================================
# Desktop application entry
# =============================================================

echo "Creating application menu entry..."

cat > "${APPLICATION_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Manage Cinnamon appearance profiles
Exec=${EXECUTABLE} run --show-window
TryExec=${EXECUTABLE}
Icon=${APPLICATION_ID}
StartupWMClass=${APPLICATION_ID}
Terminal=false
Categories=Settings;
Keywords=theme;wallpaper;appearance;cinnamon;
StartupNotify=true
DESKTOP


chmod 0644 \
    "${APPLICATION_ENTRY}"


# =============================================================
# Autostart
# =============================================================

if [[ "${AUTOSTART_ENABLED}" == true ]]; then
    echo "Creating autostart entry..."

    cat > "${AUTOSTART_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Start Cinnameleon with Cinnamon
Exec=${EXECUTABLE} run
TryExec=${EXECUTABLE}
Icon=${APPLICATION_ID}
StartupWMClass=${APPLICATION_ID}
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
DESKTOP

    chmod 0644 \
        "${AUTOSTART_ENTRY}"

else
    rm -f \
        "${AUTOSTART_ENTRY}"
fi


# =============================================================
# Refresh caches
# =============================================================

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    echo "Refreshing icon cache..."

    gtk-update-icon-cache \
        --force \
        --ignore-theme-index \
        "${ICON_THEME_DIRECTORY}" \
        >/dev/null 2>&1 || true
fi


if command -v update-desktop-database >/dev/null 2>&1; then
    echo "Refreshing application database..."

    update-desktop-database \
        "${APPLICATIONS_DIRECTORY}" \
        >/dev/null 2>&1 || true
fi


# =============================================================
# Finished
# =============================================================

echo
echo "${APPLICATION_NAME} installed successfully."
echo

echo "Executable:"
echo "  ${EXECUTABLE}"
echo

echo "Application icon:"
echo "  ${INSTALLED_APP_ICON}"
echo

echo "Desktop entry:"
echo "  ${APPLICATION_ENTRY}"
echo

echo "Tray icon sizes:"
echo "  16x16"
echo "  22x22"
echo "  24x24"
echo "  32x32"
echo