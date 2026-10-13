"""Hardware device scanner, driver inspector, and sysfs backend for Linux Device Manager."""

from dataclasses import dataclass, field
import glob
import os
import platform
import re
import shutil
import subprocess
from typing import Any


@dataclass
class DeviceInfo:
    """Represents a unified hardware device or component on the system."""

    id: str
    name: str
    category: str
    category_icon: str
    bus_type: str = "unknown"
    vendor_name: str = ""
    vendor_id: str = ""
    product_name: str = ""
    product_id: str = ""
    subsystem_vendor: str = ""
    subsystem_device: str = ""
    revision: str = ""
    pci_slot: str = ""
    usb_bus: str = ""
    usb_dev: str = ""
    usb_port: str = ""
    usb_speed: str = ""
    device_node: str = ""
    sysfs_path: str = ""
    modalias: str = ""
    driver_name: str = ""
    driver_type: str = "none"  # "dkms", "module", "builtin", "none"
    driver_type_label: str = "Driverless / Direct Access"
    driver_module_path: str = ""
    driver_memory_size: str = ""
    driver_used_by: list[str] = field(default_factory=list)
    driver_description: str = ""
    driver_version: str = ""
    driver_license: str = ""
    power_state: str = ""
    wakeup_enabled: str = ""
    parent_id: str = ""
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class SystemSummary:
    """High-level hardware overview collected via sysfs, DMI, and inxi."""

    hostname: str = ""
    distro: str = ""
    kernel: str = ""
    arch: str = ""
    desktop: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    memory_total: str = ""
    memory_used: str = ""
    motherboard: str = ""
    bios_version: str = ""
    bios_date: str = ""
    graphics_summary: str = ""
    device_count_total: int = 0
    device_counts_by_category: dict[str, int] = field(default_factory=dict)
    raw_inxi: str = ""


# Standard Windows-style device category metadata (name, icon, sort order)
CATEGORY_METADATA: dict[str, tuple[str, int]] = {
    "Display Adapters": ("🖥️", 10),
    "Audio & Sound Devices": ("🔊", 20),
    "Network Adapters": ("🌐", 30),
    "Disk Drives": ("💾", 40),
    "Storage Controllers": ("🗄️", 50),
    "Human Interface Devices (HID)": ("⌨️", 60),
    "Universal Serial Bus (USB)": ("🔌", 70),
    "Processors (CPU)": ("⚙️", 80),
    "Bluetooth & Wireless": ("📡", 90),
    "Cameras & Video Capture": ("📷", 100),
    "Ports (COM & Serial)": ("📟", 110),
    "System & Motherboard Devices": ("🧩", 120),
    "Other Devices": ("❓", 130),
}


