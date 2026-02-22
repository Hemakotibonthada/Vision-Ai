"""
Vision-AI Device Management Routes
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy import select, desc, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, Device, SensorData, SystemConfig

router = APIRouter(tags=["Devices"])


@router.get("/devices")
async def list_devices(
    device_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List all registered devices."""
    query = select(Device).order_by(desc(Device.last_seen))
    if device_type:
        query = query.where(Device.device_type == device_type)
    if is_active is not None:
        query = query.where(Device.is_active == is_active)
    result = await db.execute(query)
    devices = result.scalars().all()
    return [{
        "id": d.id, "device_id": d.device_id, "name": d.name,
        "device_type": d.device_type, "ip_address": d.ip_address,
        "mac_address": d.mac_address, "firmware_version": d.firmware_version,
        "is_active": d.is_active, "last_seen": d.last_seen.isoformat() if d.last_seen else None,
        "config": d.config, "capabilities": d.capabilities,
        "location": d.location
    } for d in devices]


@router.post("/devices")
async def register_device(device: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Register a new device."""
    existing = await db.execute(
        select(Device).where(Device.device_id == device.get("device_id"))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Device already registered")

    db_device = Device(
        device_id=device.get("device_id", ""),
        name=device.get("name", ""),
        device_type=device.get("device_type", "esp32"),
        ip_address=device.get("ip_address"),
        mac_address=device.get("mac_address"),
        firmware_version=device.get("firmware_version"),
        config=device.get("config"),
        capabilities=device.get("capabilities"),
        location=device.get("location")
    )
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return {"id": db_device.id, "device_id": db_device.device_id, "status": "registered"}


@router.get("/devices/{device_id}")
async def get_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get device details."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {
        "id": device.id, "device_id": device.device_id, "name": device.name,
        "device_type": device.device_type, "ip_address": device.ip_address,
        "mac_address": device.mac_address, "firmware_version": device.firmware_version,
        "is_active": device.is_active, "last_seen": device.last_seen.isoformat() if device.last_seen else None,
        "config": device.config, "capabilities": device.capabilities, "location": device.location
    }


@router.put("/devices/{device_id}")
async def update_device(device_id: str, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Update device configuration."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    for key in ["name", "config", "capabilities", "location", "firmware_version"]:
        if key in data:
            setattr(device, key, data[key])
    await db.commit()
    return {"device_id": device_id, "status": "updated"}


@router.delete("/devices/{device_id}")
async def delete_device(device_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a device."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.delete(device)
    await db.commit()
    return {"device_id": device_id, "status": "deleted"}


@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(device_id: str, data: dict = Body({}), db: AsyncSession = Depends(get_db)):
    """Update device heartbeat / last seen."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        # Auto-register
        device = Device(device_id=device_id, name=device_id, device_type=data.get("type", "esp32"))
        db.add(device)
    device.last_seen = datetime.utcnow()
    device.is_active = True
    if "ip_address" in data:
        device.ip_address = data["ip_address"]
    if "firmware_version" in data:
        device.firmware_version = data["firmware_version"]
    await db.commit()
    return {"status": "ok"}


@router.post("/devices/{device_id}/command")
async def send_command(device_id: str, cmd: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Send a command to device via MQTT."""
    from app.services.mqtt_service import mqtt_service
    topic = f"vision-ai/devices/{device_id}/command"
    import json
    mqtt_service.publish(topic, json.dumps(cmd))
    return {"status": "sent", "topic": topic, "command": cmd}


@router.get("/devices/{device_id}/sensors")
async def get_device_sensors(
    device_id: str,
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(500, le=5000),
    db: AsyncSession = Depends(get_db)
):
    """Get device sensor data."""
    cutoff = datetime.utcnow() - __import__("datetime").timedelta(hours=hours)
    result = await db.execute(
        select(SensorData)
        .where(SensorData.device_id == device_id, SensorData.created_at >= cutoff)
        .order_by(desc(SensorData.created_at))
        .limit(limit)
    )
    data = result.scalars().all()
    return [{
        "id": d.id, "sensor_type": d.sensor_type,
        "value": d.value, "unit": d.unit,
        "metadata": d.metadata,
        "created_at": d.created_at.isoformat()
    } for d in data]


@router.post("/devices/{device_id}/sensors")
async def push_sensor_data(device_id: str, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Push sensor data from device."""
    readings = data.get("readings", [data])
    created = []
    for r in readings:
        sensor = SensorData(
            device_id=device_id,
            sensor_type=r.get("sensor_type", "unknown"),
            value=r.get("value", 0.0),
            unit=r.get("unit"),
            metadata=r.get("metadata")
        )
        db.add(sensor)
        created.append(sensor)
    await db.commit()
    return {"status": "ok", "count": len(created)}


@router.get("/devices/{device_id}/status")
async def get_device_status(device_id: str, db: AsyncSession = Depends(get_db)):
    """Get comprehensive device status."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Recent sensor data
    sensor_result = await db.execute(
        select(SensorData)
        .where(SensorData.device_id == device_id)
        .order_by(desc(SensorData.created_at))
        .limit(10)
    )
    recent_sensors = sensor_result.scalars().all()
    
    return {
        "device": {
            "id": device.device_id, "name": device.name,
            "is_active": device.is_active,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "firmware": device.firmware_version
        },
        "sensors": [{
            "type": s.sensor_type, "value": s.value, "unit": s.unit,
            "at": s.created_at.isoformat()
        } for s in recent_sensors],
        "online": device.is_active and device.last_seen and
                  (datetime.utcnow() - device.last_seen).seconds < 300
    }


# ---- System Config ----

@router.get("/system/config")
async def get_system_config(db: AsyncSession = Depends(get_db)):
    """Get all system configuration."""
    result = await db.execute(select(SystemConfig))
    configs = result.scalars().all()
    return {c.key: {"value": c.value, "description": c.description} for c in configs}


@router.put("/system/config/{key}")
async def set_system_config(key: str, data: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Set a system configuration value."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        config.value = data.get("value")
        config.description = data.get("description", config.description)
    else:
        config = SystemConfig(key=key, value=data.get("value"), description=data.get("description"))
        db.add(config)
    await db.commit()
    return {"key": key, "status": "updated"}


@router.get("/system/health")
async def system_health(db: AsyncSession = Depends(get_db)):
    """System health check."""
    import psutil
    import torch
    
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
    except Exception:
        cpu_percent = 0
        memory = type("M", (), {"percent": 0, "total": 0, "available": 0})()
        disk = type("D", (), {"percent": 0, "total": 0, "free": 0})()
    
    gpu_available = torch.cuda.is_available() if torch else False
    gpu_info = {}
    if gpu_available:
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "memory_allocated": torch.cuda.memory_allocated(0),
            "memory_total": torch.cuda.get_device_properties(0).total_mem
        }
    
    # Count active devices
    active_result = await db.execute(
        select(func.count(Device.id)).where(Device.is_active == True)
    )
    active_devices = active_result.scalar()
    
    return {
        "status": "healthy",
        "cpu_percent": cpu_percent,
        "memory": {"percent": memory.percent, "total": memory.total, "available": memory.available},
        "disk": {"percent": disk.percent, "total": disk.total, "free": disk.free},
        "gpu": {"available": gpu_available, **gpu_info},
        "active_devices": active_devices,
        "timestamp": datetime.utcnow().isoformat()
    }
