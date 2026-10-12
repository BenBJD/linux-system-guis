"""Parser and serializer for /etc/fstab configuration files."""

from dataclasses import dataclass, field
import os


@dataclass
class FstabEntry:
    fs_spec: str = ""       # e.g. UUID=1234 or /dev/sda1
    mount_point: str = ""   # e.g. / or /home or /mnt/backup
    vfstype: str = "ext4"   # e.g. ext4, btrfs, vfat, xfs
    options: list[str] = field(default_factory=lambda: ["defaults"])
    dump: int = 0           # 0 or 1
    passno: int = 0         # 0, 1, or 2
    raw_comment: str | None = None

    def to_line(self) -> str:
        """Formats the entry into a standard fstab line."""
        if self.raw_comment:
            return self.raw_comment
        opts_str = ",".join(self.options) if self.options else "defaults"
        return f"{self.fs_spec:<42} {self.mount_point:<18} {self.vfstype:<8} {opts_str:<24} {self.dump} {self.passno}"


class FstabParser:
    @staticmethod
    def parse_file(path: str = "/etc/fstab") -> list[FstabEntry]:
        """Parses /etc/fstab into a list of FstabEntry objects."""
        if not os.path.exists(path):
            return []

        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    entries.append(FstabEntry(raw_comment=line.rstrip("\n")))
                    continue

                parts = line.split()
                if len(parts) >= 4:
                    fs_spec = parts[0]
                    mount_point = parts[1]
                    vfstype = parts[2]
                    options = parts[3].split(",")
                    dump = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
                    passno = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
                    entries.append(
                        FstabEntry(
                            fs_spec=fs_spec,
                            mount_point=mount_point,
                            vfstype=vfstype,
                            options=options,
                            dump=dump,
                            passno=passno,
                        )
                    )
        return entries

    @staticmethod
    def serialize_entries(entries: list[FstabEntry]) -> str:
        """Serializes entries into full file content with standard header."""
        lines = []
        for e in entries:
            lines.append(e.to_line())
        return "\n".join(lines) + "\n"
