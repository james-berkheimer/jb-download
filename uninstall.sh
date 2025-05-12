#!/bin/bash
set -e

INSTALL_DIR="/opt/jb-download"
PROFILE_SCRIPT="/etc/profile.d/jb-download.sh"

echo "=== Uninstalling jb-download ==="

if [ -d "$INSTALL_DIR" ]; then
  echo "➡ Removing $INSTALL_DIR"
  rm -rf "$INSTALL_DIR"
else
  echo "Install directory not found: $INSTALL_DIR"
fi

if [ -f "$PROFILE_SCRIPT" ]; then
  echo "➡ Removing alias script: $PROFILE_SCRIPT"
  rm -f "$PROFILE_SCRIPT"
else
  echo "No alias script found at $PROFILE_SCRIPT"
fi

echo "➡ Uninstall complete. You may need to run 'source /etc/profile' or reboot to clear aliases."
