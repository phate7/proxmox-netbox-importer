from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Any

import requests


@dataclass(frozen=True)
class ProxmoxVM:
    vmid: int
    name: str
    node: str
    status: str | None = None
    maxmem_mb: int | None = None

    # CPU
    cores: int | None = None
    sockets: int | None = None
    vcpus: int | None = None

    # Storage
    disk_gb: int | None = None

    # OS (Proxmox ostype like l26, win11, etc.)
    ostype: str | None = None

    tags: list[str] | None = None


class ProxmoxClient:
    def __init__(self, *, base_url: str, token_id: str, token_secret: str, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update(
            {
                "Authorization": f"PVEAPIToken={token_id}={token_secret}",
            }
        )

    @staticmethod
    def _parse_size_to_gb(spec: str) -> int | None:
        """Parse disk size like '32G', '512M', '1T' to integer GB (rounded up)."""
        m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([KMGTP])\s*$", spec.strip(), flags=re.I)
        if not m:
            return None
        num = float(m.group(1))
        unit = m.group(2).upper()
        # base 1024
        factor = {"K": 1 / 1024 / 1024, "M": 1 / 1024, "G": 1, "T": 1024, "P": 1024 * 1024}[unit]
        gb = num * factor
        # round up to at least 1 GB if non-zero
        return max(1, int(gb + 0.9999))

    def _get_qemu_config(self, node: str, vmid: int) -> dict[str, Any]:
        return self._get(f"/nodes/{node}/qemu/{vmid}/config")

    @classmethod
    def from_env(cls) -> "ProxmoxClient":
        base_url = os.environ["PVE_BASE_URL"]
        token_id = os.environ["PVE_TOKEN_ID"]
        token_secret = os.environ["PVE_TOKEN_SECRET"]
        verify_ssl = os.getenv("PVE_VERIFY_SSL", "true").strip().lower() in {"1", "true", "yes", "y", "on"}
        return cls(base_url=base_url, token_id=token_id, token_secret=token_secret, verify_ssl=verify_ssl)

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}/api2/json{path}"
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return r.json()["data"]

    def list_nodes(self) -> list[str]:
        data = self._get("/nodes")
        return [n["node"] for n in data]

    def list_all_vms(self) -> list[ProxmoxVM]:
        vms: list[ProxmoxVM] = []
        for node in self.list_nodes():
            for entry in self._get(f"/nodes/{node}/qemu"):
                vmid = int(entry["vmid"])
                name = entry.get("name") or f"vm-{vmid}"
                status = entry.get("status")
                maxmem = entry.get("maxmem")
                tags_raw = entry.get("tags")
                tags = tags_raw.split(";") if isinstance(tags_raw, str) and tags_raw else None

                maxmem_mb = int(maxmem / 1024 / 1024) if isinstance(maxmem, (int, float)) else None

                # Pull per-VM config for richer fields
                cfg = self._get_qemu_config(node, vmid)

                cores = int(cfg.get("cores")) if str(cfg.get("cores") or "").isdigit() else None
                sockets = int(cfg.get("sockets")) if str(cfg.get("sockets") or "").isdigit() else None
                vcpus = None
                if cores and sockets:
                    vcpus = cores * sockets
                elif cores:
                    vcpus = cores
                elif sockets:
                    vcpus = sockets

                ostype = cfg.get("ostype")

                # Best-effort disk size: take the largest disk 'size=' found in scsi/sata/virtio/ide entries
                disk_gb = None
                disk_fields = [k for k in cfg.keys() if k.startswith(("scsi", "sata", "virtio", "ide"))]
                sizes: list[int] = []
                for k in disk_fields:
                    val = cfg.get(k)
                    if not isinstance(val, str):
                        continue
                    m = re.search(r"(?:^|,)size=([^,]+)", val)
                    if m:
                        gb = self._parse_size_to_gb(m.group(1))
                        if gb:
                            sizes.append(gb)
                if sizes:
                    disk_gb = max(sizes)

                vms.append(
                    ProxmoxVM(
                        vmid=vmid,
                        name=name,
                        node=node,
                        status=status,
                        maxmem_mb=maxmem_mb,
                        cores=cores,
                        sockets=sockets,
                        vcpus=vcpus,
                        disk_gb=disk_gb,
                        ostype=ostype,
                        tags=tags,
                    )
                )
        return vms