class DeviceManagerBackend:
    """Backend service for probing Linux devices, drivers, sysfs, and DKMS."""

    def __init__(self):
        self.dkms_modules: set[str] = set()
        self.proc_modules: dict[str, dict[str, Any]] = {}
        self.builtin_modules: set[str] = set()
        self._driver_cache: dict[str, dict[str, Any]] = {}

    def refresh_driver_database(self) -> None:
        """Loads active loaded modules, DKMS registrations, and built-in kernel modules."""
        self.dkms_modules = self._load_dkms_modules()
        self.proc_modules = self._load_proc_modules()
        self.builtin_modules = self._load_builtin_modules()
        self._driver_cache.clear()

    def _load_dkms_modules(self) -> set[str]:
        """Collects the set of registered DKMS module names."""
        mods = set()
        if shutil.which("dkms"):
            try:
                out = subprocess.check_output(
                    ["dkms", "status"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=4,
                )
                for line in out.strip().splitlines():
                    if line and "/" in line:
                        mods.add(line.split("/")[0].strip())
            except Exception:
                pass

        # Fallback check /var/lib/dkms directory
        dkms_dir = "/var/lib/dkms"
        if os.path.isdir(dkms_dir):
            try:
                for entry in os.listdir(dkms_dir):
                    if os.path.isdir(os.path.join(dkms_dir, entry)) and entry != "dkms_dbversion":
                        mods.add(entry)
            except Exception:
                pass

        return mods

    def _load_proc_modules(self) -> dict[str, dict[str, Any]]:
        """Reads /proc/modules to map loaded module names to memory size and references."""
        result = {}
        if os.path.exists("/proc/modules"):
            try:
                with open("/proc/modules", "r", errors="ignore") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            size_bytes = int(parts[1]) if parts[1].isdigit() else 0
                            # Form friendly size
                            if size_bytes >= 1024 * 1024:
                                size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                            else:
                                size_str = f"{size_bytes / 1024:.1f} KB"

                            uses = parts[3].rstrip(",").split(",") if len(parts) > 3 and parts[3] != "-" else []
                            result[name] = {
                                "size": size_str,
                                "used_by": uses,
                            }
            except Exception:
                pass
        return result

    def _load_builtin_modules(self) -> set[str]:
        """Reads modules.builtin for the running kernel."""
        builtins = set()
        uname_r = platform.release()
        builtin_file = f"/lib/modules/{uname_r}/modules.builtin"
        if os.path.exists(builtin_file):
            try:
                with open(builtin_file, "r", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            mod = os.path.splitext(os.path.basename(line))[0]
                            mod = mod.replace("-", "_")
                            builtins.add(mod)
            except Exception:
                pass
        return builtins

    def inspect_driver(self, driver_name: str) -> dict[str, Any]:
        """Analyzes a driver/module name to determine whether it is DKMS, a loadable kernel module, or built-in."""
        if not driver_name:
            return {
                "name": "",
                "type": "none",
                "label": "Driverless / Direct Access",
                "path": "",
                "size": "",
                "used_by": [],
                "version": "",
                "license": "",
                "description": "",
            }

        norm_name = driver_name.replace("-", "_")
        if norm_name in self._driver_cache:
            return self._driver_cache[norm_name]

        info: dict[str, Any] = {
            "name": driver_name,
            "type": "module",
            "label": "Active (Kernel Module)",
            "path": "",
            "size": "",
            "used_by": [],
            "version": "",
            "license": "",
            "description": "",
        }

        # Check proc_modules for memory size and dependents
        if norm_name in self.proc_modules:
            pinfo = self.proc_modules[norm_name]
            info["size"] = pinfo["size"]
            info["used_by"] = pinfo["used_by"]
        elif driver_name in self.proc_modules:
            pinfo = self.proc_modules[driver_name]
            info["size"] = pinfo["size"]
            info["used_by"] = pinfo["used_by"]

        # 1. Check DKMS
        if driver_name in self.dkms_modules or norm_name in self.dkms_modules:
            info["type"] = "dkms"
            info["label"] = "Active (DKMS Module)"

        # 2. Check if built-in
        if driver_name in self.builtin_modules or norm_name in self.builtin_modules:
            info["type"] = "builtin"
            info["label"] = "Kernel Built-in"
            info["path"] = "(builtin)"

        # 3. Query modinfo if available for disk path, version, license, description
        if shutil.which("modinfo") and info["type"] != "builtin":
            try:
                res = subprocess.run(
                    ["modinfo", driver_name],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=3,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        if ":" in line:
                            field_name, val = line.split(":", 1)
                            field_name = field_name.strip()
                            val = val.strip()
                            if field_name == "filename":
                                info["path"] = val
                                if val == "(builtin)":
                                    info["type"] = "builtin"
                                    info["label"] = "Kernel Built-in"
                                elif "dkms" in val.lower() or "updates" in val.lower():
                                    info["type"] = "dkms"
                                    info["label"] = "Active (DKMS Module)"
                            elif field_name == "version":
                                info["version"] = val
                            elif field_name == "license":
                                info["license"] = val
                            elif field_name == "description":
                                info["description"] = val
            except Exception:
                pass

        self._driver_cache[norm_name] = info
        return info

    def scan_pci_devices(self) -> list[DeviceInfo]:
        """Parses PCI devices using lspci or /sys/bus/pci/devices/."""
        devices: list[DeviceInfo] = []
        if shutil.which("lspci"):
            try:
                out = subprocess.check_output(
                    ["lspci", "-vmm", "-knn"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=6,
                )
                cur: dict[str, str] = {}
                for line in out.splitlines():
                    line = line.strip()
                    if not line:
                        if cur:
                            dev = self._build_pci_device(cur)
                            if dev:
                                devices.append(dev)
                            cur = {}
                        continue
                    if ":" in line:
                        k, v = line.split(":", 1)
                        cur[k.strip()] = v.strip()
                if cur:
                    dev = self._build_pci_device(cur)
                    if dev:
                        devices.append(dev)
                return devices
            except Exception:
                pass

        # Fallback: scan /sys/bus/pci/devices
        pci_base = "/sys/bus/pci/devices"
        if os.path.exists(pci_base):
            for slot in sorted(os.listdir(pci_base)):
                p = os.path.join(pci_base, slot)
                dev = self._build_sysfs_pci_device(slot, p)
                if dev:
                    devices.append(dev)

        return devices

    def _build_pci_device(self, data: dict[str, str]) -> DeviceInfo | None:
        slot = data.get("Slot", "")
        if not slot:
            return None

        # Clean "Advanced Micro Devices, Inc. [AMD] [1022]" -> name & vendor id
        raw_vendor = data.get("Vendor", "")
        raw_device = data.get("Device", "")
        raw_class = data.get("Class", "")

        vendor_name, vendor_id = self._extract_name_and_hex(raw_vendor)
        device_name, device_id = self._extract_name_and_hex(raw_device)
        class_name, class_id = self._extract_name_and_hex(raw_class)

        # Categorize by class
        category = self._categorize_pci_class(class_name, class_id)
        icon, _ = CATEGORY_METADATA.get(category, ("🧩", 120))

        driver_name = data.get("Driver", "")
        drv_info = self.inspect_driver(driver_name)

        sysfs_path = f"/sys/bus/pci/devices/0000:{slot}" if not slot.startswith("0000:") else f"/sys/bus/pci/devices/{slot}"
        if not os.path.exists(sysfs_path):
            sysfs_path = f"/sys/bus/pci/devices/{slot}"

        # Additional sysfs attributes
        power_state = self._read_sysfs(sysfs_path, "power/runtime_status")
        wakeup = self._read_sysfs(sysfs_path, "power/wakeup")
        modalias = self._read_sysfs(sysfs_path, "modalias")

        # Find associated /dev node (e.g. /dev/dri/cardX or /dev/nvmeXn1)
        dev_node = self._find_dev_node_for_sysfs(sysfs_path)

        friendly_title = device_name or class_name
        if vendor_name and not friendly_title.startswith(vendor_name):
            friendly_title = f"{vendor_name} {friendly_title}"

        props = dict(data)
        if modalias:
            props["MODALIAS"] = modalias
        if dev_node:
            props["DEVNODE"] = dev_node

        return DeviceInfo(
            id=f"pci:{slot}",
            name=friendly_title,
            category=category,
            category_icon=icon,
            bus_type="pci",
            vendor_name=vendor_name,
            vendor_id=vendor_id,
            product_name=device_name,
            product_id=device_id,
            subsystem_vendor=self._extract_name_and_hex(data.get("SVendor", ""))[1],
            subsystem_device=self._extract_name_and_hex(data.get("SDevice", ""))[1],
            revision=data.get("Rev", ""),
            pci_slot=slot,
            device_node=dev_node,
            sysfs_path=sysfs_path,
            modalias=modalias,
            driver_name=driver_name,
            driver_type=drv_info["type"],
            driver_type_label=drv_info["label"],
            driver_module_path=drv_info["path"],
            driver_memory_size=drv_info["size"],
            driver_used_by=drv_info["used_by"],
            driver_description=drv_info["description"],
            driver_version=drv_info["version"],
            driver_license=drv_info["license"],
            power_state=power_state,
            wakeup_enabled=wakeup,
            parent_id="system:root",
            properties=props,
        )

    def _build_sysfs_pci_device(self, slot: str, path: str) -> DeviceInfo | None:
        vendor_id = self._read_sysfs(path, "vendor").replace("0x", "")
        device_id = self._read_sysfs(path, "device").replace("0x", "")
        class_id = self._read_sysfs(path, "class").replace("0x", "")

        driver_link = os.path.join(path, "driver")
        driver_name = os.path.basename(os.readlink(driver_link)) if os.path.islink(driver_link) else ""
        drv_info = self.inspect_driver(driver_name)

        category = self._categorize_pci_class("", class_id)
        icon, _ = CATEGORY_METADATA.get(category, ("🧩", 120))

        return DeviceInfo(
            id=f"pci:{slot}",
            name=f"PCI Device [{vendor_id}:{device_id}]",
            category=category,
            category_icon=icon,
            bus_type="pci",
            vendor_id=vendor_id,
            product_id=device_id,
            pci_slot=slot,
            sysfs_path=path,
            modalias=self._read_sysfs(path, "modalias"),
            driver_name=driver_name,
            driver_type=drv_info["type"],
            driver_type_label=drv_info["label"],
            driver_module_path=drv_info["path"],
            driver_memory_size=drv_info["size"],
            driver_used_by=drv_info["used_by"],
            parent_id="system:root",
        )

    def scan_usb_devices(self) -> list[DeviceInfo]:
        """Probes USB peripherals, hubs, controllers, and interfaces via /sys/bus/usb/devices."""
        devices: list[DeviceInfo] = []
        usb_base = "/sys/bus/usb/devices"
        if not os.path.exists(usb_base):
            return devices

        for entry in sorted(os.listdir(usb_base)):
            p = os.path.join(usb_base, entry)
            # Match top-level devices (e.g. 1-10, 2-4, usb1) and skip interface directories (e.g. 1-10:1.0)
            id_vendor_f = os.path.join(p, "idVendor")
            if not os.path.exists(id_vendor_f):
                continue

            vendor_id = self._read_sysfs(p, "idVendor")
            product_id = self._read_sysfs(p, "idProduct")
            vendor_name = self._read_sysfs(p, "manufacturer") or vendor_id
            product_name = self._read_sysfs(p, "product") or product_id
            busnum = self._read_sysfs(p, "busnum")
            devnum = self._read_sysfs(p, "devnum")
            speed = self._read_sysfs(p, "speed")
            modalias = self._read_sysfs(p, "modalias")
            dev_class = self._read_sysfs(p, "bDeviceClass")

            # Collect active interface drivers
            drivers: set[str] = set()
            dev_nodes: list[str] = []
            for iface in glob.glob(os.path.join(p, f"{entry}:*")):
                drv_link = os.path.join(iface, "driver")
                if os.path.islink(drv_link):
                    drivers.add(os.path.basename(os.readlink(drv_link)))
                # Check for input or tty or hidraw device nodes under interface
                node = self._find_dev_node_for_sysfs(iface)
                if node:
                    dev_nodes.append(node)

            driver_link = os.path.join(p, "driver")
            top_driver = os.path.basename(os.readlink(driver_link)) if os.path.islink(driver_link) else ""
            if top_driver:
                drivers.add(top_driver)

            main_driver = sorted(drivers)[0] if drivers else ""
            drv_info = self.inspect_driver(main_driver)

            # Categorize USB device
            category = self._categorize_usb_device(product_name, vendor_name, dev_class, list(drivers))
            icon, _ = CATEGORY_METADATA.get(category, ("🔌", 70))

            speed_label = f"{speed} Mbps" if speed else ""
            if speed == "480":
                speed_label = "480 Mbps (High Speed USB 2.0)"
            elif speed == "5000":
                speed_label = "5000 Mbps (SuperSpeed USB 3.0)"
            elif speed == "10000":
                speed_label = "10 Gbps (SuperSpeed+ USB 3.1)"
            elif speed == "12":
                speed_label = "12 Mbps (Full Speed USB 1.1)"

            friendly_name = product_name
            if vendor_name and vendor_name not in friendly_name:
                friendly_name = f"{vendor_name} {product_name}"

            # Parent connection for hierarchical view
            # e.g., "1-7.3" has parent "1-7", "1-7" has parent "usb1"
            parent_id = "system:root"
            if "." in entry:
                parent_sysfs = entry.rsplit(".", 1)[0]
                parent_id = f"usb:{parent_sysfs}"
            elif "-" in entry:
                bus_id = entry.split("-")[0]
                parent_id = f"usb:usb{bus_id}"

            dev_node_str = ", ".join(dev_nodes) if dev_nodes else ""

            props = {
                "BUSNUM": busnum,
                "DEVNUM": devnum,
                "SPEED": speed_label,
                "ID_VENDOR": vendor_id,
                "ID_MODEL": product_id,
                "MANUFACTURER": vendor_name,
                "PRODUCT": product_name,
                "DRIVERS": ", ".join(sorted(drivers)) if drivers else "None",
            }
            if modalias:
                props["MODALIAS"] = modalias

            devices.append(
                DeviceInfo(
                    id=f"usb:{entry}",
                    name=friendly_name,
                    category=category,
                    category_icon=icon,
                    bus_type="usb",
                    vendor_name=vendor_name,
                    vendor_id=vendor_id,
                    product_name=product_name,
                    product_id=product_id,
                    usb_bus=busnum,
                    usb_dev=devnum,
                    usb_port=entry,
                    usb_speed=speed_label,
                    device_node=dev_node_str,
                    sysfs_path=p,
                    modalias=modalias,
                    driver_name=main_driver,
                    driver_type=drv_info["type"],
                    driver_type_label=drv_info["label"],
                    driver_module_path=drv_info["path"],
                    driver_memory_size=drv_info["size"],
                    driver_used_by=drv_info["used_by"],
                    driver_description=drv_info["description"],
                    driver_version=drv_info["version"],
                    driver_license=drv_info["license"],
                    power_state=self._read_sysfs(p, "power/runtime_status"),
                    wakeup_enabled=self._read_sysfs(p, "power/wakeup"),
                    parent_id=parent_id,
                    properties=props,
                )
            )

        return devices

    def scan_block_devices(self) -> list[DeviceInfo]:
        """Probes physical disk drives and block storage (NVMe, SSDs, HDDs, USB storage)."""
        devices: list[DeviceInfo] = []
        block_base = "/sys/class/block"
        if not os.path.exists(block_base):
            return devices

        for name in sorted(os.listdir(block_base)):
            # Skip partitions like sda1, nvme0n1p1, loop devices, zram, dm
            if name.startswith(("loop", "zram", "dm-", "sr")):
                continue
            if re.search(r"p\d+$", name) or re.search(r"[a-z]+\d+$", name):
                continue

            p = os.path.join(block_base, name)
            model = self._read_sysfs(p, "device/model") or self._read_sysfs(p, "device/name") or name
            vendor = self._read_sysfs(p, "device/vendor")
            serial = self._read_sysfs(p, "device/serial")

            # Size calculation
            size_sectors = 0
            size_f = os.path.join(p, "size")
            if os.path.exists(size_f):
                try:
                    size_sectors = int(open(size_f).read().strip())
                except Exception:
                    pass

            size_bytes = size_sectors * 512
            if size_bytes >= 1024**4:
                size_str = f"{size_bytes / (1024**4):.2f} TB"
            elif size_bytes >= 1024**3:
                size_str = f"{size_bytes / (1024**3):.1f} GB"
            else:
                size_str = f"{size_bytes / (1024**2):.0f} MB"

            # Driver
            driver_link = os.path.join(p, "device/driver")
            driver_name = os.path.basename(os.readlink(driver_link)) if os.path.islink(driver_link) else ""
            if not driver_name and name.startswith("nvme"):
                driver_name = "nvme"
            drv_info = self.inspect_driver(driver_name)

            dev_node = f"/dev/{name}"
            friendly_name = f"{vendor} {model}".strip() if vendor else model
            friendly_name = f"{friendly_name} ({size_str})"

            devices.append(
                DeviceInfo(
                    id=f"block:{name}",
                    name=friendly_name,
                    category="Disk Drives",
                    category_icon="💾",
                    bus_type="block",
                    vendor_name=vendor,
                    product_name=model,
                    device_node=dev_node,
                    sysfs_path=p,
                    driver_name=driver_name,
                    driver_type=drv_info["type"],
                    driver_type_label=drv_info["label"],
                    driver_module_path=drv_info["path"],
                    driver_memory_size=drv_info["size"],
                    driver_used_by=drv_info["used_by"],
                    parent_id="system:root",
                    properties={
                        "DEVICE_NODE": dev_node,
                        "CAPACITY": size_str,
                        "MODEL": model,
                        "VENDOR": vendor,
                        "SERIAL": serial,
                        "REMOVABLE": self._read_sysfs(p, "removable"),
                    },
                )
            )

        return devices

    def scan_cpu_devices(self) -> list[DeviceInfo]:
        """Collects processor sockets and logical CPU cores from /proc/cpuinfo."""
        devices: list[DeviceInfo] = []
        if not os.path.exists("/proc/cpuinfo"):
            return devices

        try:
            with open("/proc/cpuinfo", "r", errors="ignore") as f:
                content = f.read()

            blocks = content.strip().split("\n\n")
            model_name = ""
            cores_count = len(blocks)

            for b in blocks:
                lines = b.splitlines()
                cur_cpu = {}
                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        cur_cpu[k.strip()] = v.strip()

                cpu_idx = cur_cpu.get("processor", "0")
                if not model_name and "model name" in cur_cpu:
                    model_name = cur_cpu["model name"]

                m_name = cur_cpu.get("model name", model_name or "CPU Core")
                mhz = cur_cpu.get("cpu MHz", "")

                devices.append(
                    DeviceInfo(
                        id=f"cpu:{cpu_idx}",
                        name=f"{m_name} (Core #{cpu_idx})",
                        category="Processors (CPU)",
                        category_icon="⚙️",
                        bus_type="cpu",
                        product_name=m_name,
                        sysfs_path=f"/sys/devices/system/cpu/cpu{cpu_idx}",
                        driver_name="kernel-builtin",
                        driver_type="builtin",
                        driver_type_label="Kernel Core Architecture",
                        parent_id="system:root",
                        properties={
                            "CORE_INDEX": cpu_idx,
                            "SPEED_MHZ": f"{float(mhz):.1f} MHz" if mhz else "Unknown",
                            "VENDOR_ID": cur_cpu.get("vendor_id", ""),
                            "CACHE_SIZE": cur_cpu.get("cache size", ""),
                            "FLAGS": cur_cpu.get("flags", "")[:80] + "...",
                        },
                    )
                )
        except Exception:
            pass

        return devices

    def scan_all_devices(self) -> list[DeviceInfo]:
        """Runs unified scan of PCI, USB, Block, and CPU devices with driver inspection."""
        self.refresh_driver_database()
        all_devs: list[DeviceInfo] = []

        all_devs.extend(self.scan_pci_devices())
        all_devs.extend(self.scan_usb_devices())
        all_devs.extend(self.scan_block_devices())
        all_devs.extend(self.scan_cpu_devices())

        return all_devs

    def get_system_summary(self, devices: list[DeviceInfo] | None = None) -> SystemSummary:
        """Assembles a high-level hardware summary using inxi and sysfs fallback."""
        if devices is None:
            devices = []

        summary = SystemSummary(
            hostname=platform.node(),
            distro=self._get_distro_name(),
            kernel=platform.release(),
            arch=platform.machine(),
            desktop=os.environ.get("XDG_CURRENT_DESKTOP", os.environ.get("DESKTOP_SESSION", "Desktop")),
        )

        # DMI Motherboard and BIOS
        dmi_base = "/sys/class/dmi/id"
        if os.path.exists(dmi_base):
            board_v = self._read_sysfs(dmi_base, "board_vendor")
            board_n = self._read_sysfs(dmi_base, "board_name")
            summary.motherboard = f"{board_v} {board_n}".strip() or "Standard Motherboard"
            summary.bios_version = self._read_sysfs(dmi_base, "bios_version")
            summary.bios_date = self._read_sysfs(dmi_base, "bios_date")

        # Memory
        if os.path.exists("/proc/meminfo"):
            try:
                mem_total_kb, mem_avail_kb = 0, 0
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            mem_total_kb = int(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            mem_avail_kb = int(line.split()[1])
                summary.memory_total = f"{mem_total_kb / (1024 * 1024):.1f} GiB"
                used_kb = mem_total_kb - mem_avail_kb
                summary.memory_used = f"{used_kb / (1024 * 1024):.1f} GiB ({int(used_kb / max(mem_total_kb, 1) * 100)}%)"
            except Exception:
                pass

        # CPU model
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cores = 0
                    for line in f:
                        if "model name" in line and not summary.cpu_model:
                            summary.cpu_model = line.split(":", 1)[1].strip()
                        if line.startswith("processor"):
                            cores += 1
                    summary.cpu_cores = cores
            except Exception:
                pass

        # Optional: Run inxi -b -c 0 for extra polish
        if shutil.which("inxi"):
            try:
                out = subprocess.check_output(
                    ["inxi", "-b", "-c", "0"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                summary.raw_inxi = out
                for line in out.splitlines():
                    if "Device-1:" in line and "driver:" in line and not summary.graphics_summary:
                        summary.graphics_summary = line.strip()
            except Exception:
                pass

        # Calculate counts
        summary.device_count_total = len(devices)
        counts: dict[str, int] = {}
        for d in devices:
            counts[d.category] = counts.get(d.category, 0) + 1
        summary.device_counts_by_category = counts

        return summary

    def _get_distro_name(self) -> str:
        """Extracts pretty distro name from /etc/os-release."""
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=", 1)[1].strip('"\n')
            except Exception:
                pass
        return "Linux"

    def _read_sysfs(self, path: str, attr: str) -> str:
        """Safely reads a sysfs attribute file."""
        target = os.path.join(path, attr)
        if os.path.exists(target):
            try:
                with open(target, "r", errors="ignore") as f:
                    return f.read().strip()
            except Exception:
                pass
        return ""

    def _find_dev_node_for_sysfs(self, sysfs_path: str) -> str:
        """Finds active /dev device node corresponding to a sysfs path."""
        # Check dev file (major:minor)
        dev_file = os.path.join(sysfs_path, "dev")
        if os.path.exists(dev_file) and shutil.which("udevadm"):
            try:
                out = subprocess.check_output(
                    ["udevadm", "info", "-q", "name", "-p", sysfs_path],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                ).strip()
                if out:
                    return f"/dev/{out}"
            except Exception:
                pass

        # Direct search under common subsystems (dri, tty, input)
        for sub in ["drm", "tty", "input"]:
            sub_dir = os.path.join(sysfs_path, sub)
            if os.path.isdir(sub_dir):
                for item in os.listdir(sub_dir):
                    if os.path.exists(f"/dev/{item}"):
                        return f"/dev/{item}"
                    if os.path.exists(f"/dev/input/{item}"):
                        return f"/dev/input/{item}"
                    if os.path.exists(f"/dev/dri/{item}"):
                        return f"/dev/dri/{item}"

        return ""

    def _extract_name_and_hex(self, val: str) -> tuple[str, str]:
        """Splits 'Advanced Micro Devices, Inc. [AMD] [1022]' into ('AMD', '1022')."""
        val = val.strip()
        m = re.findall(r"\[([0-9a-fA-F]{4})\]", val)
        hex_id = m[-1] if m else ""
        clean_name = re.sub(r"\[[0-9a-fA-F]{4}\]", "", val).strip()
        return clean_name, hex_id

    def _categorize_pci_class(self, class_name: str, class_id: str) -> str:
        """Maps PCI class codes or description names to Windows-like categories."""
        cl = class_name.lower()
        cid = class_id.lower()

        if "vga" in cl or "3d" in cl or "display" in cl or cid.startswith("03"):
            return "Display Adapters"
        if "audio" in cl or "sound" in cl or "multimedia" in cl or cid.startswith("04"):
            return "Audio & Sound Devices"
        if "ethernet" in cl or "network" in cl or "wireless" in cl or cid.startswith("02"):
            return "Network Adapters"
        if "non-volatile" in cl or "nvme" in cl or "sata" in cl or "storage" in cl or cid.startswith("01"):
            return "Storage Controllers"
        if "usb" in cl or cid.startswith("0c03"):
            return "Universal Serial Bus (USB)"
        if "serial" in cl or "communication" in cl or cid.startswith("07"):
            return "Ports (COM & Serial)"
        if "bluetooth" in cl:
            return "Bluetooth & Wireless"
        if "bridge" in cl or "iommu" in cl or "smbus" in cl or cid.startswith("06") or cid.startswith("08"):
            return "System & Motherboard Devices"

        return "Other Devices"

    def _categorize_usb_device(self, prod_name: str, vendor_name: str, dev_class: str, drivers: list[str]) -> str:
        """Categorizes USB peripherals into appropriate categories."""
        combined = f"{prod_name} {vendor_name} {' '.join(drivers)}".lower()

        if "hub" in combined and "root" not in combined:
            return "Universal Serial Bus (USB)"
        if any(h in combined for h in ["keyboard", "mouse", "pointer", "receiver", "gamepad", "controller", "usbhid"]):
            return "Human Interface Devices (HID)"
        if any(a in combined for a in ["audio", "sound", "headset", "microphone", "speaker", "dac"]):
            return "Audio & Sound Devices"
        if any(v in combined for v in ["cam", "camera", "video", "capture", "uvc"]):
            return "Cameras & Video Capture"
        if any(n in combined for n in ["ethernet", "lan", "wifi", "wlan", "wireless", "802.11"]):
            return "Network Adapters"
        if any(b in combined for b in ["bluetooth", "bt"]):
            return "Bluetooth & Wireless"
        if any(s in combined for s in ["storage", "disk", "flash", "ultra", "usb-storage"]):
            return "Disk Drives"
        if any(c in combined for c in ["serial", "cdc_acm", "modem", "tty"]):
            return "Ports (COM & Serial)"
        if "host controller" in combined:
            return "Universal Serial Bus (USB)"

        return "Universal Serial Bus (USB)"
