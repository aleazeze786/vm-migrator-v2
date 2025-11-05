from __future__ import annotations

import ssl
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, List, Optional
from urllib.parse import urlparse

from pyVim import connect
from pyVmomi import vim


class VCenterError(Exception):
    """Raised when we cannot communicate with vCenter."""


@dataclass
class VCenterDatacenterInfo:
    name: str
    moid: str


@dataclass
class VCenterHostInfo:
    name: str
    moid: str
    datacenter_moid: Optional[str]
    cpu_cores: Optional[int]
    memory_bytes: Optional[int]
    product: Optional[str]
    version: Optional[str]


@dataclass
class VCenterVMInfo:
    name: str
    moid: str
    host_moid: Optional[str]
    power_state: Optional[str]
    cpu_count: Optional[int]
    memory_bytes: Optional[int]
    storage_gb: Optional[float]
    os: Optional[str]


@dataclass
class VCenterInventory:
    datacenters: List[VCenterDatacenterInfo]
    hosts: List[VCenterHostInfo]
    virtual_machines: List[VCenterVMInfo]


def _build_ssl_context(verify_ssl: bool) -> Optional[ssl.SSLContext]:
    if verify_ssl:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


@contextmanager
def vcenter_connection(
    api_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True,
) -> Generator[vim.ServiceInstance, None, None]:
    """Context manager that yields a live vCenter service instance."""
    parsed = urlparse(api_url)
    # Allow users to paste either base host or full SDK URL.
    host = parsed.hostname or api_url
    if not host:
        raise VCenterError("vCenter URL is missing a hostname")
    port = parsed.port or 443
    ssl_context = _build_ssl_context(verify_ssl)
    try:
        si = connect.SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=port,
            sslContext=ssl_context,
        )
    except Exception as exc:  # pragma: no cover - depends on remote endpoint
        raise VCenterError(f"Failed to connect to vCenter at {host}:{port}: {exc}") from exc

    try:
        yield si
    finally:  # pragma: no cover - network teardown
        connect.Disconnect(si)


def _find_parent_datacenter(obj) -> Optional[vim.Datacenter]:
    parent = getattr(obj, "parent", None)
    while parent is not None:
        if isinstance(parent, vim.Datacenter):
            return parent
        parent = getattr(parent, "parent", None)
    return None


def _memory_mb_to_bytes(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return int(value) * 1024 * 1024


def _bytes_to_gb(value: Optional[int]) -> Optional[float]:
    if value is None:
        return None
    return round(value / (1024 ** 3), 2)


def fetch_inventory(
    api_url: str,
    username: str,
    password: str,
    verify_ssl: bool = True,
) -> VCenterInventory:
    """Collect datacenters, hosts, and VMs from vCenter."""
    datacenters: List[VCenterDatacenterInfo] = []
    hosts: List[VCenterHostInfo] = []
    vms: List[VCenterVMInfo] = []

    with vcenter_connection(api_url, username, password, verify_ssl) as si:
        content = si.RetrieveContent()
        view_mgr = content.viewManager
        if not view_mgr:
            raise VCenterError("vCenter returned no view manager")

        # Datacenters
        dc_view = view_mgr.CreateContainerView(
            content.rootFolder, [vim.Datacenter], True
        )
        try:
            for dc in dc_view.view:
                datacenters.append(
                    VCenterDatacenterInfo(
                        name=dc.name,
                        moid=dc._moId,
                    )
                )
        finally:
            dc_view.Destroy()

        # Hosts
        host_view = view_mgr.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True
        )
        try:
            for host in host_view.view:
                summary = host.summary
                hardware = getattr(summary, "hardware", None)
                prod = getattr(getattr(summary, "config", None), "product", None)
                datacenter = _find_parent_datacenter(host)
                hosts.append(
                    VCenterHostInfo(
                        name=host.name,
                        moid=host._moId,
                        datacenter_moid=datacenter._moId if datacenter else None,
                        cpu_cores=getattr(hardware, "numCpuCores", None),
                        memory_bytes=getattr(hardware, "memorySize", None),
                        product=getattr(prod, "name", None),
                        version=getattr(prod, "version", None),
                    )
                )
        finally:
            host_view.Destroy()

        # VMs
        vm_view = view_mgr.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        try:
            for vm in vm_view.view:
                summary = vm.summary
                runtime = getattr(summary, "runtime", None)
                config = getattr(summary, "config", None)
                storage = getattr(summary, "storage", None)
                host = runtime.host if runtime else None
                vms.append(
                    VCenterVMInfo(
                        name=vm.name,
                        moid=vm._moId,
                        host_moid=host._moId if host else None,
                        power_state=getattr(runtime, "powerState", None),
                        cpu_count=getattr(config, "numCpu", None),
                        memory_bytes=_memory_mb_to_bytes(
                            getattr(config, "memorySizeMB", None)
                        ),
                        storage_gb=_bytes_to_gb(
                            getattr(storage, "committed", None)
                        ),
                        os=getattr(config, "guestFullName", None),
                    )
                )
        finally:
            vm_view.Destroy()

    return VCenterInventory(
        datacenters=datacenters, hosts=hosts, virtual_machines=vms
    )
