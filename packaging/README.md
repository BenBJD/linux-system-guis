# Packaging & Distribution

## 1. Arch Linux

The PKGBUILD is designed to work standalone from the AUR and locally within this monorepo.

### Prerequisites
```bash
sudo pacman -S --needed base-devel python-build python-installer python-wheel python-hatchling python-pyqt6
```

### Local Build
```bash
./packaging/build_arch.sh
```
This script creates a local source tarball, runs `makepkg`, and produces `linux-system-guis-*-*-any.pkg.tar.zst`.

### Installing

```bash
sudo pacman -U packaging/arch/*.pkg.tar.zst
```

---

## 2. Debian / Ubuntu / Linux Mint (.deb)

### Prerequisites
```bash
sudo apt install -y debhelper dh-python python3-all python3-pyqt6 python3-build python3-installer python3-hatchling
```

### Build Package
```bash
./packaging/build_deb.sh
```

This produces `linux-system-guis_*-*_all.deb`, which can be installed with:
```bash
sudo dpkg -i packaging/debian/*.deb
```

---

## 3. Fedora / RHEL / openSUSE (.rpm)

### Prerequisites
```bash
sudo dnf install -y rpm-build python3-devel python3-pip python3-wheel python3-hatchling python3-installer python3-pyqt6
```

### Build Package
```bash
./packaging/build_rpm.sh
```

This produces `linux-system-guis-*-*_noarch.rpm`, which can be installed with:
```bash
sudo dnf install packaging/rpm/build/rpmbuild/RPMS/noarch/*.rpm
```