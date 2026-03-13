# KVM MCP Server

A Python-based Model Context Protocol (MCP) server for managing KVM virtual machines. This server allows MCP clients to control VMs on a KVM host, including starting, stopping, and snapshot management.

## Features

- **List VMs**: Get a list of all VMs and their current status
- **VM Status**: Get detailed status of a specific VM
- **VM Info**: Get hardware configuration details (CPU, memory, disks, networks)
- **Start VM**: Start a stopped virtual machine
- **Stop VM**: Gracefully or forcibly stop a running VM
- **Create Snapshot**: Create snapshots of VMs
- **List Snapshots**: List all snapshots for a VM
- **Rollback Snapshot**: Rollback a VM to a previous snapshot

## Requirements

### System Requirements

- Linux with KVM/QEMU virtualization enabled
- libvirt daemon running (`libvirtd` service)
- Python 3.10 or higher

### Python Dependencies

```
fastmcp>=0.1.0
libvirt-python>=9.0.0
```

> **Note**: This server uses the FastMCP library from [prefecthq/fastmcp](https://github.com/prefecthq/fastmcp). The MCP SDK's FastMCP implementatio (FastMCP v1) is rather poor in quality IMO.

### System Dependencies

You'll need to install libvirt development libraries before installing the Python bindings:

**Debian/Ubuntu:**
```bash
sudo apt-get install libvirt-dev libvirt0 python3-dev build-essential
```

**RHEL/CentOS/Fedora:**
```bash
sudo dnf install libvirt-devel libvirt python3-devel gcc
```

**Arch Linux:**
```bash
sudo pacman -S libvirt python-python3 gcc
```

## Installation

1. Create a Python virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

2. Install the Python dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure your user has permission to access libvirt:
```bash
sudo usermod -aG libvirt $USER
sudo usermod -aG kvm $USER
```
Log out and back in for group changes to take effect.

## Usage

### Running the Server

Run the MCP server:
```bash
python kvm_mcp_server.py
```

The server will start and listen for MCP client connections via stdio (default MCP transport).

### Configuration

Add the server to your MCP client configuration. For example, in your VS Code MCP settings:

```json
{
  "mcpServers": {
    "kvm-manager": {
      "command": "python",
      "args": ["/path/to/kvm_mcp_server.py"]
    }
  }
}
```

### Available Tools

#### `list_vms`
List all virtual machines with their status.

**Example Response:**
```json
[
  {"name": "ubuntu-server", "status": "running"},
  {"name": "windows-11", "status": "shut off"},
  {"name": "debian-test", "status": "shut off"}
]
```

#### `get_vm_status(vm_name)`
Get detailed status for a specific VM.

**Parameters:**
- `vm_name`: Name of the VM

**Example Response:**
```json
{
  "name": "ubuntu-server",
  "status": "running",
  "status_detail": "running normally",
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "max_memory": "4.00 GB",
  "memory": "3.85 GB",
  "nr_vcpus": 4
}
```

#### `get_vm_info(vm_name)`
Get hardware configuration for a VM.

**Parameters:**
- `vm_name`: Name of the VM

**Example Response:**
```json
{
  "name": "ubuntu-server",
  "memory": "4.00 GB",
  "vcpus": 4,
  "disks": [
    {
      "device": "disk",
      "bus": "virtio",
      "target": "vda",
      "source": "/var/lib/libvirt/images/ubuntu-server.qcow2"
    }
  ],
  "networks": [
    {
      "type": "network",
      "model": "virtio",
      "mac": "52:54:00:12:34:56",
      "source": "default"
    }
  ],
  "graphics": []
}
```

#### `start_vm(vm_name)`
Start a virtual machine.

**Parameters:**
- `vm_name`: Name of the VM to start

**Example Response:**
```json
{
  "success": true,
  "message": "VM 'ubuntu-server' started successfully",
  "vm_name": "ubuntu-server"
}
```

#### `stop_vm(vm_name, force)`
Stop a virtual machine.

**Parameters:**
- `vm_name`: Name of the VM to stop
- `force`: (optional, default: false) If true, forcibly power off; otherwise send ACPI shutdown

**Example Response:**
```json
{
  "success": true,
  "message": "VM 'ubuntu-server' shutdown request sent (ACPI)",
  "vm_name": "ubuntu-server"
}
```

#### `create_snapshot(vm_name, snapshot_name, description)`
Create a snapshot of a VM.

**Parameters:**
- `vm_name`: Name of the VM
- `snapshot_name`: Unique name for the snapshot
- `description`: (optional) Description for the snapshot

**Example Response:**
```json
{
  "success": true,
  "message": "Snapshot 'backup-2024-01-15' created for VM 'ubuntu-server'",
  "vm_name": "ubuntu-server",
  "snapshot_name": "backup-2024-01-15"
}
```

#### `list_snapshots(vm_name)`
List all snapshots for a VM.

**Parameters:**
- `vm_name`: Name of the VM

**Example Response:**
```json
{
  "vm_name": "ubuntu-server",
  "snapshots": [
    {
      "name": "backup-2024-01-15",
      "state": "running",
      "timestamp": 1705312800
    },
    {
      "name": "before-upgrade",
      "state": "running",
      "timestamp": 1705226400
    }
  ]
}
```

#### `rollback_snapshot(vm_name, snapshot_name)`
Rollback a VM to a specific snapshot.

**Parameters:**
- `vm_name`: Name of the VM
- `snapshot_name`: Name of the snapshot to rollback to

**Example Response:**
```json
{
  "success": true,
  "message": "VM 'ubuntu-server' rolled back to snapshot 'backup-2024-01-15'",
  "vm_name": "ubuntu-server",
  "snapshot_name": "backup-2024-01-15"
}
```

**Example Log Output:**
```
INFO:     Started server process [14721]
INFO:     Waiting for application startup.
2026-03-13 08:47:19,879 - mcp.server.streamable_http_manager - INFO - StreamableHTTP session manager started
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     192.168.101.128:56332 - "OPTIONS /mcp HTTP/1.1" 200 OK
INFO:     192.168.101.128:56332 - "POST /mcp HTTP/1.1" 404 Not Found
2026-03-13 08:47:26,658 - mcp.server.streamable_http_manager - INFO - Created new transport with session ID: 24cad7c18bdc441f84d6071b72668c7c
INFO:     192.168.101.128:56332 - "POST /mcp HTTP/1.1" 200 OK
INFO:     192.168.101.128:56332 - "POST /mcp HTTP/1.1" 202 Accepted
INFO:     192.168.101.128:56332 - "GET /mcp HTTP/1.1" 200 OK
INFO:     192.168.101.128:56333 - "POST /mcp HTTP/1.1" 200 OK
2026-03-13 08:47:26,926 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
INFO:     192.168.101.128:56333 - "POST /mcp HTTP/1.1" 200 OK
2026-03-13 08:47:27,046 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-03-13 08:47:27,051 - __main__ - INFO - Tool called: stop_vm(vm_name=debian12, force=False)
2026-03-13 08:47:27,052 - kvm_client - INFO - Stopping VM: debian12 (force=False)
2026-03-13 08:47:27,436 - kvm_client - INFO - VM 'debian12' shutdown request sent (ACPI)
2026-03-13 08:47:27,437 - __main__ - INFO - stop_vm succeeded: VM 'debian12' shutdown request sent (ACPI)
```

## Security Notes

- Change the bind address to 127.0.0.1 for local development
- This server runs with no authentication, suitable only for trusted environments
- The server requires access to the libvirt daemon, which typically requires root or libvirt group membership
- Ensure proper system-level access controls are in place on your KVM host

## Troubleshooting

### Permission Denied
If you get permission errors, ensure your user is in the `libvirt` and `kvm` groups:
```bash
sudo usermod -aG libvirt,kvm $USER
```

### Connection Failed
Check that the libvirt daemon is running:
```bash
sudo systemctl status libvirtd
```

### Snapshot Errors
- Snapshots require the VM to use qcow2 disk format with copy-on-write support
- Internal snapshots are supported for single-disk VMs; external snapshots may require additional configuration

## License

MIT License

## Credits

This project uses:
- [prefecthq/fastmcp](https://github.com/prefecthq/fastmcp) - FastMCP library for building MCP servers
- [libvirt-python](https://libvirt.org/) - Python bindings for libvirt/KVM
