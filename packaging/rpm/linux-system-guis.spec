Name:           linux-system-guis
Version:        0.1.0
Release:        1%{?dist}
Summary:        Educational, transparent desktop administration suite for Linux

License:        MIT
URL:            https://github.com/BenBJD/linux-system-guis
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  python3-hatchling
BuildRequires:  python3-installer
BuildRequires:  python3-build

Requires:       python3
Requires:       python3-pyqt6
Requires:       polkit
Recommends:     sudo
Recommends:     systemd
Recommends:     acl
Recommends:     e2fsprogs

%description
A suite of visual Linux administration utilities designed to educate users on
the exact underlying configuration syntax and commands. Features real-time syntax
preview banners, educational tooltips, strict dry-run validators (including visudo),
and automatic backups.

Includes graphical tools for:
- /etc/fstab disk mount entries (fstab-gui)
- /etc/udev/rules.d device rules (udev-gui)
- systemd services and timers (systemd-gui)
- User accounts and security groups (usermgmt-gui)
- /etc/sudoers and /etc/sudoers.d rules (sudoers-gui)
- journalctl system logs and vacuuming (journal-gui)
- Kernel sysctl parameters tuning (sysctl-gui)
- POSIX ACLs and chattr file attributes (permissions-gui)
- GRUB & systemd-boot bootloaders (bootloader-gui)
- Central hub dashboard (linux-system-guis)

%prep
%autosetup -n %{name}-%{version}

%build
# Build wheels for core library and applications
mkdir -p dist
python3 -m build --wheel --no-isolation --outdir dist packages/core
for app in launcher fstab-gui udev-gui systemd-gui usermgmt-gui sudoers-gui journal-gui sysctl-gui permissions-gui bootloader-gui; do
    python3 -m build --wheel --no-isolation --outdir dist "apps/$app"
done

%install
for whl in dist/*.whl; do
    python3 -m installer --destdir=%{buildroot} "$whl"
done

# If python3 -m installer placed files under /usr/local
if [ -d %{buildroot}/usr/local ]; then
    mkdir -p %{buildroot}%{_prefix}
    cp -r %{buildroot}/usr/local/* %{buildroot}%{_prefix}/ 2>/dev/null || true
    rm -rf %{buildroot}/usr/local
fi

# Install desktop entry files
mkdir -p %{buildroot}%{_datadir}/applications
cp packaging/desktop/*.desktop %{buildroot}%{_datadir}/applications/

# Install scalable application icon
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
cp packaging/desktop/icons/linux-system-guis.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/

%files
%license LICENSE
%doc README.md
%{_bindir}/linux-system-guis
%{_bindir}/fstab-gui
%{_bindir}/udev-gui
%{_bindir}/systemd-gui
%{_bindir}/usermgmt-gui
%{_bindir}/sudoers-gui
%{_bindir}/journal-gui
%{_bindir}/sysctl-gui
%{_bindir}/permissions-gui
%{_bindir}/bootloader-gui
%{python3_sitelib}/*
%{_datadir}/applications/*.desktop
%{_datadir}/icons/hicolor/scalable/apps/linux-system-guis.svg

%changelog
* Sun Oct 11 2026 Ben Davison <benjdavison02@gmail.com> - 0.1.0-1
- Initial packaging release for Fedora / RHEL / openSUSE
