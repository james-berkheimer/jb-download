JB Download

A command-line utility for downloading media using yt-dlp, with clean settings integration, virtual environment isolation, and one-command updating.

---

Quick Start: Install Locally

To install jb-download into /opt/jb-download with a virtual environment:

1. Download the installer bundle

   curl -L https://github.com/james-berkheimer/jb-download/releases/latest/download/install-jb-download.tar.gz | tar xz
   cd jb-download-installer
   chmod +x install.sh

2. Run the installer

   sudo ./install.sh

This will:

- Install Python and required tools
- Create a virtual environment in /opt/jb-download/venv
- Download the latest jb-download wheel from GitHub Releases
- Install jb-download into the venv
- Add aliases and environment config via /etc/profile.d/jb-download.sh

---

Aliases

After reboot or 'source /etc/profile', the following commands will be available:

    jb-download             # Run the CLI
    jb-download-update      # Pull the latest jb-download release and install it
    jb-download-uninstall   # Remove jb-download from system
    jb-download-settings    # Open your active jb-download settings.json

---

Updating

To update the app:

    jb-download-update

This will:

- Download the latest jb-download wheel from GitHub Releases
- Install the new version into the existing venv
- Clean up temporary files

---

Uninstalling

To remove jb-download completely:

    sudo jb-download-uninstall

This will:

- Remove /opt/jb-download
- Remove the /etc/profile.d/jb-download.sh alias file
- Recommend reboot or 'source /etc/profile' to finalize cleanup

---

Developer Info

This repo includes:

- Full CI pipeline with version bumping, wheel building, and GitHub Release upload
- Installer scripts live in the root of the project
- Releases available at: https://github.com/james-berkheimer/jb-download/releases

---

Versioning

Versioning is handled automatically via GitHub Actions. The VERSION file is updated and tagged on every push to main.

---

License

MIT © James Berkheimer
