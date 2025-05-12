#!/bin/bash
set -e

echo "=== Updating jb-download in Container ==="

VENV_PATH="/opt/jb-download/venv"

# Get latest release version dynamically from GitHub API
DOWNLOAD_VERSION=$(curl -s https://api.github.com/repos/james-berkheimer/jb-download/releases/latest | grep -Po '"tag_name": "v\K[^"]+')

if [ -z "$DOWNLOAD_VERSION" ]; then
  echo "Error: Unable to fetch latest jb-download version from GitHub."
  exit 1
fi

echo "➡ Latest version detected: $DOWNLOAD_VERSION"

echo "➡ Downloading jb-download v$DOWNLOAD_VERSION wheel..."
curl -fL -o /tmp/download-${DOWNLOAD_VERSION}-py3-none-any.whl \
  https://github.com/james-berkheimer/jb-download/releases/download/v${DOWNLOAD_VERSION}/download-${DOWNLOAD_VERSION}-py3-none-any.whl

echo "➡ Installing updated wheel..."
$VENV_PATH/bin/pip install --upgrade /tmp/download-${DOWNLOAD_VERSION}-py3-none-any.whl

echo "➡ Cleaning up temporary files..."
rm -f /tmp/download-*.whl

echo "➡ Verifying jb-download installation..."
$VENV_PATH/bin/jb-download --help

echo "✅ jb-download successfully updated."
