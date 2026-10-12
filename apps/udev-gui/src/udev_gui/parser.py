"""Parser and serializer for systemd/udev rules files."""

from dataclasses import dataclass, field
import glob
import os
import re


@dataclass
class UdevRule:
    raw_line: str = ""
    is_comment: bool = False
    # Core Match keys
    action: str = ""          # add, remove, change
    subsystem: str = ""       # usb, tty, net, input, block
    subsystem_key: str = "SUBSYSTEM" # SUBSYSTEM or SUBSYSTEMS
    kernel: str = ""          # e.g. ttyUSB*, sd*
    kernel_key: str = "KERNEL"
    vendor_id: str = ""       # ATTR{idVendor} or ATTRS{idVendor}
    vendor_key: str = "ATTR{idVendor}"
    product_id: str = ""      # ATTR{idProduct} or ATTRS{idProduct}
    product_key: str = "ATTR{idProduct}"
    
    # Core Assignment keys
    mode: str = ""            # MODE="0666"
    group: str = ""           # GROUP="plugdev"
    owner: str = ""           # OWNER="username"
    symlink: str = ""         # SYMLINK+="mydevice"
    tag_uaccess: bool = False # TAG+="uaccess"
    run_cmd: str = ""         # RUN+="..."

    # Advanced / Custom tokens (e.g. ATTR{power/wakeup}="disabled", OPTIONS+=..., GOTO=...)
    extra_tokens: list[str] = field(default_factory=list)

    def to_line(self) -> str:
        if self.is_comment or self.raw_line.startswith("#"):
            return self.raw_line

        tokens = []
        if self.action:
            tokens.append(f'ACTION=="{self.action}"')
        if self.subsystem:
            tokens.append(f'{self.subsystem_key}=="{self.subsystem}"')
        if self.kernel:
            tokens.append(f'{self.kernel_key}=="{self.kernel}"')
        if self.vendor_id:
            tokens.append(f'{self.vendor_key}=="{self.vendor_id}"')
        if self.product_id:
            tokens.append(f'{self.product_key}=="{self.product_id}"')

        if self.mode:
            tokens.append(f'MODE="{self.mode}"')
        if self.group:
            tokens.append(f'GROUP="{self.group}"')
        if self.owner:
            tokens.append(f'OWNER="{self.owner}"')
        if self.symlink:
            tokens.append(f'SYMLINK+="{self.symlink}"')
        if self.tag_uaccess:
            tokens.append('TAG+="uaccess"')
        if self.run_cmd:
            tokens.append(f'RUN+="{self.run_cmd}"')

        # Append extra tokens (preserving attributes like ATTR{power/wakeup}="disabled")
        tokens.extend(self.extra_tokens)

        return ", ".join(tokens)


class UdevParser:
    # Matches KEY OPERATOR "VALUE" or KEY OPERATOR VALUE (including keys with slashes like ATTR{power/wakeup})
    TOKEN_PATTERN = re.compile(
        r'([A-Za-z0-9_{}/.:-]+)\s*(==|!=|\+=|:=|=)\s*(?:"([^"]*)"|([A-Za-z0-9_.-]+))'
    )

    @classmethod
    def parse_rule_line(cls, line: str) -> UdevRule:
        rule = UdevRule(raw_line=line.strip())
        if not line.strip() or line.strip().startswith("#"):
            rule.is_comment = True
            return rule

        matches = cls.TOKEN_PATTERN.findall(line)
        for match in matches:
            key = match[0]
            op = match[1]
            val = match[2] if match[2] else match[3]

            if key == "ACTION" and op == "==":
                rule.action = val
            elif key in ("SUBSYSTEM", "SUBSYSTEMS") and op == "==":
                rule.subsystem = val
                rule.subsystem_key = key
            elif key in ("KERNEL", "KERNELS") and op == "==":
                rule.kernel = val
                rule.kernel_key = key
            elif key in ("ATTR{idVendor}", "ATTRS{idVendor}") and op == "==":
                rule.vendor_id = val
                rule.vendor_key = key
            elif key in ("ATTR{idProduct}", "ATTRS{idProduct}") and op == "==":
                rule.product_id = val
                rule.product_key = key
            elif key == "MODE" and op in ("=", ":="):
                rule.mode = val
            elif key == "GROUP" and op in ("=", ":="):
                rule.group = val
            elif key == "OWNER" and op in ("=", ":="):
                rule.owner = val
            elif key == "SYMLINK" and op in ("=", "+="):
                rule.symlink = val
            elif key == "TAG" and op in ("=", "+=") and val == "uaccess":
                rule.tag_uaccess = True
            elif key == "RUN" and op in ("=", "+="):
                rule.run_cmd = val
            else:
                # Retain arbitrary / advanced tokens (like ATTR{power/wakeup}="disabled")
                formatted = f'{key}{op}"{val}"'
                rule.extra_tokens.append(formatted)

        return rule

    @staticmethod
    def list_rules_files(rules_dir: str = "/etc/udev/rules.d") -> list[str]:
        if not os.path.exists(rules_dir):
            return []
        return sorted(glob.glob(os.path.join(rules_dir, "*.rules")))
