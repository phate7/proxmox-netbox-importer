from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import requests


@dataclass(frozen=True)
class ProxmoxVM:
    vmid: int
    name: str
    node: str
    status: str | None = None
    maxmem_mb: int | None = None
    maxcpu: int | None = None
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
                maxcpu = entry.get("maxcpu")
                tags_raw = entry.get("tags")
                tags = tags_raw.split(";") if isinstance(tags_raw, str) and tags_raw else None

                maxmem_mb = int(maxmem / 1024 / 1024) if isinstance(maxmem, (int, float)) else None
                maxcpu_int = int(maxcpu) if isinstance(maxcpu, (int, float)) else None

                vms.append(
                    ProxmoxVM(
                        vmid=vmid,
                        name=name,
                        node=node,
                        status=status,
                        maxmem_mb=maxmem_mb,
                        maxcpu=maxcpu_int,
                        tags=tags,
                    )
                )
        return vms
