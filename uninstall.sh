#!/usr/bin/env bash
# Remove jb-download from the system.
set -euo pipefail

INSTALL_DIR="/opt/jb-download"
SETTINGS_PATH="$INSTALL_DIR/jb-download_settings.json"
PROFILE_SCRIPT="/etc/profile.d/jb-download.sh"
ASSUME_YES=0

usage() {
  echo "Usage: uninstall.sh [-y|--yes]"
  echo "  -y, --yes  Do not prompt for confirmation."
}

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
  shift
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: this uninstaller must be run as root (try: sudo jb-download-uninstall)." >&2
  exit 1
fi

echo "=== Uninstalling jb-download ==="
echo "This removes $INSTALL_DIR and $PROFILE_SCRIPT."

if [ "$ASSUME_YES" -ne 1 ]; then
  read -r -p "Continue? [y/N] " reply
  case "$reply" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

# Keep the user's settings around; they are cheap to save and painful to rebuild.
if [ -f "$SETTINGS_PATH" ]; then
  BACKUP="/root/jb-download_settings.json.bak"
  cp "$SETTINGS_PATH" "$BACKUP"
  echo "-> Saved a copy of your settings to $BACKUP"
fi

if [ -d "$INSTALL_DIR" ]; then
  echo "-> Removing $INSTALL_DIR"
  rm -rf "$INSTALL_DIR"
else
  echo "-> Install directory not found: $INSTALL_DIR"
fi

if [ -f "$PROFILE_SCRIPT" ]; then
  echo "-> Removing alias script: $PROFILE_SCRIPT"
  rm -f "$PROFILE_SCRIPT"
else
  echo "-> No alias script found at $PROFILE_SCRIPT"
fi

echo "Uninstall complete. Run 'source /etc/profile' or start a new login shell to clear the aliases."
