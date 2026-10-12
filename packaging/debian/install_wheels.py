#!/usr/bin/env python3
"""Custom wheel installer helper for Debian packages.

Ensures wheels are installed strictly to /usr/bin and the Debian system
dist-packages directory (/usr/lib/python3/dist-packages) rather than
the Debian default /usr/local prefix.
"""

import glob
import os
import sys
import sysconfig
from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.sources import WheelFile
from installer.utils import get_launcher_kind


def main():
    destdir = sys.argv[1] if len(sys.argv) > 1 else "debian/linux-system-guis"
    wheels_dir = sys.argv[2] if len(sys.argv) > 2 else "debian/dist"

    scheme_name = (
        "deb_system" if "deb_system" in sysconfig.get_scheme_names() else "posix_prefix"
    )
    scheme_dict = sysconfig.get_paths(
        scheme_name, vars={"base": "/usr", "platbase": "/usr"}
    )
    scheme_dict["headers"] = "/usr/include"

    # Enforce standard /usr paths
    scheme_dict["scripts"] = "/usr/bin"
    if "deb_system" in sysconfig.get_scheme_names():
        scheme_dict["purelib"] = "/usr/lib/python3/dist-packages"
        scheme_dict["platlib"] = "/usr/lib/python3/dist-packages"

    wheel_files = sorted(glob.glob(os.path.join(wheels_dir, "*.whl")))
    if not wheel_files:
        print(f"Error: No wheels found in {wheels_dir}", file=sys.stderr)
        sys.exit(1)

    for wheel_path in wheel_files:
        print(f"Installing {os.path.basename(wheel_path)} into {destdir}...")
        with WheelFile.open(wheel_path) as source:
            destination = SchemeDictionaryDestination(
                scheme_dict=scheme_dict,
                interpreter="/usr/bin/python3",
                script_kind=get_launcher_kind(),
                destdir=destdir,
            )
            install(source, destination, {})


if __name__ == "__main__":
    main()
