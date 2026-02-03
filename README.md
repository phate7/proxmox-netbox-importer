# proxmox-netbox-importer

Python-Skript/CLI zum Import von Proxmox VE VMs in **NetBox**.

## Features

- Liest VMs aus Proxmox (über Proxmox REST API)
- Erstellt/aktualisiert VMs in NetBox (Virtualization → Virtual Machines)
- Idempotent: optionales **Update** existierender Einträge
- Mapping über Tags/Cluster/Node möglich (konfigurierbar)

> Hinweis: NetBox-Datenmodell ist oft org-spezifisch (Tenant/Site/Cluster/Role). Das Tool ist daher bewusst konfigurierbar.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Konfiguration (ENV)

### Proxmox

- `PVE_BASE_URL` (z.B. `https://pve.example.com:8006`)
- `PVE_TOKEN_ID` (z.B. `root@pam!netbox-import`)
- `PVE_TOKEN_SECRET`
- `PVE_VERIFY_SSL` (`true|false`, default: `true`)

### NetBox

- `NETBOX_BASE_URL` (z.B. `https://netbox.example.com`)
- `NETBOX_TOKEN`
- `NETBOX_VERIFY_SSL` (`true|false`, default: `true`)

### Import-Verhalten

- `NETBOX_VM_DEFAULT_STATUS` (default: `active`)
- `NETBOX_VM_DEFAULT_CLUSTER_ID` (optional)
- `NETBOX_VM_DEFAULT_TENANT_ID` (optional)
- `DRY_RUN` (`true|false`, default: `false`)
- `UPDATE_EXISTING` (`true|false`, default: `true`)

## Usage

```bash
proxmox-netbox-import --help

# Beispiel
export PVE_BASE_URL="https://pve:8006"
export PVE_TOKEN_ID="root@pam!netbox-import"
export PVE_TOKEN_SECRET="..."

export NETBOX_BASE_URL="https://netbox"
export NETBOX_TOKEN="..."

proxmox-netbox-import
```

## Was wird gemappt?

Standardmäßig:

- Proxmox VMID → Custom Field `proxmox_vmid` (optional)
- Name → NetBox VM `name`
- CPU/RAM → `vcpus`, `memory`
- Node/Cluster → `cluster` (wenn konfiguriert)

## Roadmap / Anpassungen

Sag mir kurz, wie du’s in NetBox modelliert hast (Cluster/Site/Tenant/Tags), dann passe ich das Mapping an.

## License

MIT
