# Linux System GUIs

A desktop GUI suite for low-level Linux administration that shows the commands and configuration files it writes.

Low-level Linux tasks such as managing disk mounts, kernel device rules, systemd units, sudoers rules, and boot parameters usually require editing configuration files or running terminal commands by hand:
1. A syntax mistake in `/etc/fstab` or `/etc/sudoers` can prevent a system from booting or lock out root access.
2. Traditional graphical tools hide what they are doing, so users never see the underlying commands or file formats.

Each tool in this suite previews every change before writing to disk:
- Changing any option, checkbox, or input updates a live command or config-line preview banner at the top of the window.
- Tooltips explain what each option does, its kernel or system effect, security risks, and example usage, with links to the relevant manual pages.
- Before applying changes, the tool shows a colorized diff, runs dry-run checks where supported, and creates a timestamped backup.
- A "Copy Line" button copies the generated line or command to the clipboard so you can inspect or run it in a terminal.

---

## Suite applications

| Application                   | Command             | Description                                                                                                                                         |
|-------------------------------|---------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| **Launcher**                  | `linux-system-guis` | Central dashboard to browse, filter, and launch all utilities                                                                                       |
| **Device Manager**            | `device-gui`        | Hardware and driver inspector (`lspci`, `lsusb`, `modinfo`, `dkms`) with property inspection and driver loading                                     |
| **fstab Editor**              | `fstab-gui`         | Visual editor for `/etc/fstab` with live entry preview, mount options (`noatime`, `nosuid`, `nofail`), and `mount -fa` dry runs                     |
| **udev Rule Builder**         | `udev-gui`          | Device rule builder for `/etc/udev/rules.d/` (`idVendor`, `MODE="0660"`, `TAG+="uaccess"`) with `udevadm` reload helper                             |
| **systemd Manager**           | `systemd-gui`       | Service and timer explorer (`systemctl`) with schedule generator (`OnCalendar`), status tags, and unit management                                   |
| **User and Group Security**   | `usermgmt-gui`      | User account and group membership editor (`sudo`, `docker`, `dialout`, `audio`) with live `usermod` preview                                         |
| **Sudoers Configuration**     | `sudoers-gui`       | Editor for `/etc/sudoers.d/` privileges, user and group rules, `NOPASSWD` toggles, and `visudo -c -f` validation                                    |
| **System Logs**               | `journal-gui`       | Filter `journalctl` by boot session (`-b`), unit (`-u`), priority (`-p`), and regex (`-g`), and vacuum old logs (`--vacuum-time`, `--vacuum-size`) |
| **Kernel Parameters**         | `sysctl-gui`        | Explore and tune kernel parameters (`sysctl -w`, `/etc/sysctl.d/`) with explanations of swappiness, BBR, and inotify                                |
| **Advanced File Permissions** | `permissions-gui`   | Visual editor for POSIX ACLs (`getfacl`, `setfacl`, default directory ACLs) and file attributes (`chattr`, `lsattr`, immutable `+i`)                |
| **Bootloader Configuration**  | `bootloader-gui`    | Configure GRUB (`/etc/default/grub` and `grub-mkconfig`) and systemd-boot timeouts, default entries, and kernel arguments (`nomodeset`, `quiet`)    |

---

## Installation

See [packaging/README.md](packaging/README.md) for Arch Linux, Debian/Ubuntu, and Fedora/RHEL package build instructions.

For local development, this project uses [uv](https://docs.astral.sh/uv/) for workspace management.

## Contributing

The defaults and tooltips come from manual pages and the Arch Wiki, but many are opinionated. Open an issue or pull request to suggest changes.

### Sync dependencies
```bash
uv sync
```

### Run applications

Launch the central dashboard:
```bash
uv run linux-system-guis
```

Or run any tool directly:
```bash
uv run device-gui
uv run fstab-gui
uv run udev-gui
uv run systemd-gui
uv run usermgmt-gui
uv run sudoers-gui
uv run journal-gui
uv run sysctl-gui
uv run permissions-gui
uv run bootloader-gui
```

### Running tests

Run the test suite with `uv`:
```bash
uv run pytest
```
