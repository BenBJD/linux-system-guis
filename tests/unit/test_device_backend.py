"""Unit tests for Device Manager hardware backend and driver inspection."""

from device_gui.backend import (
    CATEGORY_METADATA,
    DeviceInfo,
    DeviceManagerBackend,
    SystemSummary,
)


def test_device_info_dataclass():
    dev = DeviceInfo(
        id="pci:0000:01:00.0",
        name="NVIDIA GeForce RTX 3060 Ti",
        category="Display Adapters",
        category_icon="🖥️",
        bus_type="pci",
        vendor_id="10de",
        product_id="2489",
        driver_name="nvidia",
        driver_type="module",
        driver_type_label="Active (Kernel Module)",
    )
    assert dev.id == "pci:0000:01:00.0"
    assert dev.category == "Display Adapters"
    assert dev.driver_type == "module"
    assert dev.vendor_id == "10de"


def test_categorize_pci_class():
    backend = DeviceManagerBackend()
    assert backend._categorize_pci_class("VGA compatible controller", "0300") == "Display Adapters"
    assert backend._categorize_pci_class("3D controller", "0302") == "Display Adapters"
    assert backend._categorize_pci_class("Audio device", "0403") == "Audio & Sound Devices"
    assert backend._categorize_pci_class("Ethernet controller", "0200") == "Network Adapters"
    assert backend._categorize_pci_class("Non-Volatile memory controller", "0108") == "Storage Controllers"
    assert backend._categorize_pci_class("USB controller", "0c03") == "Universal Serial Bus (USB)"
    assert backend._categorize_pci_class("Host bridge", "0600") == "System & Motherboard Devices"
    assert backend._categorize_pci_class("Serial controller", "0700") == "Ports (COM & Serial)"


def test_categorize_usb_device():
    backend = DeviceManagerBackend()
    assert backend._categorize_usb_device("USB Receiver", "Logitech", "", ["usbhid"]) == "Human Interface Devices (HID)"
    assert backend._categorize_usb_device("Gaming Keyboard", "Glorious", "", ["usbhid"]) == "Human Interface Devices (HID)"
    assert backend._categorize_usb_device("USB2.0 Hub", "Genesys", "", ["hub"]) == "Universal Serial Bus (USB)"
    assert backend._categorize_usb_device("Ultra Flash Drive", "SanDisk", "", ["usb-storage"]) == "Disk Drives"
    assert backend._categorize_usb_device("HD Pro Webcam C920", "Logitech", "", ["uvcvideo"]) == "Cameras & Video Capture"
    assert backend._categorize_usb_device("USB Audio DAC", "FiiO", "", ["snd-usb-audio"]) == "Audio & Sound Devices"


def test_driver_inspection_logic():
    backend = DeviceManagerBackend()
    backend.dkms_modules = {"custom_wifi", "xone"}
    backend.builtin_modules = {"ext4", "usbhid"}
    backend.proc_modules = {
        "nvidia": {"size": "55.4 MB", "used_by": ["nvidia_modeset"]},
    }

    # 1. Driverless
    none_info = backend.inspect_driver("")
    assert none_info["type"] == "none"

    # 2. DKMS
    dkms_info = backend.inspect_driver("xone")
    assert dkms_info["type"] == "dkms"
    assert "DKMS" in dkms_info["label"]

    # 3. Builtin
    builtin_info = backend.inspect_driver("usbhid")
    assert builtin_info["type"] == "builtin"
    assert "Built-in" in builtin_info["label"]

    # 4. Standard loaded module
    mod_info = backend.inspect_driver("nvidia")
    assert mod_info["size"] == "55.4 MB"
    assert "nvidia_modeset" in mod_info["used_by"]


def test_system_summary_and_counts():
    backend = DeviceManagerBackend()
    devs = [
        DeviceInfo(id="1", name="GPU", category="Display Adapters", category_icon="🖥️"),
        DeviceInfo(id="2", name="NIC", category="Network Adapters", category_icon="🌐"),
        DeviceInfo(id="3", name="Mouse", category="Human Interface Devices (HID)", category_icon="⌨️"),
    ]
    summary = backend.get_system_summary(devs)
    assert summary.device_count_total == 3
    assert summary.device_counts_by_category["Display Adapters"] == 1
    assert summary.device_counts_by_category["Network Adapters"] == 1
    assert summary.device_counts_by_category["Human Interface Devices (HID)"] == 1
    assert summary.kernel != ""


def test_real_system_scan():
    backend = DeviceManagerBackend()
    devices = backend.scan_all_devices()
    # On any Linux system with PCI/USB/CPU, we expect at least 1 device
    assert len(devices) > 0
    assert all(d.id and d.name and d.category for d in devices)
