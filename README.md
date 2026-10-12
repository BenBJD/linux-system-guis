# Linux System GUIs

An educational, transparent, and safe desktop GUI suite for low-level Linux administration.

Some Linux configuration tasks (such as managing disk mounts, kernel device rules, systemd units, sudoers rules, and boot parameters) lack a GUI and instead require editing configuration files or memorising terminal commands. For new users, this introduces two major problems:
1. A syntax mistake in `/etc/fstab` or `/etc/sudoers` can cause boot failure or lock out root access.
2. Traditional graphical tools often hide what they are doing, preventing users from learning the underlying commands and file formats.

This suite aims to be a useful GUI, as well as a tutor:
- Every option, checkbox, and input dynamically updates a visible syntax/command preview banner at the top of the window.
- Every toggle explains what the option does, kernel/system implications, security risks, and example usage.
- Full colorized diffs and sanity checks are shown before changes are written. Dry-run verifications and automatic timestamped backups are created prior to modification.
- "Copy Line / Command" buttons let users inspect or run commands manually in their terminal.

---

## Suite Applications

| Application                   | Command             | Description                                                                                                                                          |
|-------------------------------|---------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Launcher**                  | `linux-system-guis` | Central dashboard to browse, search, and launch all utilities                                                                                        |
| **fstab Editor**              | `fstab-gui`         | Visual manager for `/etc/fstab` with live entry preview, mount options (`noatime`, `nosuid`, `nofail`), and `mount -fa` dry run                      |
| **udev Rule Builder**         | `udev-gui`          | Interactive device rule builder for `/etc/udev/rules.d/` (`idVendor`, `MODE="0666"`, `TAG+="uaccess"`) with `udevadm` reload helper                  |
| **systemd Manager**           | `systemd-gui`       | Service and timer explorer (`systemctl`) with schedule generator (`OnCalendar`), friendly status tags, and unit management                           |
| **User & Group Security**     | `usermgmt-gui`      | User management and group membership editor (`sudo`, `docker`, `dialout`, `audio`) with real-time `usermod` preview                                  |
| **Sudoers Configuration**     | `sudoers-gui`       | Visually configure `/etc/sudoers.d/` privileges, user/group rules, NOPASSWD toggles, and strict validation via `visudo -c -f`                        |
| **System Logs**               | `journal-gui`       | Filter `journalctl` by boot session (`-b`), unit (`-u`), priority (`-p`), and regex (`-g`), plus log maintenance (`--vacuum-time`, `--vacuum-size`)  |
| **Kernel Parameters**         | `sysctl-gui`        | Explore and tune kernel parameters (`sysctl -w`, `/etc/sysctl.d/`) with plain-English explanations of swappiness, BBR, and inotify                   |
| **Advanced File Permissions** | `permissions-gui`   | Visual editor for POSIX ACLs (`getfacl`/`setfacl`, default directory ACLs) and file attributes (`chattr`/`lsattr` immutable `+i`)                    |
| **Bootloader Configuration**  | `bootloader-gui`    | Configure GRUB (`/etc/default/grub` + `grub-mkconfig`) & systemd-boot timeout, default entries, and kernel recovery arguments (`nomodeset`, `quiet`) |

---

## Installation

### Uv
TODO

### Arch Linux
TODO

### Ubuntu/Debian
TODO

### RHEL/Fedora
TODO

## Contributing

The design decisions and tooltips are from man pages and the Arch wiki, but still very much opinionated, so please feel free to open an issue or PR to suggest improvements.

This project uses [uv](https://docs.astral.sh/uv/) for workspace management.

### Sync Dependencies
```bash
uv sync
```

### Run Applications

Launch the central dashboard:
```bash
uv run linux-system-guis
```

Or run any tool directly:
```bash
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

### Running Tests

Execute the automated test suite with `uv`:
```bash
uv run pytest
```
