#!/usr/bin/env bash

set -euo pipefail

APPLICATION_ID="io.github.goncalosamp27.cinnameleon"
APPLICATION_NAME="Cinnameleon"

PROJECT_DIRECTORY="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
    pwd
)"

EXECUTABLE="${PROJECT_DIRECTORY}/.venv/bin/cinnameleon"

APPLICATIONS_DIRECTORY="${HOME}/.local/share/applications"
AUTOSTART_DIRECTORY="${HOME}/.config/autostart"

APPLICATION_ENTRY="${APPLICATIONS_DIRECTORY}/${APPLICATION_ID}.desktop"
AUTOSTART_ENTRY="${AUTOSTART_DIRECTORY}/${APPLICATION_ID}.desktop"

if [[ ! -x "${EXECUTABLE}" ]]; then
    echo "Cinnameleon executable was not found:"
    echo "${EXECUTABLE}"
    echo
    echo "Create the virtual environment and install the project first."
    exit 1
fi

mkdir -p \
    "${APPLICATIONS_DIRECTORY}" \
    "${AUTOSTART_DIRECTORY}"

cat > "${APPLICATION_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Automatically apply appearance profiles based on your wallpaper
Exec=${EXECUTABLE} run
Icon=preferences-desktop-theme
Terminal=false
Categories=Settings;
Keywords=theme;wallpaper;appearance;dark;light;cinnamon;
StartupNotify=false
StartupWMClass=${APPLICATION_ID}
DESKTOP

cat > "${AUTOSTART_ENTRY}" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=${APPLICATION_NAME}
Comment=Start Cinnameleon with the Cinnamon session
Exec=${EXECUTABLE} run
Icon=preferences-desktop-theme
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
DESKTOP

chmod 0644 \
    "${APPLICATION_ENTRY}" \
    "${AUTOSTART_ENTRY}"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "${APPLICATIONS_DIRECTORY}" \
        >/dev/null 2>&1 || true
fi

echo "Desktop integration installed."
echo
echo "Application menu:"
echo "  ${APPLICATION_ENTRY}"
echo
echo "Autostart:"
echo "  ${AUTOSTART_ENTRY}"
