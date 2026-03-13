"""
KVM Client - libvirt wrapper for KVM VM management
"""

import libvirt
import html
import logging
from typing import Optional, Dict, List, Any

# Set up logging
logger = logging.getLogger(__name__)


class KVMMachineError(Exception):
    """Custom exception for KVM-related errors"""
    pass


class KVMClient:
    """
    Client for managing KVM virtual machines via libvirt.
    """

    def __init__(self, uri: str = "qemu:///system"):
        """
        Initialize the KVM client.

        Args:
            uri: libvirt connection URI (default: qemu:///system for local KVM)
        """
        self.uri = uri
        self.conn: Optional[libvirt.virConnect] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to libvirt daemon"""
        logger.info(f"Connecting to libvirt at {self.uri}")
        try:
            self.conn = libvirt.open(self.uri)
            if self.conn is None:
                raise KVMMachineError(f"Failed to connect to {self.uri}")
            logger.info("Successfully connected to libvirt")
        except libvirt.libvirtError as e:
            logger.error(f"Failed to connect to libvirt: {e}")
            raise KVMMachineError(f"Failed to connect to libvirt: {e}")

    def __del__(self):
        """Close connection on deletion"""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass

    def list_vms(self) -> List[Dict[str, Any]]:
        """
        List all VMs and their current status.

        Returns:
            List of dictionaries containing VM name and status
        """
        logger.info("Listing all VMs")
        vms = []
        try:
            # Get all domains (including inactive ones)
            domains = self.conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_INACTIVE)
        except libvirt.libvirtError as e:
            logger.error(f"Failed to list VMs: {e}")
            raise KVMMachineError(f"Failed to list VMs: {e}")

        for domain in domains:
            try:
                name = domain.name()
                state = self._get_state_name(domain.state())
                logger.debug(f"  Found VM: {name} ({state})")
                vms.append({
                    "name": name,
                    "status": state
                })
            except libvirt.libvirtError as e:
                logger.error(f"Failed to get info for VM: {e}")
                raise KVMMachineError(f"Failed to get VM info: {e}")

        logger.info(f"Found {len(vms)} VM(s)")
        return vms

    def get_vm_status(self, vm_name: str) -> Dict[str, Any]:
        """
        Get detailed status of a specific VM.

        Args:
            vm_name: Name of the VM

        Returns:
            Dictionary containing VM status information
        """
        logger.info(f"Getting status for VM: {vm_name}")
        domain = self._get_domain(vm_name)
        state, state_detail = domain.state()

        result = {
            "name": vm_name,
            "status": self._get_state_name(state),
            "status_detail": self._get_state_detail(state, state_detail),
            "uuid": domain.UUIDString(),
            "max_memory": self._format_bytes(domain.maxMemory()),
            "memory": self._format_bytes(domain.memory()),
            "nr_vcpus": domain.vcpusCount()
        }
        logger.debug(f"VM {vm_name} status: {result['status']} ({result['status_detail']})")
        return result

    def get_vm_info(self, vm_name: str) -> Dict[str, Any]:
        """
        Get detailed hardware information about a VM.

        Args:
            vm_name: Name of the VM

        Returns:
            Dictionary containing VM hardware configuration
        """
        logger.info(f"Getting hardware info for VM: {vm_name}")
        domain = self._get_domain(vm_name)

        try:
            xml = domain.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        except libvirt.libvirtError as e:
            logger.error(f"Failed to get VM XML: {e}")
            raise KVMMachineError(f"Failed to get VM XML: {e}")

        # Parse basic info from XML
        info = {
            "name": vm_name,
            "uuid": domain.UUIDString(),
            "memory": self._format_bytes(domain.maxMemory()),
            "current_memory": self._format_bytes(domain.memory()),
            "vcpus": domain.vcpusCount(),
            "disks": [],
            "networks": [],
            "graphics": []
        }

        # Parse disks from XML
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml)
            ns = {"qemu": "http://libvirt.org/schemas/domain/qemu/1.0"}

            # Find disk elements
            for disk in root.findall(".//disk"):
                disk_info = {
                    "device": disk.get("device", "disk"),
                    "bus": disk.get("bus", "unknown"),
                }
                target = disk.find("target")
                if target is not None:
                    disk_info["target"] = target.get("dev", "unknown")
                source = disk.find("source")
                if source is not None:
                    disk_info["source"] = source.get("file") or source.get("dev") or source.get("name")
                info["disks"].append(disk_info)
                logger.debug(f"  Disk: {disk_info}")

            # Find interface elements
            for iface in root.findall(".//interface"):
                iface_info = {
                    "type": iface.get("type", "unknown"),
                    "model": iface.find("model").get("name") if iface.find("model") is not None else "unknown",
                }
                mac = iface.find("mac")
                if mac is not None:
                    iface_info["mac"] = mac.get("address")
                source = iface.find("source")
                if source is not None:
                    iface_info["source"] = source.get("network") or source.get("bridge")
                info["networks"].append(iface_info)
                logger.debug(f"  Network: {iface_info}")

            # Find graphics elements
            for graphic in root.findall(".//graphics"):
                graphic_info = {
                    "type": graphic.get("type", "unknown"),
                    "port": graphic.get("port"),
                    "autoport": graphic.get("autoport") == "yes",
                    "listen": graphic.get("listen", "0.0.0.0")
                }
                info["graphics"].append(graphic_info)
                logger.debug(f"  Graphics: {graphic_info}")

        except Exception as e:
            # If XML parsing fails, return basic info
            logger.warning(f"Failed to parse VM XML for {vm_name}: {e}")

        logger.info(f"VM {vm_name} has {len(info['disks'])} disk(s), {len(info['networks'])} network(s)")
        return info

    def start_vm(self, vm_name: str) -> Dict[str, Any]:
        """
        Start a VM.

        Args:
            vm_name: Name of the VM to start

        Returns:
            Status dictionary
        """
        logger.info(f"Starting VM: {vm_name}")
        domain = self._get_domain(vm_name)

        try:
            domain.create()
            logger.info(f"VM '{vm_name}' started successfully")
            return {
                "success": True,
                "message": f"VM '{vm_name}' started successfully",
                "vm_name": vm_name
            }
        except libvirt.libvirtError as e:
            if "already running" in str(e):
                logger.info(f"VM '{vm_name}' is already running")
                return {
                    "success": True,
                    "message": f"VM '{vm_name}' is already running",
                    "vm_name": vm_name
                }
            logger.error(f"Failed to start VM '{vm_name}': {e}")
            raise KVMMachineError(f"Failed to start VM '{vm_name}': {e}")

    def stop_vm(self, vm_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Stop a VM.

        Args:
            vm_name: Name of the VM to stop
            force: If True, forcibly power off; otherwise send ACPI shutdown

        Returns:
            Status dictionary
        """
        logger.info(f"Stopping VM: {vm_name} (force={force})")
        domain = self._get_domain(vm_name)

        state, _ = domain.state()

        if state == libvirt.VIR_DOMAIN_SHUTDOWN or state == libvirt.VIR_DOMAIN_SHUTOFF:
            logger.info(f"VM '{vm_name}' is already stopped")
            return {
                "success": True,
                "message": f"VM '{vm_name}' is already stopped",
                "vm_name": vm_name
            }

        try:
            if force:
                domain.destroy()
                logger.info(f"VM '{vm_name}' forcibly powered off")
                return {
                    "success": True,
                    "message": f"VM '{vm_name}' forcibly powered off",
                    "vm_name": vm_name
                }
            else:
                # Try graceful shutdown via ACPI
                domain.shutdown()
                logger.info(f"VM '{vm_name}' shutdown request sent (ACPI)")
                return {
                    "success": True,
                    "message": f"VM '{vm_name}' shutdown request sent (ACPI)",
                    "vm_name": vm_name
                }
        except libvirt.libvirtError as e:
            logger.error(f"Failed to stop VM '{vm_name}': {e}")
            raise KVMMachineError(f"Failed to stop VM '{vm_name}': {e}")

    def create_snapshot(self, vm_name: str, snapshot_name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a snapshot of a VM.

        Args:
            vm_name: Name of the VM
            snapshot_name: Name for the snapshot
            description: Optional description for the snapshot

        Returns:
            Status dictionary
        """
        logger.info(f"Creating snapshot '{snapshot_name}' for VM: {vm_name}")
        domain = self._get_domain(vm_name)

        # Create snapshot metadata
        snap_xml = f"""<snapshot>
            <name>{self._xml_escape(snapshot_name)}</name>
            <description>{self._xml_escape(description)}</description>
            <state>
                <active/>
            </state>
        </snapshot>"""

        try:
            snapshot = domain.createWithXML(snap_xml, 0)
            logger.info(f"Snapshot '{snapshot_name}' created for VM '{vm_name}'")
            return {
                "success": True,
                "message": f"Snapshot '{snapshot_name}' created for VM '{vm_name}'",
                "vm_name": vm_name,
                "snapshot_name": snapshot_name
            }
        except libvirt.libvirtError as e:
            logger.error(f"Failed to create snapshot '{snapshot_name}' for VM '{vm_name}': {e}")
            raise KVMMachineError(f"Failed to create snapshot: {e}")

    def list_snapshots(self, vm_name: str) -> List[Dict[str, Any]]:
        """
        List all snapshots for a VM.

        Args:
            vm_name: Name of the VM

        Returns:
            List of snapshot dictionaries
        """
        logger.info(f"Listing snapshots for VM: {vm_name}")
        domain = self._get_domain(vm_name)

        ss_dict = []
        try:
            snapshots = domain.listAllSnapshots(flags=0)
            if not snapshots:
                logger.info(f"No snapshots found for domain {domain}")
            else:
                logger.info(f"Snapshots for domain {domain}:")
                for snapshot in snapshots:
                    d = {}
                    # Get the name of the snapshot
                    snap_name = snapshot.getName()
                    logger.info(f"- {snap_name}")
                    # snap_xml = snapshot.getXMLDesc(0)
                    d["name"] = snap_name
                    ss_dict.append(d)

            return ss_dict
        except libvirt.libvirtError as e:
            logger.error(f"Failed to list snapshots for VM '{vm_name}': {e}")
            raise KVMMachineError(f"Failed to list snapshots: {e}")

    def rollback_snapshot(self, vm_name: str, snapshot_name: str) -> Dict[str, Any]:
        """
        Rollback VM to a specific snapshot.

        Args:
            vm_name: Name of the VM
            snapshot_name: Name of the snapshot to rollback to

        Returns:
            Status dictionary
        """
        logger.warning(f"Rolling back VM '{vm_name}' to snapshot '{snapshot_name}'")
        domain = self._get_domain(vm_name)

        try:
            snapshot = domain.snapshotLookupByName(snapshot_name)
            snapshot.revert(libvirt.VIR_DOMAIN_REVERT_SNAPSHOT)
            logger.info(f"VM '{vm_name}' successfully rolled back to snapshot '{snapshot_name}'")
            return {
                "success": True,
                "message": f"VM '{vm_name}' rolled back to snapshot '{snapshot_name}'",
                "vm_name": vm_name,
                "snapshot_name": snapshot_name
            }
        except libvirt.libvirtError as e:
            if "not found" in str(e):
                logger.error(f"Snapshot '{snapshot_name}' not found for VM '{vm_name}'")
                raise KVMMachineError(f"Snapshot '{snapshot_name}' not found for VM '{vm_name}'")
            logger.error(f"Failed to rollback snapshot '{snapshot_name}': {e}")
            raise KVMMachineError(f"Failed to rollback snapshot: {e}")

    def _get_domain(self, vm_name: str) -> libvirt.virDomain:
        """
        Get a domain by name.

        Args:
            vm_name: Name of the VM

        Returns:
            libvirt.virDomain object

        Raises:
            KVMMachineError: If VM not found
        """
        if self.conn is None:
            logger.error("Not connected to libvirt")
            raise KVMMachineError("Not connected to libvirt")

        try:
            domain = self.conn.lookupByName(vm_name)
            logger.debug(f"Found domain: {vm_name}")
            return domain
        except libvirt.libvirtError as e:
            logger.error(f"VM '{vm_name}' not found: {e}")
            raise KVMMachineError(f"VM '{vm_name}' not found: {e}")

    def _get_state_name(self, state: int) -> str:
        """Convert libvirt state integer to human-readable name"""
        state_map = {
            libvirt.VIR_DOMAIN_RUNNING: "running",
            libvirt.VIR_DOMAIN_BLOCKED: "blocked",
            libvirt.VIR_DOMAIN_SHUTDOWN: "shut down",
            libvirt.VIR_DOMAIN_SHUTOFF: "shut off",
            libvirt.VIR_DOMAIN_CRASHED: "crashed",
            libvirt.VIR_DOMAIN_PAUSED: "paused",
        }
        return state_map.get(state[0], "unknown")

    def _get_state_detail(self, state: int, detail: int) -> str:
        """Get detailed state information"""
        if state == libvirt.VIR_DOMAIN_RUNNING:
            if detail == libvirt.VIR_DOMAIN_RUNNING_RUNNING:
                return "running normally"
            elif detail == libvirt.VIR_DOMAIN_RUNNING_RUNNABLE:
                return "runnable (not running)"
            elif detail == libvirt.VIR_DOMAIN_RUNNING_SUSPENDED:
                return "suspended"
        elif state == libvirt.VIR_DOMAIN_SHUTDOWN:
            return "shutting down"
        elif state == libvirt.VIR_DOMAIN_CRASHED:
            return "crashed"
        elif state == libvirt.VIR_DOMAIN_PAUSED:
            if detail == libvirt.VIR_DOMAIN_PAUSED_PAUSED:
                return "paused by user"
            elif detail == libvirt.VIR_DOMAIN_PAUSED_EXTERNAL:
                return "paused externally"
            elif detail == libvirt.VIR_DOMAIN_PAUSED_INSERTED:
                return "paused for device insertion"
            elif detail == libvirt.VIR_DOMAIN_PAUSED_MIGRATING:
                return "paused for migration"
            elif detail == libvirt.VIR_DOMAIN_PAUSED_SNAPSHOT:
                return "paused for snapshot"
            elif detail == libvirt.VIR_DOMAIN_PAUSED_DEBUG:
                return "paused for debugging"
        return "unknown state"

    def _format_bytes(self, size: int) -> str:
        """Format bytes to human-readable string"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    def _xml_escape(self, text: str) -> str:
        """Basic XML escaping for special characters"""
        if not text:
            return text
        return html.escape(text, quote=True)