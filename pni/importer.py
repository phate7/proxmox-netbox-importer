from __future__ import annotations

from dataclasses import dataclass

from pni.netbox import NetBoxClient
from pni.proxmox import ProxmoxClient


@dataclass
class ImportSummary:
    scanned: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0

    def to_text(self) -> str:
        return (
            "ImportSummary\n"
            f"  scanned: {self.scanned}\n"
            f"  created: {self.created}\n"
            f"  updated: {self.updated}\n"
            f"  skipped: {self.skipped}\n"
        )


def run_import(*, dry_run: bool, update_existing: bool) -> ImportSummary:
    pve = ProxmoxClient.from_env()
    nb = NetBoxClient.from_env()

    summary = ImportSummary()

    vms = pve.list_all_vms()
    summary.scanned = len(vms)

    for vm in vms:
        desired = nb.build_vm_payload_from_proxmox(vm)

        existing = nb.get_vm_by_name(vm.name)
        if existing is None:
            if dry_run:
                summary.created += 1
                continue
            nb.create_vm(desired)
            summary.created += 1
            continue

        if not update_existing:
            summary.skipped += 1
            continue

        patch = nb.diff_vm(existing, desired)
        if not patch:
            summary.skipped += 1
            continue

        if dry_run:
            summary.updated += 1
            continue

        nb.update_vm(existing["id"], patch)
        summary.updated += 1

    return summary
