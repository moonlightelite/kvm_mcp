#!/usr/bin/env python3
"""
KVM MCP Server - Model Context Protocol server for KVM virtual machine management

This server provides tools for controlling KVM virtual machines through the Model Context Protocol.
It uses libvirt to communicate with the local KVM/QEMU hypervisor.
"""

import logging
import json
import uvicorn
#from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
from typing import List, Dict, Any
from kvm_client import KVMClient, KVMMachineError
from starlette.middleware.cors import CORSMiddleware


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the FastMCP server instance
mcp = FastMCP("kvm-manager")

# Initialize the KVM client
logger.info("Initializing KVM MCP Server")
kvm_client = KVMClient()
logger.info("KVM MCP Server initialized successfully")

app = mcp.http_app(path="/mcp")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["mcp-session-id"]  # Fixes "Missing session ID" in MCP Inspector
)

@mcp.tool()
def list_vms() -> str:
    """
    List all virtual machines on the KVM host with their current status.

    Returns:
        JSON string containing a list of VMs with their names and statuses.
    """
    logger.info("Tool called: list_vms")
    try:
        vms = kvm_client.list_vms()
        logger.info(f"list_vms returned {len(vms)} VM(s)")
        return _format_json(vms)
    except KVMMachineError as e:
        logger.error(f"list_vms failed: {e}")
        return _format_error(str(e))


@mcp.tool()
def get_vm_status(vm_name: str) -> str:
    """
    Get detailed status information for a specific virtual machine.

    Args:
        vm_name: The name of the virtual machine to query.

    Returns:
        JSON string containing the VM's status, memory usage, and CPU count.
    """
    logger.info(f"Tool called: get_vm_status(vm_name={vm_name})")
    try:
        status = kvm_client.get_vm_status(vm_name)
        logger.info(f"get_vm_status returned: {status['status']}")
        return _format_json(status)
    except KVMMachineError as e:
        logger.error(f"get_vm_status failed for {vm_name}: {e}")
        return _format_error(str(e))


@mcp.tool()
def get_vm_info(vm_name: str) -> str:
    """
    Get detailed hardware configuration information for a virtual machine.

    Args:
        vm_name: The name of the virtual machine to query.

    Returns:
        JSON string containing the VM's hardware configuration including
        memory, vCPUs, disks, network interfaces, and graphics settings.
    """
    logger.info(f"Tool called: get_vm_info(vm_name={vm_name})")
    try:
        info = kvm_client.get_vm_info(vm_name)
        logger.info(f"get_vm_info returned: {info['vcpus']} vCPUs, {info['memory']} memory")
        return _format_json(info)
    except KVMMachineError as e:
        logger.error(f"get_vm_info failed for {vm_name}: {e}")
        return _format_error(str(e))


@mcp.tool()
def start_vm(vm_name: str) -> str:
    """
    Start a virtual machine.

    Args:
        vm_name: The name of the virtual machine to start.

    Returns:
        JSON string containing the operation result and status message.
    """
    logger.info(f"Tool called: start_vm(vm_name={vm_name})")
    try:
        result = kvm_client.start_vm(vm_name)
        logger.info(f"start_vm succeeded: {result['message']}")
        return _format_json(result)
    except KVMMachineError as e:
        logger.error(f"start_vm failed for {vm_name}: {e}")
        return _format_error(str(e))


@mcp.tool()
def stop_vm(vm_name: str, force: bool = False) -> str:
    """
    Stop a virtual machine.

    Args:
        vm_name: The name of the virtual machine to stop.
        force: If True, forcibly power off the VM. If False (default),
               send a graceful shutdown request via ACPI.

    Returns:
        JSON string containing the operation result and status message.
    """
    logger.info(f"Tool called: stop_vm(vm_name={vm_name}, force={force})")
    try:
        result = kvm_client.stop_vm(vm_name, force=force)
        logger.info(f"stop_vm succeeded: {result['message']}")
        return _format_json(result)
    except KVMMachineError as e:
        logger.error(f"stop_vm failed for {vm_name}: {e}")
        return _format_error(str(e))


mcp.tool()
def create_snapshot(vm_name: str, snapshot_name: str, description: str = "") -> str:
    """
    Create a snapshot of a virtual machine.

    Args:
        vm_name: The name of the virtual machine to snapshot.
        snapshot_name: A unique name for the snapshot.
        description: Optional description for the snapshot.

    Returns:
        JSON string containing the operation result and status message.
    """
    logger.info(f"Tool called: create_snapshot(vm_name={vm_name}, snapshot_name={snapshot_name})")
    try:
        result = kvm_client.create_snapshot(vm_name, snapshot_name, description)
        logger.info(f"create_snapshot succeeded: {result['message']}")
        return _format_json(result)
    except KVMMachineError as e:
        logger.error(f"create_snapshot failed: {e}")
        return _format_error(str(e))


@mcp.tool()
def list_snapshots(vm_name: str) -> str:
    """
    List all snapshots for a virtual machine.

    Args:
        vm_name: The name of the virtual machine.

    Returns:
        JSON string containing a list of snapshots with their names,
        states, and timestamps.
    """
    logger.info(f"Tool called: list_snapshots(vm_name={vm_name})")
    try:
        snapshots = kvm_client.list_snapshots(vm_name)
        logger.info(f"list_snapshots returned {len(snapshots)} snapshot(s)")
        return _format_json({"vm_name": vm_name, "snapshots": snapshots})
    except KVMMachineError as e:
        logger.error(f"list_snapshots failed for {vm_name}: {e}")
        return _format_error(str(e))


@mcp.tool()
def rollback_snapshot(vm_name: str, snapshot_name: str) -> str:
    """
    Rollback a virtual machine to a specific snapshot.

    Args:
        vm_name: The name of the virtual machine to rollback.
        snapshot_name: The name of the snapshot to rollback to.

    Returns:
        JSON string containing the operation result and status message.
    """
    logger.warning(f"Tool called: rollback_snapshot(vm_name={vm_name}, snapshot_name={snapshot_name})")
    try:
        result = kvm_client.rollback_snapshot(vm_name, snapshot_name)
        logger.info(f"rollback_snapshot succeeded: {result['message']}")
        return _format_json(result)
    except KVMMachineError as e:
        logger.error(f"rollback_snapshot failed: {e}")
        return _format_error(str(e))


def _format_json(data: Any) -> str:
    """Format data as a JSON string"""
    return json.dumps(data, indent=2)


def _format_error(message: str) -> str:
    """Format an error message as JSON"""
    return json.dumps({"error": message}, indent=2)


if __name__ == "__main__":
    # Run the MCP server
    logger.info("Starting KVM MCP Server...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
    logger.info("KVM MCP Server stopped")