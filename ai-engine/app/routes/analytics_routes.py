"""
Vision-AI Analytics & Alert Routes
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, Event, AlertRule, Zone
from app.services.analytics_service import analytics_service
from app.services.alert_service import alert_service

router = APIRouter(tags=["Analytics & Alerts"])


# ---- Analytics ----

@router.get("/analytics/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Get dashboard summary data."""
    return await analytics_service.get_dashboard_summary(db)


@router.get("/analytics/timeline")
async def get_timeline(
    hours: int = Query(24, ge=1, le=720),
    interval: int = Query(60, ge=5, le=1440),
    db: AsyncSession = Depends(get_db)
):
    """Get detection timeline."""
    return await analytics_service.get_detection_timeline(db, hours, interval)


@router.get("/analytics/peak-hours")
async def get_peak_hours(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get peak detection hours."""
    return await analytics_service.get_peak_hours(db, days)


@router.get("/analytics/trends")
async def get_trends(
    period: str = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get detection trends."""
    return await analytics_service.get_trends(db, period, days)


@router.get("/analytics/compare")
async def compare_periods(
    start1: datetime = Query(...),
    end1: datetime = Query(...),
    start2: datetime = Query(...),
    end2: datetime = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Compare two time periods."""
    return await analytics_service.compare_periods(db, start1, end1, start2, end2)


@router.get("/analytics/zones/{zone_id}")
async def get_zone_analytics(
    zone_id: int,
    hours: int = Query(24),
    db: AsyncSession = Depends(get_db)
):
    """Get zone occupancy analytics."""
    return await analytics_service.get_zone_analytics(db, zone_id, hours)


@router.post("/analytics/confusion-matrix")
async def generate_confusion_matrix(data: dict = Body(...)):
    """Generate confusion matrix from predictions and ground truth."""
    return await analytics_service.generate_confusion_matrix(
        data.get("predictions", []),
        data.get("ground_truth", [])
    )


@router.post("/analytics/precision-recall")
async def get_precision_recall(data: dict = Body(...)):
    """Generate precision-recall curves."""
    return await analytics_service.precision_recall_curve(
        data.get("detections", []),
        data.get("thresholds")
    )


@router.get("/analytics/datasets/{dataset_id}/stats")
async def get_dataset_stats(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Get dataset statistics."""
    return await analytics_service.get_dataset_stats(db, dataset_id)


@router.get("/analytics/report")
async def generate_report(
    report_type: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Generate analytics report."""
    return await analytics_service.generate_report(db, report_type, start, end)


# ---- Events ----

@router.get("/events")
async def list_events(
    event_type: Optional[str] = Query(None),
    severity: Optional[int] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """List events with filtering."""
    from sqlalchemy import select, desc
    
    query = select(Event).order_by(desc(Event.created_at))
    if event_type:
        query = query.where(Event.event_type == event_type)
    if severity:
        query = query.where(Event.severity >= severity)
    
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    
    return [{
        "id": e.id, "type": e.event_type, "severity": e.severity,
        "title": e.title, "description": e.description,
        "data": e.data, "acknowledged": e.acknowledged,
        "created_at": e.created_at.isoformat() if e.created_at else None
    } for e in events]


@router.post("/events")
async def create_event(event: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Create a new event."""
    db_event = Event(
        event_type=event.get("type", "system"),
        severity=event.get("severity", 1),
        title=event.get("title", ""),
        description=event.get("description", ""),
        data=event.get("data"),
        image_path=event.get("image_path")
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    
    # Evaluate alert rules
    await alert_service.evaluate(event)
    
    return {"id": db_event.id, "status": "created"}


@router.put("/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Acknowledge an event."""
    from sqlalchemy import select
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.acknowledged = True
    await db.commit()
    return {"id": event_id, "acknowledged": True}


# ---- Alert Rules ----

@router.get("/alerts/rules")
async def list_alert_rules():
    """List all alert rules."""
    return alert_service.get_rules()


@router.post("/alerts/rules")
async def create_alert_rule(rule: dict = Body(...)):
    """Create alert rule."""
    alert_service.add_rule(rule)
    return {"status": "created", "rule": rule}


@router.get("/alerts/history")
async def get_alert_history(limit: int = Query(50)):
    """Get alert history."""
    return alert_service.get_history(limit)


@router.get("/alerts/stats")
async def get_alert_stats():
    """Get alert statistics."""
    return alert_service.get_stats()


# ---- Zones ----

@router.get("/zones")
async def list_zones(db: AsyncSession = Depends(get_db)):
    """List detection zones."""
    from sqlalchemy import select
    result = await db.execute(select(Zone))
    zones = result.scalars().all()
    return [{
        "id": z.id, "name": z.name, "camera_id": z.camera_id,
        "zone_type": z.zone_type, "points": z.points,
        "color": z.color, "is_active": z.is_active,
        "config": z.config
    } for z in zones]


@router.post("/zones")
async def create_zone(zone: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Create a detection zone."""
    db_zone = Zone(
        name=zone.get("name", ""),
        camera_id=zone.get("camera_id"),
        zone_type=zone.get("zone_type", "intrusion"),
        points=zone.get("points", []),
        color=zone.get("color", "#ff0000"),
        config=zone.get("config")
    )
    db.add(db_zone)
    await db.commit()
    await db.refresh(db_zone)
    return {"id": db_zone.id, "status": "created"}
