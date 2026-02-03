from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Dict

import requests


class NetBoxClient:
    def __init__(self, *, base_url: str, token: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        self.default_status = os.getenv("NETBOX_VM_DEFAULT_STATUS", "active")
        self.default_cluster_id = os.getenv("NETBOX_VM_DEFAULT_CLUSTER_ID")
        self.default_tenant_id = os.getenv("NETBOX_VM_DEFAULT_TENANT_ID")

    @classmethod
    def from_env(cls) -> "NetBoxClient":
        base_url = os.environ["NETBOX_BASE_URL"]
        token = os.environ["NETBOX_TOKEN"]
        verify_ssl = os.getenv("NETBOX_VERIFY_SSL", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
        return cls(base_url=base_url, token=token, verify_ssl=verify_ssl)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/{path.lstrip('/')}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        r = self.session.get(self._url(path), params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: Any) -> Any:
        r = self.session.post(self._url(path), json=json, timeout=30)
        r.raise_for_status()
        return r.json()

    def _patch(self, path: str, json: Any) -> Any:
        r = self.session.patch(self._url(path), json=json, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_vm_by_name(self, name: str) -> dict[str, Any] | None:
        data = self._get("virtualization/virtual-machines/", params={"name": name, "limit": 1})
        results = data.get("results") or []
        return results[0] if results else None

    def create_vm(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("virtualization/virtual-machines/", json=payload)

    def update_vm(self, vm_id: int, patch: dict[str, Any]) -> dict[str, Any]:
        return self._patch(f"virtualization/virtual-machines/{vm_id}/", json=patch)

    def build_vm_payload_from_proxmox(self, vm: Any) -> dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": vm.name,
            "status": self.default_status,
        }

        # Optional fields
        if vm.maxcpu is not None:
            payload["vcpus"] = vm.maxcpu
        if vm.maxmem_mb is not None:
            payload["memory"] = vm.maxmem_mb

        if self.default_cluster_id:
            payload["cluster"] = int(self.default_cluster_id)

        if self.default_tenant_id:
            payload["tenant"] = int(self.default_tenant_id)

        # If you have a custom field in NetBox, you can enable this:
        # payload["custom_fields"] = {"proxmox_vmid": vm.vmid, "proxmox_node": vm.node}

        return payload

    def diff_vm(self, existing: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
        """Return patch dict with changed fields only."""
        patch: dict[str, Any] = {}
        for k, v in desired.items():
            if k not in existing:
                patch[k] = v
                continue
            if existing[k] != v:
                patch[k] = v
        return patch
