from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from proxmoxer import ProxmoxAPI


class ProxmoxError(Exception):
    """Raised when the Proxmox API returns an error."""


@dataclass
class ProxmoxNodeInfo:
    name: str
    status: Optional[str]
    cpu_usage: Optional[float]
    memory_usage: Optional[int]


def _parse_connection_args(api_url: str) -> dict:
    parsed = urlparse(api_url)
    host = parsed.hostname or api_url
    if not host:
        raise ProxmoxError("Proxmox URL is missing a hostname")
    port = parsed.port or 8006
    # Proxmox API path normally ends with /api2/json but proxmoxer handles that.
    return {"host": host, "port": port}


def fetch_nodes(
    api_url: str,
    username: str,
    secret: str,
    verify_ssl: bool = True,
) -> List[ProxmoxNodeInfo]:
    """Return basic node information from Proxmox VE."""
    kwargs = _parse_connection_args(api_url)
    try:
        proxmox = ProxmoxAPI(
            kwargs["host"],
            user=username,
            password=secret,
            port=kwargs["port"],
            verify_ssl=verify_ssl,
        )
    except Exception as exc:  # pragma: no cover - remote dependency
        raise ProxmoxError(f"Failed to authenticate with Proxmox: {exc}") from exc

    try:
        nodes = proxmox.nodes.get()
    except Exception as exc:  # pragma: no cover - remote dependency
        raise ProxmoxError(f"Failed to list nodes: {exc}") from exc

    out: List[ProxmoxNodeInfo] = []
    for node in nodes:
        name = node.get("node")
        status = node.get("status")
        cpu_usage = node.get("cpu")
        memory_usage = node.get("mem")

        if name:
            out.append(
                ProxmoxNodeInfo(
                    name=name,
                    status=status,
                    cpu_usage=cpu_usage,
                    memory_usage=memory_usage,
                )
            )

    return out
