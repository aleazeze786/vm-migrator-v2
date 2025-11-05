from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


class ProviderType(str, Enum):
    proxmox = "proxmox"
    vcenter = "vcenter"


class ProviderCreate(BaseModel):
    name: str
    type: ProviderType
    api_url: str
    username: Optional[str] = None
    secret: Optional[str] = None
    verify_ssl: bool = True


class ProviderOut(BaseModel):
    id: int
    name: str
    type: ProviderType
    api_url: str
    username: Optional[str]
    verify_ssl: bool

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    source_provider_id: int
    destination_provider_id: int
    source_vm_id: int
    target_node: Optional[str] = None


class BatchJobCreate(BaseModel):
    source_provider_id: int
    destination_provider_id: int
    source_vm_ids: List[int]
    target_node: Optional[str] = None


class JobOut(BaseModel):
    id: int
    vm_name: str
    status: str
    progress: int
    source_provider_id: Optional[int]
    destination_provider_id: Optional[int]
    source_vm_id: Optional[int]
    target_node: Optional[str]

    class Config:
        from_attributes = True


class VCenterDatacenterOut(BaseModel):
    id: int
    name: str
    moid: str

    class Config:
        from_attributes = True


class VCenterHostOut(BaseModel):
    id: int
    name: str
    moid: str
    datacenter_id: Optional[int]
    cpu_cores: Optional[int]
    memory_bytes: Optional[int]
    product: Optional[str]
    version: Optional[str]

    class Config:
        from_attributes = True


class VirtualMachineOut(BaseModel):
    id: int
    name: str
    source_identifier: str
    power_state: Optional[str]
    cpu_count: Optional[int]
    memory_bytes: Optional[int]
    storage_gb: Optional[float]
    os: Optional[str]
    vcenter_host_id: Optional[int]

    class Config:
        from_attributes = True


class ProxmoxNodeOut(BaseModel):
    id: int
    name: str
    status: Optional[str]
    cpu_usage: Optional[float]
    memory_usage: Optional[int]

    class Config:
        from_attributes = True


class SystemLogOut(BaseModel):
    id: int
    level: str
    component: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
