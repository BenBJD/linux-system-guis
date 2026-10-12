"""Backend queries and operations for Linux users and groups."""

from dataclasses import dataclass, field
import grp
import pwd
from linux_gui_core.runner.executor import ExecutionResult, SafeExecutor


@dataclass
class UserInfo:
    username: str
    uid: int
    gid: int
    gecos: str
    home: str
    shell: str
    groups: list[str] = field(default_factory=list)
    is_system_user: bool = False


class UserManagementBackend:
    @staticmethod
    def list_users(include_system: bool = False) -> list[UserInfo]:
        """Fetch users from system pwd and grp databases."""
        users: list[UserInfo] = []
        all_groups = grp.getgrall()

        for p in pwd.getpwall():
            is_sys = p.pw_uid < 1000 and p.pw_name != "root"
            if not include_system and is_sys:
                continue

            # Find all groups user belongs to
            user_groups = []
            for g in all_groups:
                if p.pw_name in g.gr_mem or p.pw_gid == g.gr_gid:
                    user_groups.append(g.gr_name)

            users.append(
                UserInfo(
                    username=p.pw_name,
                    uid=p.pw_uid,
                    gid=p.pw_gid,
                    gecos=p.pw_gecos,
                    home=p.pw_dir,
                    shell=p.pw_shell,
                    groups=sorted(list(set(user_groups))),
                    is_system_user=is_sys,
                )
            )
        return sorted(users, key=lambda u: u.uid)

    @staticmethod
    def list_all_groups() -> list[str]:
        return sorted([g.gr_name for g in grp.getgrall()])

    @staticmethod
    def build_add_user_cmd(
        username: str,
        shell: str = "/bin/bash",
        groups: list[str] | None = None,
        gecos: str = "",
        create_home: bool = True,
    ) -> str:
        tokens = ["useradd"]
        if create_home:
            tokens.append("-m")
        if shell:
            tokens.extend(["-s", shell])
        if gecos.strip():
            tokens.extend(["-c", f'"{gecos.strip()}"'])
        if groups:
            tokens.extend(["-G", ",".join(groups)])
        tokens.append(username)
        return f"sudo {' '.join(tokens)}"

    @staticmethod
    def build_modify_groups_cmd(username: str, groups: list[str]) -> str:
        if not groups:
            return f"sudo usermod -G '' {username}"
        return f"sudo usermod -G {','.join(groups)} {username}"

    @staticmethod
    def build_del_user_cmd(username: str, remove_home: bool = True) -> str:
        flag = "-r " if remove_home else ""
        return f"sudo userdel {flag}{username}"

    @staticmethod
    def execute_command_string(cmd_str: str) -> ExecutionResult:
        # Strip leading sudo if present, run elevated
        clean = cmd_str
        if clean.startswith("sudo "):
            clean = clean[5:]
        parts = clean.split()
        return SafeExecutor.run_command(parts, elevated=True)
