from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

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
    vm_name: str

class BatchJobCreate(BaseModel):
    provider_id: int
    vm_names: List[str]

class JobOut(BaseModel):
    id: int
    vm_name: str
    status: str
    progress: int
    class Config:
        from_attributes = True
