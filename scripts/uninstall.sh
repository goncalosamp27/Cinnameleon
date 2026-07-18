#!/usr/bin/env bash

set -Eeuo pipefail

APPLICATION_ID="io.github.goncalosamp27.cinnameleon"
APPLICATION_NAME="Cinnameleon"

PURGE=false

show_help() {
    cat <<HELP
Usage: ./scripts/uninstall.sh [options]

Options:
  --purge  Also remove configuration, logs, snapshots and saved state
  --help   Show this help message

User wallpapers in ~/Pictures/Cinnameleon are always preserved.
HELP
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge)
            PURGE=true
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

DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
STATE_HOME="${XDG_STATE_HOME:-${HOME}/.local/state}"

INSTALL_DIRECTORY="${DATA_HOME}/cinnameleon"
EXECUTABLE="${INSTALL_DIRECTORY}/venv/bin/cinnameleon"

APPLICATION_ENTRY="${DATA_HOME}/applications/${APPLICATION_ID}.desktop"
AUTOSTART_ENTRY="${CONFIG_HOME}/autostart/${APPLICATION_ID}.desktop"

ICON_THEME_DIRECTORY="${DATA_HOME}/icons/hicolor"
APP_ICON="${ICON_THEME_DIRECTORY}/scalable/apps/${APPLICATION_ID}.svg"
TRAY_ICON="${ICON_THEME_DIRECTORY}/scalable/status/${APPLICATION_ID}-tray-symbolic.svg"

CONFIG_DIRECTORY="${CONFIG_HOME}/cinnameleon"
STATE_DIRECTORY="${STATE_HOME}/cinnameleon"

echo "Uninstalling ${APPLICATION_NAME}"
echo "=================================="
echo

if [[ -x "${EXECUTABLE}" ]]; then
    pkill -f "${EXECUTABLE} run" \
        2>/dev/null || true
fi

rm -f \
    "${APPLICATION_ENTRY}" \
    "${AUTOSTART_ENTRY}" \
    "${APP_ICON}" \
    "${TRAY_ICON}"

rm -rf "${INSTALL_DIRECTORY}"

if [[ "${PURGE}" == true ]]; then
    echo "Removing configuration and application state..."

    rm -rf \
        "${CONFIG_DIRECTORY}" \
        "${STATE_DIRECTORY}"
else
    echo "Preserving user configuration and state:"
    echo "  ${CONFIG_DIRECTORY}"
    echo "  ${STATE_DIRECTORY}"
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
        "${DATA_HOME}/applications" \
        >/dev/null 2>&1 || true
fi

echo
echo "${APPLICATION_NAME} was uninstalled."
echo
echo "User wallpapers were preserved."