#!/bin/bash
set -e

VENV_PATH="/opt/jb-download/venv"
INSTALL_DIR="/opt/jb-download"

echo "=== Installing dependencies ==="
apt update
apt install -y python3 python3-venv python3-pip curl

echo "=== Creating installation directory ==="
mkdir -p "$VENV_PATH"

echo "=== Creating virtual environment ==="
python3 -m venv "$VENV_PATH"
"$VENV_PATH/bin/pip" install --upgrade pip setuptools wheel

echo "=== Downloading latest jb-download wheel ==="
LATEST_VERSION=$(curl -s https://api.github.com/repos/james-berkheimer/jb-download/releases/latest | grep -Po '"tag_name": "v\\K[^"]+')
if [ -z "$LATEST_VERSION" ]; then
  echo "Error: Unable to fetch latest jb-download version from GitHub."
  exit 1
fi
WHEEL_PATH="/tmp/jb_download-${LATEST_VERSION}-py3-none-any.whl"
curl -fL -o "$WHEEL_PATH" \
  "https://github.com/james-berkheimer/jb-download/releases/download/v${LATEST_VERSION}/jb_download-${LATEST_VERSION}-py3-none-any.whl"

if [ ! -f "$WHEEL_PATH" ]; then
  echo "❌ Wheel file not downloaded properly!"
  exit 1
fi

echo "=== Installing jb-download v${LATEST_VERSION} ==="
"$VENV_PATH/bin/pip" install "$WHEEL_PATH"
rm -f /tmp/jb_download-*.whl

echo "=== Verifying install ==="
/opt/jb-download/venv/bin/jb-download --help

echo "=== Creating update.sh ==="
cat > "$INSTALL_DIR/update.sh" << 'EOF'
#!/bin/bash
set -e
VENV_PATH="/opt/jb-download/venv"
LATEST_VERSION=$(curl -s https://api.github.com/repos/james-berkheimer/jb-download/releases/latest | grep -Po '"tag_name": "v\\K[^"]+')
if [ -z "$LATEST_VERSION" ]; then
  echo "Error: Unable to fetch latest jb-download version."
  exit 1
fi
echo "➡ Updating to version: $LATEST_VERSION"
WHEEL_PATH="/tmp/jb_download-${LATEST_VERSION}-py3-none-any.whl"
curl -fL -o "$WHEEL_PATH" \
  "https://github.com/james-berkheimer/jb-download/releases/download/v${LATEST_VERSION}/jb_download-${LATEST_VERSION}-py3-none-any.whl"

if [ ! -f "$WHEEL_PATH" ]; then
  echo "❌ Wheel file not downloaded properly!"
  exit 1
fi

"$VENV_PATH/bin/pip" install --upgrade "$WHEEL_PATH"
rm -f /tmp/jb_download-*.whl
"$VENV_PATH/bin/jb-download" --help
echo "Update complete"
EOF

chmod +x "$INSTALL_DIR/update.sh"

echo "=== Setting up aliases ==="
cat > /etc/profile.d/jb-download.sh << 'EOF'
export JBDOWNLOAD_SETTINGS=/opt/jb-download/venv/lib/python3.*/site-packages/jb_download_settings.json
alias jb-download="/opt/jb-download/venv/bin/jb-download"
alias jb-download-update="/opt/jb-download/update.sh"
alias jb-download-uninstall="/opt/jb-download/uninstall.sh"
alias jb-download-settings='nano $(find /opt/jb-download/venv/lib/python3*/site-packages/jb_download_settings.json 2>/dev/null | head -n 1)'
EOF

chmod +x /etc/profile.d/jb-download.sh

echo "=== Installation complete ==="
echo "➡ Run 'source /etc/profile' or reboot to activate aliases"
