#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prevent active Python virtual environment from interfering with makepkg / build
if [ -n "$VIRTUAL_ENV" ]; then
    export PATH="/usr/bin:/bin:$(echo "$PATH" | sed -e "s|$VIRTUAL_ENV/bin:||g" -e "s|:$VIRTUAL_ENV/bin||g")"
    unset VIRTUAL_ENV
fi

echo "==> Building Arch Linux package (makepkg)..."
cd "$SCRIPT_DIR/arch"

VERSION="0.1.0"
TAR_NAME="linux-system-guis-${VERSION}.tar.gz"

# Clean previous build artifacts
rm -rf pkg src dist *.pkg.tar.zst "$TAR_NAME"

echo "==> Creating source archive $TAR_NAME from local tree..."
# Archive from git if available, otherwise tar
git -C "$ROOT_DIR" archive --format=tar.gz --prefix="linux-system-guis-${VERSION}/" HEAD -o "$SCRIPT_DIR/arch/$TAR_NAME" 2>/dev/null || {
    tar --exclude='.git' --exclude='.venv' --exclude='packaging/arch/pkg' \
        --exclude='packaging/arch/src' --exclude='packaging/arch/dist' \
        --exclude='packaging/arch/*.pkg.tar.*' --exclude='build' \
        --exclude='dist' \
        -czf "$SCRIPT_DIR/arch/$TAR_NAME" \
        --transform "s,^\.,linux-system-guis-${VERSION}," -C "$ROOT_DIR" .
}

# Run makepkg
makepkg -f --nodeps --skipchecksums

# Generate .SRCINFO for AUR distribution
makepkg --printsrcinfo > .SRCINFO 2>/dev/null || true

echo "==> Arch package built successfully in $SCRIPT_DIR/arch/"
ls -lh "$SCRIPT_DIR/arch/"*.pkg.tar.zst 2>/dev/null || true
