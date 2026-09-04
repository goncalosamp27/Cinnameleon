#!/usr/bin/env bash

set -Eeuo pipefail

APPLICATION_ID="io.github.goncalosamp27.cinnameleon"
APPLICATION_NAME="Cinnameleon"

PURGE=false


while [[ $# -gt 0 ]]; do
    case "$1" in
        --purge)
            PURGE=true
            shift
            ;;

        --help)
            echo "Usage: ./scripts/uninstall.sh [--purge]"
            exit 0
            ;;

        *)
            echo "Unknown option: $1"
            exit 2
            ;;
    esac
done


DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
STATE_HOME="${XDG_STATE_HOME:-${HOME}/.local/state}"

INSTALL_DIRECTORY="${DATA_HOME}/cinnameleon"

APPLICATION_ENTRY="${DATA_HOME}/applications/${APPLICATION_ID}.desktop"
AUTOSTART_ENTRY="${CONFIG_HOME}/autostart/${APPLICATION_ID}.desktop"

ICON_THEME_DIRECTORY="${DATA_HOME}/icons/hicolor"

APP_ICON="${ICON_THEME_DIRECTORY}/32x32/apps/${APPLICATION_ID}.png"

CONFIG_DIRECTORY="${CONFIG_HOME}/cinnameleon"
STATE_DIRECTORY="${STATE_HOME}/cinnameleon"


echo "Uninstalling ${APPLICATION_NAME}"
echo "=================================="
echo


pkill -f "cinnameleon run" \
    2>/dev/null || true


rm -f \
    "${APPLICATION_ENTRY}" \
    "${AUTOSTART_ENTRY}" \
    "${APP_ICON}"


for SIZE in 16 22 24 32; do
    rm -f \
        "${ICON_THEME_DIRECTORY}/${SIZE}x${SIZE}/status/${APPLICATION_ID}-tray-symbolic.png"
done


rm -rf \
    "${INSTALL_DIRECTORY}"


if [[ "${PURGE}" == true ]]; then
    rm -rf \
        "${CONFIG_DIRECTORY}" \
        "${STATE_DIRECTORY}"

    echo "Configuration and state removed."
else
    echo "Configuration and state preserved."
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