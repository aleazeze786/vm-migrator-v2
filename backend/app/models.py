from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base
import enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey  # add ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship 
Base = declarative_base()

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

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    vm_name = Column(String(255), nullable=False)
    status = Column(String(32), default="queued")
    progress = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=False)
    message = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
