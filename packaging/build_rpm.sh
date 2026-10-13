#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prevent active Python virtual environment from interfering with build
if [ -n "$VIRTUAL_ENV" ]; then
    export PATH="/usr/bin:/bin:$(echo "$PATH" | sed -e "s|$VIRTUAL_ENV/bin:||g" -e "s|:$VIRTUAL_ENV/bin||g")"
    unset VIRTUAL_ENV
fi

echo "==> Building Fedora/RHEL/openSUSE package (.rpm)..."
cd "$ROOT_DIR"

if command -v rpmbuild >/dev/null 2>&1; then
    RPMBUILD_DIR="$ROOT_DIR/build/rpmbuild"
    mkdir -p "$RPMBUILD_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

    VERSION="0.1.0"
    TAR_NAME="linux-system-guis-${VERSION}"

    # Create archive directly from local tree to include untracked/staged files during development
    tar --exclude='.git' --exclude='.venv' --exclude='packaging/arch/pkg' \
        --exclude='packaging/arch/src' --exclude='packaging/arch/dist' \
        --exclude='packaging/arch/*.pkg.tar.*' --exclude='build' \
        --exclude='dist' \
        -czf "$RPMBUILD_DIR/SOURCES/${TAR_NAME}.tar.gz" \
        --transform "s,^\.,${TAR_NAME}," -C "$ROOT_DIR" .

    cp "$SCRIPT_DIR/rpm/linux-system-guis.spec" "$RPMBUILD_DIR/SPECS/"
    rpmbuild --define "_topdir $RPMBUILD_DIR" -ba "$RPMBUILD_DIR/SPECS/linux-system-guis.spec"

    echo "==> RPM built successfully in $RPMBUILD_DIR/RPMS/noarch/"
    ls -lh "$RPMBUILD_DIR/RPMS/noarch/"*.rpm 2>/dev/null || true
else
    echo "Notice: rpmbuild is not installed on this system."
    echo "To build on Fedora / RHEL / openSUSE, run:"
    echo "  sudo dnf install -y rpm-build python3-devel python3-pip python3-wheel python3-hatchling python3-installer"
    echo "  ./packaging/build_rpm.sh"
fi
