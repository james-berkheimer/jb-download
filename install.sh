#!/usr/bin/env bash
# Install jb-download into an isolated virtual environment under /opt/jb-download.
set -euo pipefail

INSTALL_DIR="/opt/jb-download"
VENV_PATH="$INSTALL_DIR/venv"
SETTINGS_PATH="$INSTALL_DIR/jb-download_settings.json"
PROFILE_SCRIPT="/etc/profile.d/jb-download.sh"
REPO="james-berkheimer/jb-download"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: this installer must be run as root (try: sudo ./install.sh)." >&2
  exit 1
fi

echo "=== Installing dependencies ==="
apt-get update
apt-get install -y python3 python3-venv python3-pip curl jq ffmpeg

echo "=== Creating virtual environment ==="
mkdir -p "$INSTALL_DIR"
python3 -m venv "$VENV_PATH"
"$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel

echo "=== Downloading latest jb-download wheel ==="
VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | jq -r '.tag_name // empty' | sed 's/^v//' || true)"
if [ -z "$VERSION" ]; then
  echo "Error: unable to fetch the latest jb-download version from GitHub." >&2
  exit 1
fi
echo "-> Latest version: $VERSION"

WHEEL_PATH="$(mktemp -d)/jb_download-${VERSION}-py3-none-any.whl"
trap 'rm -rf "$(dirname "$WHEEL_PATH")"' EXIT
curl -fL -o "$WHEEL_PATH" \
  "https://github.com/$REPO/releases/download/v${VERSION}/jb_download-${VERSION}-py3-none-any.whl"

if [ ! -s "$WHEEL_PATH" ]; then
  echo "Error: the downloaded wheel is missing or empty." >&2
  exit 1
fi

echo "=== Installing jb-download v${VERSION} ==="
"$VENV_PATH/bin/pip" install "$WHEEL_PATH"

echo "=== Installing management scripts ==="
for script in update.sh uninstall.sh; do
  if [ ! -f "$SCRIPT_DIR/$script" ]; then
    echo "Error: $script is missing from the installer bundle." >&2
    exit 1
  fi
  install -m 755 "$SCRIPT_DIR/$script" "$INSTALL_DIR/$script"
done

echo "=== Seeding settings ==="
DEFAULTS="$("$VENV_PATH/bin/python" -c 'from jb_download.settings import PACKAGED_DEFAULTS; print(PACKAGED_DEFAULTS)')"
if [ -f "$SETTINGS_PATH" ]; then
  echo "-> Keeping existing settings at $SETTINGS_PATH"
elif [ -f "$DEFAULTS" ]; then
  cp "$DEFAULTS" "$SETTINGS_PATH"
  echo "-> Wrote default settings to $SETTINGS_PATH"
else
  echo "Warning: packaged defaults not found at '$DEFAULTS'." >&2
fi

echo "=== Setting up aliases ==="
cat > "$PROFILE_SCRIPT" << EOF
export JBDOWNLOAD_SETTINGS="$SETTINGS_PATH"
alias jb-download="$VENV_PATH/bin/jb-download"
alias jb-download-update="$INSTALL_DIR/update.sh"
alias jb-download-uninstall="$INSTALL_DIR/uninstall.sh"
alias jb-download-settings="\${EDITOR:-nano} $SETTINGS_PATH"
EOF
chmod 644 "$PROFILE_SCRIPT"

echo "=== Verifying install ==="
"$VENV_PATH/bin/jb-download" --version

echo "=== Installation complete ==="
echo "-> Run 'source $PROFILE_SCRIPT' or start a new login shell to activate the aliases."
