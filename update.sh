#!/usr/bin/env bash
# Update the installed jb-download to the latest published release.
set -euo pipefail

INSTALL_DIR="/opt/jb-download"
VENV_PATH="$INSTALL_DIR/venv"
SETTINGS_PATH="$INSTALL_DIR/jb-download_settings.json"
REPO="james-berkheimer/jb-download"

echo "=== Updating jb-download ==="

if [ ! -x "$VENV_PATH/bin/pip" ]; then
  echo "Error: jb-download is not installed at $INSTALL_DIR." >&2
  exit 1
fi

VERSION="$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" | jq -r '.tag_name // empty' | sed 's/^v//' || true)"
if [ -z "$VERSION" ]; then
  echo "Error: unable to fetch the latest jb-download version from GitHub." >&2
  exit 1
fi

CURRENT="$("$VENV_PATH/bin/jb-download" --version 2>/dev/null | awk '{print $NF}' || true)"
echo "-> Installed: ${CURRENT:-unknown}, latest: $VERSION"
if [ "$CURRENT" = "$VERSION" ]; then
  echo "Already up to date."
  exit 0
fi

WHEEL_PATH="$(mktemp -d)/jb_download-${VERSION}-py3-none-any.whl"
trap 'rm -rf "$(dirname "$WHEEL_PATH")"' EXIT

echo "-> Downloading jb-download v$VERSION ..."
curl -fL -o "$WHEEL_PATH" \
  "https://github.com/$REPO/releases/download/v${VERSION}/jb_download-${VERSION}-py3-none-any.whl"

if [ ! -s "$WHEEL_PATH" ]; then
  echo "Error: the downloaded wheel is missing or empty." >&2
  exit 1
fi

echo "-> Installing ..."
"$VENV_PATH/bin/pip" install --upgrade "$WHEEL_PATH"

# Existing settings are never overwritten; a fresh install seeds them instead.
if [ ! -f "$SETTINGS_PATH" ]; then
  DEFAULTS="$("$VENV_PATH/bin/python" -c 'from jb_download.settings import PACKAGED_DEFAULTS; print(PACKAGED_DEFAULTS)')"
  if [ -f "$DEFAULTS" ]; then
    cp "$DEFAULTS" "$SETTINGS_PATH"
    echo "-> Wrote default settings to $SETTINGS_PATH"
  fi
fi

echo "-> Verifying ..."
"$VENV_PATH/bin/jb-download" --version

echo "jb-download updated successfully."
