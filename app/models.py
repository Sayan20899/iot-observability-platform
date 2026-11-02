from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(80), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    location = Column(String(120), nullable=False, default="Unknown")
    status = Column(String(30), nullable=False, default="online")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    telemetry = relationship("Telemetry", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")

class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(80), ForeignKey("devices.device_id"), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    power = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    device = relationship("Device", back_populates="telemetry")
    __table_args__ = (Index("ix_telemetry_device_recorded", "device_id", "recorded_at"),)

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(80), ForeignKey("devices.device_id"), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    message = Column(String(250), nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    device = relationship("Device", back_populates="alerts")
