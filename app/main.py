import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Alert, Device, Telemetry
from app.schemas import DeviceCreate, TelemetryCreate

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(
    title="IoT Observability Platform",
    description="Device monitoring, telemetry analytics and alert management API",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(BASE_DIR / "templates" / "index.html")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "iot-observability-api",
            "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/devices")
def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Device).order_by(Device.id).all()
    output = []
    for device in devices:
        latest = (db.query(Telemetry).filter(Telemetry.device_id == device.device_id)
                  .order_by(desc(Telemetry.recorded_at)).first())
        output.append({
            "id": device.id, "device_id": device.device_id, "name": device.name,
            "location": device.location, "status": device.status,
            "last_temperature": latest.temperature if latest else None,
            "last_seen": latest.recorded_at.isoformat() if latest else None,
        })
    return output

@app.post("/api/devices", status_code=201)
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    if db.query(Device).filter(Device.device_id == payload.device_id).first():
        raise HTTPException(status_code=409, detail="Device already exists")
    device = Device(device_id=payload.device_id, name=payload.name,
                    location=payload.location, status="online")
    db.add(device)
    db.commit()
    db.refresh(device)
    return {"message": "Device registered", "device_id": device.device_id}

@app.post("/api/telemetry", status_code=201)
def ingest_telemetry(payload: TelemetryCreate, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")
    reading = Telemetry(**payload.model_dump())
    db.add(reading)
    device.status = "online"
    if payload.temperature > 40:
        db.add(Alert(device_id=payload.device_id, severity="critical",
                     message=f"High temperature: {payload.temperature:.1f} °C"))
    if payload.humidity > 85:
        db.add(Alert(device_id=payload.device_id, severity="warning",
                     message=f"High humidity: {payload.humidity:.1f}%"))
    db.commit()
    return {"message": "Telemetry received", "device_id": payload.device_id}

@app.get("/api/telemetry")
def get_telemetry(limit: int = Query(100, ge=1, le=1000),
                  device_id: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Telemetry)
    if device_id:
        query = query.filter(Telemetry.device_id == device_id)
    rows = query.order_by(desc(Telemetry.recorded_at)).limit(limit).all()
    return [{"id": r.id, "device_id": r.device_id, "temperature": r.temperature,
             "humidity": r.humidity, "power": r.power,
             "recorded_at": r.recorded_at.isoformat()} for r in rows]

@app.get("/api/summary")
def get_summary(db: Session = Depends(get_db)):
    devices = db.query(func.count(Device.id)).scalar() or 0
    online = db.query(func.count(Device.id)).filter(Device.status == "online").scalar() or 0
    readings = db.query(func.count(Telemetry.id)).scalar() or 0
    alerts = db.query(func.count(Alert.id)).filter(Alert.acknowledged.is_(False)).scalar() or 0
    average = db.query(func.avg(Telemetry.temperature)).scalar()
    return {"total_devices": devices, "online_devices": online, "total_readings": readings,
            "active_alerts": alerts, "average_temperature": round(average, 2) if average is not None else 0}

@app.get("/api/series")
def get_series(hours: int = Query(24, ge=1, le=168), device_id: str | None = None,
               db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = db.query(Telemetry).filter(Telemetry.recorded_at >= cutoff)
    if device_id:
        query = query.filter(Telemetry.device_id == device_id)
    rows = query.order_by(Telemetry.recorded_at).all()
    return [{"time": r.recorded_at.isoformat(), "device_id": r.device_id,
             "temperature": r.temperature, "humidity": r.humidity, "power": r.power}
            for r in rows]

@app.get("/api/alerts")
def get_alerts(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(Alert).order_by(desc(Alert.created_at)).limit(limit).all()
    return [{"id": a.id, "device_id": a.device_id, "severity": a.severity,
             "message": a.message, "acknowledged": a.acknowledged,
             "created_at": a.created_at.isoformat()} for a in rows]

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    return {"message": "Alert acknowledged", "alert_id": alert_id}

@app.post("/api/demo/generate")
def generate_demo_data(db: Session = Depends(get_db)):
    definitions = [
        ("IOT-001", "Temperature Sensor A", "Production Floor"),
        ("IOT-002", "Humidity Sensor B", "Warehouse"),
        ("IOT-003", "Power Monitor C", "Control Room"),
        ("IOT-004", "Environmental Sensor D", "Laboratory"),
    ]
    for device_id, name, location in definitions:
        if not db.query(Device).filter(Device.device_id == device_id).first():
            db.add(Device(device_id=device_id, name=name, location=location, status="online"))
    db.commit()
    now = datetime.now(timezone.utc)
    count = 0
    for device_id, _, _ in definitions:
        for offset in range(23, -1, -1):
            db.add(Telemetry(
                device_id=device_id,
                temperature=round(random.uniform(21, 43), 2),
                humidity=round(random.uniform(30, 92), 2),
                power=round(random.uniform(12, 96), 2),
                recorded_at=now - timedelta(hours=offset),
            ))
            count += 1
    db.commit()
    return {"message": "Demo data generated", "devices": len(definitions), "readings_generated": count}

@app.delete("/api/demo/reset")
def reset_demo_data(db: Session = Depends(get_db)):
    # This endpoint is intended for a local demo environment only.
    db.query(Alert).delete()
    db.query(Telemetry).delete()
    db.query(Device).delete()
    db.commit()
    return {"message": "All demo records cleared"}
