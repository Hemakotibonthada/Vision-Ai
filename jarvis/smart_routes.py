"""
Jarvis AI - Smart Home Extended Routes
Features 26-50: Weather, energy, scene memory, predictions, calendar,
guests, sleep, NLU, conversations, habits, emergency, geofencing,
device health, timelapse, notifications, backup, scheduler, smart lighting
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/smart", tags=["Smart Home"])


# ========== Feature 26-27: Weather ==========

class WeatherUpdate(BaseModel):
    temperature: float = 22.0
    humidity: int = 55
    condition: str = "clear"
    wind_speed: float = 10
    pressure: float = 1013
    uv_index: int = 3

class WeatherRule(BaseModel):
    condition: dict  # {"field": "temperature", "op": ">", "value": 30}
    action: str

@router.get("/weather")
async def get_weather():
    from jarvis.services.weather_service import weather_service
    return weather_service.get_current()

@router.post("/weather")
async def update_weather(data: WeatherUpdate):
    from jarvis.services.weather_service import weather_service
    weather_service.update_weather(data.dict())
    return {"status": "updated"}

@router.get("/weather/forecast")
async def get_forecast():
    from jarvis.services.weather_service import weather_service
    return weather_service.get_forecast_summary()

@router.post("/weather/rules")
async def add_weather_rule(rule: WeatherRule):
    from jarvis.services.weather_service import weather_service
    weather_service.add_weather_rule(rule.dict())
    return {"status": "rule_added"}

@router.get("/weather/alerts")
async def get_weather_alerts():
    from jarvis.services.weather_service import weather_service
    return {"alerts": weather_service.get_alerts()}

@router.get("/weather/history")
async def get_weather_history(limit: int = Query(100)):
    from jarvis.services.weather_service import weather_service
    return {"history": weather_service.get_history(limit)}


# ========== Feature 28-29: Energy Monitoring ==========

class PowerUpdate(BaseModel):
    device_id: str
    watts: float
    voltage: float = 220
    current: float = 0

class EnergyBudget(BaseModel):
    daily_kwh: float = None
    monthly_kwh: float = None

@router.post("/energy/power")
async def update_power(data: PowerUpdate):
    from jarvis.services.energy_service import energy_service
    energy_service.update_power(data.device_id, data.watts, data.voltage, data.current)
    return {"status": "updated"}

@router.get("/energy/current")
async def get_energy_current():
    from jarvis.services.energy_service import energy_service
    return energy_service.get_current_usage()

@router.get("/energy/daily")
async def get_energy_daily():
    from jarvis.services.energy_service import energy_service
    return energy_service.get_daily_summary()

@router.get("/energy/tips")
async def get_energy_tips():
    from jarvis.services.energy_service import energy_service
    return {"tips": energy_service.get_optimization_tips()}

@router.post("/energy/budget")
async def set_energy_budget(budget: EnergyBudget):
    from jarvis.services.energy_service import energy_service
    energy_service.set_budget(budget.daily_kwh, budget.monthly_kwh)
    return {"status": "budget_set"}


# ========== Feature 30: Scene Memory ==========

class SceneState(BaseModel):
    room: str
    state: dict

@router.post("/scene/save")
async def save_scene(data: SceneState):
    from jarvis.services.smart_home_services import scene_memory
    scene_memory.save_scene(data.room, data.state)
    return {"status": "saved", "room": data.room}

@router.post("/scene/compare")
async def compare_scene(data: SceneState):
    from jarvis.services.smart_home_services import scene_memory
    return scene_memory.detect_changes(data.room, data.state)

@router.get("/scene/{room}")
async def get_scene(room: str):
    from jarvis.services.smart_home_services import scene_memory
    return scene_memory.get_room_state(room)

@router.get("/scene/changes/log")
async def get_change_log(limit: int = Query(50)):
    from jarvis.services.smart_home_services import scene_memory
    return {"changes": scene_memory.get_change_log(limit)}


# ========== Feature 31: Predictive Automation ==========

class BehaviorLog(BaseModel):
    action: str
    context: dict = {}

@router.post("/predict/log")
async def log_behavior(data: BehaviorLog):
    from jarvis.services.smart_home_services import predictive_service
    predictive_service.log_behavior(data.action, data.context)
    return {"status": "logged"}

@router.post("/predict/learn")
async def learn_patterns():
    from jarvis.services.smart_home_services import predictive_service
    return predictive_service.learn_patterns()

@router.get("/predict/next")
async def predict_next():
    from jarvis.services.smart_home_services import predictive_service
    return predictive_service.predict_next_action()

@router.get("/predict/suggestions")
async def get_suggestions():
    from jarvis.services.smart_home_services import predictive_service
    return {"suggestions": predictive_service.get_suggestions()}


# ========== Feature 32: Calendar ==========

class CalendarEvent(BaseModel):
    title: str
    start: str
    end: str = None
    recurring: str = None
    actions: list = []

@router.post("/calendar/events")
async def add_calendar_event(event: CalendarEvent):
    from jarvis.services.smart_home_services import calendar_service
    return calendar_service.add_event(event.title, event.start, event.end, event.recurring, event.actions)

@router.get("/calendar/upcoming")
async def get_upcoming_events(hours: int = Query(24)):
    from jarvis.services.smart_home_services import calendar_service
    return {"events": calendar_service.get_upcoming(hours)}

@router.get("/calendar/today")
async def get_today_events():
    from jarvis.services.smart_home_services import calendar_service
    return {"events": calendar_service.get_today()}

@router.get("/calendar/all")
async def get_all_events():
    from jarvis.services.smart_home_services import calendar_service
    return {"events": calendar_service.get_all()}

@router.delete("/calendar/events/{event_id}")
async def delete_calendar_event(event_id: int):
    from jarvis.services.smart_home_services import calendar_service
    calendar_service.delete_event(event_id)
    return {"status": "deleted"}


# ========== Feature 33: Guest Management ==========

class GuestRegister(BaseModel):
    name: str
    face_id: str = None
    access_level: str = "visitor"

@router.post("/guests/register")
async def register_guest(data: GuestRegister):
    from jarvis.services.smart_home_services import guest_service
    return guest_service.register_guest(data.name, data.face_id, data.access_level)

@router.post("/guests/{guest_id}/visit")
async def log_guest_visit(guest_id: str, location: str = Query("entrance")):
    from jarvis.services.smart_home_services import guest_service
    guest_service.log_visit(guest_id, location)
    return {"status": "logged"}

@router.get("/guests/{guest_id}/access/{zone}")
async def check_guest_access(guest_id: str, zone: str):
    from jarvis.services.smart_home_services import guest_service
    return guest_service.check_access(guest_id, zone)

@router.get("/guests/active")
async def get_active_visitors():
    from jarvis.services.smart_home_services import guest_service
    return {"visitors": guest_service.get_active_visitors()}

@router.get("/guests")
async def get_all_guests():
    from jarvis.services.smart_home_services import guest_service
    return {"guests": guest_service.get_all_guests()}

@router.get("/guests/visits")
async def get_visit_log(limit: int = Query(50)):
    from jarvis.services.smart_home_services import guest_service
    return {"visits": guest_service.get_visit_log(limit)}


# ========== Feature 34: Sleep Monitoring ==========

@router.post("/sleep/start")
async def start_sleep():
    from jarvis.services.smart_home_services import sleep_service
    return sleep_service.start_sleep()

@router.post("/sleep/end")
async def end_sleep():
    from jarvis.services.smart_home_services import sleep_service
    return sleep_service.end_sleep()

@router.post("/sleep/disturbance")
async def log_sleep_disturbance(reason: str = Query("motion")):
    from jarvis.services.smart_home_services import sleep_service
    sleep_service.log_disturbance(reason)
    return {"status": "logged"}

@router.get("/sleep/stats")
async def get_sleep_stats(days: int = Query(7)):
    from jarvis.services.smart_home_services import sleep_service
    return sleep_service.get_sleep_stats(days)

@router.get("/sleep/routine")
async def get_sleep_routine():
    from jarvis.services.smart_home_services import sleep_service
    return sleep_service.get_routine_config()


# ========== Feature 35: NLU ==========

class NLUInput(BaseModel):
    text: str

@router.post("/nlu/parse")
async def parse_intent(data: NLUInput):
    from jarvis.services.smart_home_services import nlu_service
    return nlu_service.parse_intent(data.text)

@router.get("/nlu/context")
async def get_nlu_context():
    from jarvis.services.smart_home_services import nlu_service
    return {"context": nlu_service.get_context()}


# ========== Feature 36: Conversation Context ==========

@router.post("/conversation/start")
async def start_conversation(user_id: str = Query("default")):
    from jarvis.services.smart_home_services import conversation_service
    session_id = conversation_service.start_session(user_id)
    return {"session_id": session_id}

class ConversationTurn(BaseModel):
    session_id: str
    role: str = "user"
    message: str

@router.post("/conversation/turn")
async def add_conversation_turn(data: ConversationTurn):
    from jarvis.services.smart_home_services import conversation_service, nlu_service
    intent = nlu_service.parse_intent(data.message)
    conversation_service.add_turn(data.session_id, data.role, data.message, intent)
    resolved = conversation_service.resolve_reference(data.session_id, data.message)
    return {"intent": intent, "resolved_text": resolved, "context": conversation_service.get_context(data.session_id)}

@router.get("/conversation/{session_id}/history")
async def get_conversation_history(session_id: str, limit: int = Query(10)):
    from jarvis.services.smart_home_services import conversation_service
    return {"history": conversation_service.get_history(session_id, limit)}


# ========== Feature 37: Habit Learning ==========

class HabitAction(BaseModel):
    action: str

@router.post("/habits/record")
async def record_habit(data: HabitAction):
    from jarvis.services.smart_home_services import habit_service
    habit_service.record_action(data.action)
    return {"status": "recorded"}

@router.post("/habits/analyze")
async def analyze_habits():
    from jarvis.services.smart_home_services import habit_service
    return {"habits": habit_service.analyze_habits()}

@router.get("/habits")
async def get_habits():
    from jarvis.services.smart_home_services import habit_service
    return {"habits": habit_service.get_habits(), "suggestion": habit_service.get_current_suggestion()}


# ========== Feature 38: Emergency Protocols ==========

class EmergencyTrigger(BaseModel):
    type: str  # fire, intrusion, medical, gas_leak, flood
    details: dict = {}

class EmergencyContact(BaseModel):
    name: str
    phone: str
    email: str = None

@router.post("/emergency/trigger")
async def trigger_emergency(data: EmergencyTrigger):
    from jarvis.services.smart_home_services import emergency_service
    return emergency_service.trigger_emergency(data.type, data.details)

@router.post("/emergency/resolve/{emergency_type}")
async def resolve_emergency(emergency_type: str):
    from jarvis.services.smart_home_services import emergency_service
    return emergency_service.resolve_emergency(emergency_type)

@router.post("/emergency/contacts")
async def add_emergency_contact(contact: EmergencyContact):
    from jarvis.services.smart_home_services import emergency_service
    emergency_service.add_emergency_contact(contact.name, contact.phone, contact.email)
    return {"status": "added"}

@router.get("/emergency/active")
async def get_active_emergencies():
    from jarvis.services.smart_home_services import emergency_service
    return {"emergencies": emergency_service.get_active_emergencies()}

@router.get("/emergency/log")
async def get_emergency_log(limit: int = Query(50)):
    from jarvis.services.smart_home_services import emergency_service
    return {"log": emergency_service.get_log(limit)}


# ========== Feature 39: Geofencing ==========

class GeofenceZone(BaseModel):
    name: str
    lat: float
    lon: float
    radius_m: float
    enter_actions: list = []
    exit_actions: list = []

class LocationUpdate(BaseModel):
    user_id: str
    lat: float
    lon: float

@router.post("/geofence/zones")
async def add_geofence_zone(zone: GeofenceZone):
    from jarvis.services.smart_home_services import geofence_service
    return geofence_service.add_zone(zone.name, zone.lat, zone.lon, zone.radius_m, zone.enter_actions, zone.exit_actions)

@router.post("/geofence/location")
async def update_geofence_location(data: LocationUpdate):
    from jarvis.services.smart_home_services import geofence_service
    events = geofence_service.update_location(data.user_id, data.lat, data.lon)
    return {"events": events}

@router.get("/geofence/zones")
async def get_geofence_zones():
    from jarvis.services.smart_home_services import geofence_service
    return {"zones": geofence_service.get_zones()}

@router.get("/geofence/locations")
async def get_user_locations():
    from jarvis.services.smart_home_services import geofence_service
    return {"locations": geofence_service.get_user_locations()}


# ========== Feature 40: Device Health ==========

class DeviceHealth(BaseModel):
    device_id: str
    cpu_temp: float = 0
    free_memory_pct: float = 100
    wifi_rssi: int = -50
    uptime_seconds: int = 0
    battery_pct: float = 100

@router.post("/health/device")
async def update_device_health(data: DeviceHealth):
    from jarvis.services.smart_home_services import device_health_monitor
    alerts = device_health_monitor.update_health(data.device_id, data.dict())
    return {"alerts": alerts}

@router.get("/health/devices")
async def get_all_device_health():
    from jarvis.services.smart_home_services import device_health_monitor
    return {"devices": device_health_monitor.get_health(), "summary": device_health_monitor.get_health_summary()}

@router.get("/health/devices/{device_id}")
async def get_device_health(device_id: str):
    from jarvis.services.smart_home_services import device_health_monitor
    return device_health_monitor.get_health(device_id)


# ========== Feature 41: Timelapse ==========

@router.post("/timelapse/start")
async def start_timelapse(interval: int = Query(60)):
    from jarvis.services.smart_home_services import timelapse_service
    return timelapse_service.start(interval)

@router.post("/timelapse/stop")
async def stop_timelapse():
    from jarvis.services.smart_home_services import timelapse_service
    return timelapse_service.stop()

@router.get("/timelapse/status")
async def get_timelapse_status():
    from jarvis.services.smart_home_services import timelapse_service
    return timelapse_service.get_status()


# ========== Feature 42: Notification Priority ==========

class Notification(BaseModel):
    title: str
    body: str
    severity: str = "low"  # critical, high, medium, low

class QuietHours(BaseModel):
    start: int
    end: int

@router.post("/notifications/evaluate")
async def evaluate_notification(data: Notification):
    from jarvis.services.smart_home_services import notification_priority_service
    return notification_priority_service.evaluate(data.dict())

@router.post("/notifications/quiet-hours")
async def set_quiet_hours(data: QuietHours):
    from jarvis.services.smart_home_services import notification_priority_service
    notification_priority_service.set_quiet_hours(data.start, data.end)
    return {"status": "set"}

@router.get("/notifications/stats")
async def get_notification_stats():
    from jarvis.services.smart_home_services import notification_priority_service
    return notification_priority_service.get_stats()


# ========== Feature 43: Backup/Restore ==========

class BackupRequest(BaseModel):
    label: str = "manual"
    state: dict = {}

@router.post("/backup/create")
async def create_backup(data: BackupRequest):
    from jarvis.services.smart_home_services import backup_service
    return backup_service.create_backup(data.state, data.label)

@router.post("/backup/restore/{backup_id}")
async def restore_backup(backup_id: str):
    from jarvis.services.smart_home_services import backup_service
    return backup_service.restore_backup(backup_id)

@router.get("/backup/list")
async def list_backups():
    from jarvis.services.smart_home_services import backup_service
    return {"backups": backup_service.list_backups()}

@router.delete("/backup/{backup_id}")
async def delete_backup(backup_id: str):
    from jarvis.services.smart_home_services import backup_service
    backup_service.delete_backup(backup_id)
    return {"status": "deleted"}


# ========== Feature 44: Task Scheduler ==========

class ScheduledTask(BaseModel):
    name: str
    action: str
    schedule: dict  # {"type": "interval|cron|once", "value": ...}
    params: dict = {}

@router.post("/scheduler/tasks")
async def add_scheduled_task(task: ScheduledTask):
    from jarvis.services.smart_home_services import task_scheduler
    return task_scheduler.add_task(task.name, task.action, task.schedule, task.params)

@router.get("/scheduler/tasks")
async def get_scheduled_tasks():
    from jarvis.services.smart_home_services import task_scheduler
    return {"tasks": task_scheduler.get_tasks()}

@router.get("/scheduler/due")
async def get_due_tasks():
    from jarvis.services.smart_home_services import task_scheduler
    return {"due_tasks": task_scheduler.get_due_tasks()}

@router.post("/scheduler/tasks/{task_id}/toggle")
async def toggle_task(task_id: int):
    from jarvis.services.smart_home_services import task_scheduler
    enabled = task_scheduler.toggle_task(task_id)
    return {"enabled": enabled}

@router.get("/scheduler/log")
async def get_scheduler_log(limit: int = Query(50)):
    from jarvis.services.smart_home_services import task_scheduler
    return {"log": task_scheduler.get_execution_log(limit)}


# ========== Feature 45: Smart Lighting ==========

class LightSetting(BaseModel):
    room: str
    brightness: int = 100
    color_temp: int = 4000
    color: str = None

@router.post("/lights/set")
async def set_room_light(data: LightSetting):
    from jarvis.services.smart_home_services import smart_lighting
    return smart_lighting.set_room_light(data.room, data.brightness, data.color_temp, data.color)

@router.get("/lights/circadian")
async def get_circadian_setting():
    from jarvis.services.smart_home_services import smart_lighting
    return smart_lighting.get_circadian_setting()

@router.get("/lights")
async def get_all_lights():
    from jarvis.services.smart_home_services import smart_lighting
    return {"rooms": smart_lighting.get_all_rooms()}

@router.post("/lights/all-off")
async def all_lights_off():
    from jarvis.services.smart_home_services import smart_lighting
    return smart_lighting.all_off()

@router.post("/lights/all-on")
async def all_lights_on(brightness: int = Query(100)):
    from jarvis.services.smart_home_services import smart_lighting
    return smart_lighting.all_on(brightness)
