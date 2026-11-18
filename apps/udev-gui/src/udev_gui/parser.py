"""Parser and serializer for systemd/udev rules files."""

from dataclasses import dataclass, field
import glob
import os
import re


@dataclass
class UdevRule:
    raw_line: str = ""
    is_comment: bool = False
    # Core Match keys (==)
    action: str = ""                 # add, remove, change, bind, unbind
    subsystem: str = ""              # usb, hidraw, input, tty, net, block, drm, misc...
    subsystem_key: str = "SUBSYSTEM" # SUBSYSTEM or SUBSYSTEMS
    kernel: str = ""                 # e.g. hidraw*, event*, ttyUSB*, uinput
    kernel_key: str = "KERNEL"       # KERNEL or KERNELS
    driver: str = ""                 # e.g. usbhid, hid-multitouch, i2c_hid_acpi
    driver_key: str = "DRIVER"       # DRIVER or DRIVERS
    vendor_id: str = ""              # ATTR{idVendor} or ATTRS{idVendor}
    vendor_key: str = "ATTR{idVendor}"
    product_id: str = ""             # ATTR{idProduct} or ATTRS{idProduct}
    product_key: str = "ATTR{idProduct}"

    # Core Assignment keys (=, +=, :=)
    mode: str = ""                   # MODE="0666" / "0660"
    group: str = ""                  # GROUP="plugdev" / "input" / "dialout"
    owner: str = ""                  # OWNER="username"
    symlink: str = ""                # SYMLINK+="mydevice"
    tag_uaccess: bool = False        # TAG+="uaccess"
    run_cmd: str = ""                # RUN+="..." or RUN{builtin}+="..."
    run_key: str = "RUN"             # RUN, RUN{program}, or RUN{builtin}
    run_op: str = "+="               # +=, =, or :=
    systemd_wants: str = ""          # ENV{SYSTEMD_WANTS}+="my.service"

    # Additional / Custom tokens (e.g. ATTR{power/wakeup}="disabled", ATTRS{name}=="*Touchpad*", OPTIONS+=...)
    extra_tokens: list[str] = field(default_factory=list)

    _SINGLE_TOKEN_RE = re.compile(
        r'^([A-Za-z0-9_{}/.:-]+)\s*(==|!=|\+=|-=|:=|=)\s*([ei])?(?:"((?:\\.|[^"\\])*)"|([^\s,]+))$'
    )

    def get_extra_value(
        self,
        keys: tuple[str, ...] | str,
        ops: tuple[str, ...] | None = None,
    ) -> str:
        """Find the first matching token in ``extra_tokens`` and return its string value (or ``""``)."""
        key_tuple = (keys,) if isinstance(keys, str) else keys
        for token in self.extra_tokens:
            m = self._SINGLE_TOKEN_RE.match(token.strip())
            if not m:
                continue
            k, op, _prefix, q_val, bare_val = m.groups()
            val = q_val if q_val is not None else (bare_val or "")
            if k in key_tuple and (ops is None or op in ops):
                return val
        return ""

    def set_extra_value(
        self,
        key: str,
        op: str,
        value: str,
        replace_keys: tuple[str, ...] | None = None,
        ops: tuple[str, ...] | None = None,
    ) -> None:
        """Insert, update, or remove (when ``value`` is empty) a structured token in ``extra_tokens``."""
        target_keys = replace_keys or (key,)
        new_token = f'{key}{op}"{value}"'
        updated: list[str] = []
        replaced = False

        for token in self.extra_tokens:
            m = self._SINGLE_TOKEN_RE.match(token.strip())
            if m:
                k, tok_op, *_ = m.groups()
                if k in target_keys and (ops is None or tok_op in ops):
                    if value and not replaced:
                        updated.append(new_token)
                        replaced = True
                    continue
            updated.append(token)

        if value and not replaced:
            updated.append(new_token)

        self.extra_tokens = updated

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
        if self.driver:
            tokens.append(f'{self.driver_key}=="{self.driver}"')
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
        if self.systemd_wants:
            if not any("TAG" in t and "systemd" in t for t in self.extra_tokens):
                tokens.append('TAG+="systemd"')
            tokens.append(f'ENV{{SYSTEMD_WANTS}}+="{self.systemd_wants}"')
        if self.run_cmd:
            rk = self.run_key or "RUN"
            rop = self.run_op or "+="
            tokens.append(f'{rk}{rop}"{self.run_cmd}"')

        # Append extra tokens (preserving attributes like ATTR{power/wakeup}="disabled", ATTRS{name}=="...")
        tokens.extend(self.extra_tokens)

        return ", ".join(tokens)


class UdevParser:
    # Matches KEY OPERATOR [e|i]"VALUE" (supporting escaped \" inside quotes) or KEY OPERATOR VALUE
    TOKEN_PATTERN = re.compile(
        r'([A-Za-z0-9_{}/.:-]+)\s*(==|!=|\+=|-=|:=|=)\s*([ei])?(?:"((?:\\.|[^"\\])*)"|([^\s,]+))'
    )

    @classmethod
    def parse_rule_line(cls, line: str) -> UdevRule:
        rule = UdevRule(raw_line=line.strip())
        if not line.strip() or line.strip().startswith("#"):
            rule.is_comment = True
            return rule

        for match in cls.TOKEN_PATTERN.finditer(line):
            key, op, prefix, quoted_val, bare_val = match.groups()
            val = quoted_val if quoted_val is not None else (bare_val or "")
            prefix_str = prefix or ""

            if key == "ACTION" and op == "==" and not prefix_str:
                rule.action = val
            elif key in ("SUBSYSTEM", "SUBSYSTEMS") and op == "==" and not prefix_str:
                rule.subsystem = val
                rule.subsystem_key = key
            elif key in ("KERNEL", "KERNELS") and op == "==" and not prefix_str:
                rule.kernel = val
                rule.kernel_key = key
            elif key in ("DRIVER", "DRIVERS") and op == "==" and not prefix_str:
                rule.driver = val
                rule.driver_key = key
            elif key in ("ATTR{idVendor}", "ATTRS{idVendor}") and op == "==" and not prefix_str:
                rule.vendor_id = val
                rule.vendor_key = key
            elif key in ("ATTR{idProduct}", "ATTRS{idProduct}") and op == "==" and not prefix_str:
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
            elif key == "ENV{SYSTEMD_WANTS}" and op in ("=", "+="):
                rule.systemd_wants = val
            elif key in ("RUN", "RUN{program}", "RUN{builtin}") and op in ("=", "+=", ":="):
                rule.run_cmd = val
                rule.run_key = key
                rule.run_op = op
            else:
                formatted = f'{key}{op}{prefix_str}"{val}"'
                rule.extra_tokens.append(formatted)

        # If ENV{SYSTEMD_WANTS} was parsed, clean redundant TAG+="systemd" from extra_tokens
        # since to_line() emits TAG+="systemd" automatically when systemd_wants is set
        if rule.systemd_wants:
            rule.extra_tokens = [
                t for t in rule.extra_tokens if t not in ('TAG+="systemd"', 'TAG="systemd"')
            ]

        return rule

    @staticmethod
    def list_rules_files(rules_dir: str = "/etc/udev/rules.d") -> list[str]:
        if not os.path.exists(rules_dir):
            return []
        return sorted(glob.glob(os.path.join(rules_dir, "*.rules")))
