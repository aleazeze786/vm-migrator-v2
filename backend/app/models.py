import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    BigInteger,
    Float,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


class ProviderType(str, enum.Enum):
    proxmox = "proxmox"
    vcenter = "vcenter"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default="admin")


class Provider(Base):
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(Enum(ProviderType), nullable=False)
    api_url = Column(String(255), nullable=False)
    username = Column(String(128), nullable=True)
    secret = Column(String(255), nullable=True)   # dev-only storage; swap later
    verify_ssl = Column(Boolean, default=True)
    vcenter_datacenters = relationship(
        "VCenterDatacenter", cascade="all, delete-orphan", back_populates="provider"
    )
    vcenter_hosts = relationship(
        "VCenterHost", cascade="all, delete-orphan", back_populates="provider"
    )
    virtual_machines = relationship(
        "VirtualMachine", cascade="all, delete-orphan", back_populates="provider"
    )
    proxmox_nodes = relationship(
        "ProxmoxNode", cascade="all, delete-orphan", back_populates="provider"
    )


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(255), nullable=False)
    status = Column(String(32), default="queued")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    source_provider_id = Column(
        Integer, ForeignKey("providers.id"), nullable=True, index=True
    )
    destination_provider_id = Column(
        Integer, ForeignKey("providers.id"), nullable=True, index=True
    )
    source_vm_id = Column(
        Integer, ForeignKey("virtual_machines.id"), nullable=True, index=True
    )
    target_node = Column(String(255), nullable=True)
    source_provider = relationship(
        "Provider", foreign_keys=[source_provider_id], viewonly=True
    )
    destination_provider = relationship(
        "Provider", foreign_keys=[destination_provider_id], viewonly=True
    )
    source_vm = relationship(
        "VirtualMachine", foreign_keys=[source_vm_id], viewonly=True
    )


class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=False)
    message = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VCenterDatacenter(Base):
    __tablename__ = "vcenter_datacenters"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    moid = Column(String(128), nullable=False, unique=True)
    provider = relationship("Provider", back_populates="vcenter_datacenters")
    hosts = relationship(
        "VCenterHost", cascade="all, delete-orphan", back_populates="datacenter"
    )


class VCenterHost(Base):
    __tablename__ = "vcenter_hosts"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    datacenter_id = Column(
        Integer, ForeignKey("vcenter_datacenters.id"), nullable=True, index=True
    )
    name = Column(String(255), nullable=False)
    moid = Column(String(128), nullable=False, unique=True)
    cpu_cores = Column(Integer, nullable=True)
    memory_bytes = Column(BigInteger, nullable=True)
    product = Column(String(255), nullable=True)
    version = Column(String(64), nullable=True)
    provider = relationship("Provider", back_populates="vcenter_hosts")
    datacenter = relationship("VCenterDatacenter", back_populates="hosts")
    virtual_machines = relationship(
        "VirtualMachine",
        back_populates="vcenter_host",
        cascade="all, delete-orphan",
    )


class ProxmoxNode(Base):
    __tablename__ = "proxmox_nodes"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(64), nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(BigInteger, nullable=True)
    provider = relationship("Provider", back_populates="proxmox_nodes")


class VirtualMachine(Base):
    __tablename__ = "virtual_machines"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False, index=True)
    vcenter_host_id = Column(
        Integer, ForeignKey("vcenter_hosts.id"), nullable=True, index=True
    )
    source_identifier = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    power_state = Column(String(64), nullable=True)
    cpu_count = Column(Integer, nullable=True)
    memory_bytes = Column(BigInteger, nullable=True)
    storage_gb = Column(Float, nullable=True)
    os = Column(String(255), nullable=True)
    provider = relationship("Provider", back_populates="virtual_machines")
    vcenter_host = relationship("VCenterHost", back_populates="virtual_machines")


class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(16), nullable=False)
    component = Column(String(64), nullable=False)
    message = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
