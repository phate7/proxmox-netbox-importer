from __future__ import annotations

from dataclasses import dataclass
import os
import re
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

        # Optional: map Proxmox ostype -> NetBox platform slug (create if missing)
        # Examples: l26->linux, win11->windows
        self.platform_map = {
            "l26": "linux",
            "l24": "linux",
            "win10": "windows",
            "win11": "windows",
            "w2k": "windows",
            "w2k3": "windows",
            "w2k8": "windows",
            "wvista": "windows",
            "wxp": "windows",
        }

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

    def get_platform_by_slug(self, slug: str) -> dict[str, Any] | None:
        data = self._get("dcim/platforms/", params={"slug": slug, "limit": 1})
        results = data.get("results") or []
        return results[0] if results else None

    def get_or_create_platform(self, slug: str) -> int | None:
        slug = slug.strip().lower()
        if not slug:
            return None
        existing = self.get_platform_by_slug(slug)
        if existing:
            return int(existing["id"])
        # Create a minimal platform
        name = slug.replace("-", " ")
        created = self._post("dcim/platforms/", json={"name": name, "slug": slug})
        return int(created["id"])

    def build_vm_payload_from_proxmox(self, vm: Any) -> dict[str, Any]:
        payload: Dict[str, Any] = {
            "name": vm.name,
            "status": self.default_status,
        }

        # CPU/RAM
        if getattr(vm, "vcpus", None) is not None:
            payload["vcpus"] = vm.vcpus
        elif getattr(vm, "maxcpu", None) is not None:
            payload["vcpus"] = vm.maxcpu

        if getattr(vm, "maxmem_mb", None) is not None:
            payload["memory"] = vm.maxmem_mb

        # Disk (GB)
        if getattr(vm, "disk_gb", None) is not None:
            payload["disk"] = vm.disk_gb

        # Platform (best-effort from ostype)
        ostype = getattr(vm, "ostype", None)
        if isinstance(ostype, str) and ostype:
            slug = self.platform_map.get(ostype)
            if slug:
                platform_id = self.get_or_create_platform(slug)
                if platform_id:
                    payload["platform"] = platform_id

        if self.default_cluster_id:
            payload["cluster"] = int(self.default_cluster_id)

        if self.default_tenant_id:
            payload["tenant"] = int(self.default_tenant_id)

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
