#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prevent active Python virtual environment from interfering with build
if [ -n "$VIRTUAL_ENV" ]; then
    export PATH="/usr/bin:/bin:$(echo "$PATH" | sed -e "s|$VIRTUAL_ENV/bin:||g" -e "s|:$VIRTUAL_ENV/bin||g")"
    unset VIRTUAL_ENV
fi

echo "==> Building Debian/Ubuntu package (.deb)..."
cd "$ROOT_DIR"

if command -v dpkg-buildpackage >/dev/null 2>&1; then
    # Prepare debian directory in root
    rm -rf "$ROOT_DIR/debian"
    cp -r "$SCRIPT_DIR/debian" "$ROOT_DIR/debian"
    dpkg-buildpackage -us -uc -b
    echo "==> .deb package built successfully in parent directory."
else
    echo "Notice: dpkg-buildpackage is not installed on this system."
    echo "To build on Debian/Ubuntu, run:"
    echo "  sudo apt install -y debhelper dh-python python3-all python3-pyqt6 python3-build python3-installer python3-hatchling"
    echo "  cp -r packaging/debian ."
    echo "  dpkg-buildpackage -us -uc -b"
fi
