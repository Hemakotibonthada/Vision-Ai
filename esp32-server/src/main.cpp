/*
 * =============================================================
 * Vision-AI + Jarvis  ESP32 Server — Main Controller  v3.0
 * =============================================================
 * Features: WiFi AP/STA, MQTT, WebSocket, REST API, OTA,
 *           Sensors, GPIO 8-Relay, BLE, Power Management,
 *           System Monitor, Door Sensor, Servo Lock, IR Blaster,
 *           Scheduled Tasks, Jarvis AI Heartbeat & Integration
 * =============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <EEPROM.h>
#include <ESPAsyncWebServer.h>
#include <AsyncTCP.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include <time.h>
#include <ESP32Servo.h>

#include "config.h"
#include "wifi_manager.h"
#include "mqtt_client.h"
#include "sensor_manager.h"
#include "gpio_manager.h"
#include "ota_manager.h"
#include "ble_manager.h"
#include "power_manager.h"
#include "system_monitor.h"

// ============================================
// Global Objects
// ============================================
WiFiManager wifiMgr;
MQTTClientManager mqttMgr;
SensorManager sensorMgr;
GPIOManager gpioMgr;
OTAManager otaMgr;
BLEManager bleMgr;
PowerManager powerMgr;
SystemMonitor sysMon;

AsyncWebServer server(HTTP_PORT);
AsyncWebSocket ws("/ws");

// ---- Door Sensor ----
volatile bool doorStateChanged = false;
volatile bool doorOpen = false;
unsigned long lastDoorEvent = 0;

// ---- Servo Lock ----
Servo lockServo;
bool lockEngaged = true;

// ---- Schedule System ----
struct ScheduleEntry {
    uint8_t relay;       // 1-8, or 0xFF = all
    uint8_t hour;
    uint8_t minute;
    uint8_t daysMask;    // bit0=Sun .. bit6=Sat
    uint8_t action;      // 0=off, 1=on, 2=toggle
    uint8_t enabled;
    uint8_t repeat;      // 0=once, 1=daily, 2=weekdays, 3=weekends
    uint8_t sceneIdx;    // if 0xFF ➜ normal relay action, else load scene
};
ScheduleEntry schedules[MAX_SCHEDULES];
int scheduleCount = 0;

// ---- Boot counter ----
uint32_t bootCount = 0;

// ============================================
// Task Handles (FreeRTOS)
// ============================================
TaskHandle_t sensorTaskHandle = NULL;
TaskHandle_t mqttTaskHandle = NULL;
TaskHandle_t monitorTaskHandle = NULL;
TaskHandle_t scheduleTaskHandle = NULL;

// ============================================
// Rate Limiting
// ============================================
struct RateLimit {
    unsigned long windowStart;
    int requestCount;
} rateLimit = {0, 0};

bool checkRateLimit() {
    unsigned long now = millis();
    if (now - rateLimit.windowStart > API_RATE_WINDOW) {
        rateLimit.windowStart = now;
        rateLimit.requestCount = 0;
    }
    rateLimit.requestCount++;
    return rateLimit.requestCount <= API_RATE_LIMIT;
}

// ============================================
// Authentication Middleware
// ============================================
bool authenticate(AsyncWebServerRequest* request) {
    if (!AUTH_ENABLED) return true;
    
    // Check API key header
    if (request->hasHeader("X-API-Key")) {
        return request->getHeader("X-API-Key")->value() == API_KEY;
    }
    
    // Check basic auth
    if (request->authenticate(AUTH_USERNAME, AUTH_PASSWORD)) {
        return true;
    }
    
    request->send(401, "application/json", "{\"error\":\"Unauthorized\"}");
    return false;
}

// ============================================
// Door Sensor ISR (magnetic reed switch)
// ============================================
void IRAM_ATTR doorISR() {
    unsigned long now = millis();
    if (now - lastDoorEvent > DOOR_DEBOUNCE_MS) {
        doorOpen = (digitalRead(PIN_DOOR_SENSOR) == HIGH);
        doorStateChanged = true;
        lastDoorEvent = now;
    }
}

void handleDoorEvent() {
    if (!doorStateChanged) return;
    doorStateChanged = false;

    String state = doorOpen ? "open" : "closed";
    Serial.printf("[Door] State: %s\n", state.c_str());

    // Publish to Jarvis via MQTT
    StaticJsonDocument<256> doc;
    doc["event"]  = "door";
    doc["state"]  = state;
    doc["timestamp"] = millis();
    doc["device"] = MQTT_CLIENT_ID;
    char buf[256];
    serializeJson(doc, buf);
    mqttMgr.publish(TOPIC_JARVIS_DOOR, buf);

    // Also broadcast on WebSocket
    ws.textAll("{\"type\":\"door\",\"state\":\"" + state + "\"}");

    if (doorOpen) {
        gpioMgr.buzzPattern("relay");          // short beep
        sysMon.log("INFO", "Door opened");
    } else {
        sysMon.log("INFO", "Door closed");
    }
}

// ============================================
// Servo Lock (SG90 on GPIO26)
// ============================================
void initServoLock() {
    lockServo.attach(PIN_SERVO_LOCK, 500, 2400);
    // Restore lock state from EEPROM
    uint8_t saved = EEPROM.read(EEPROM_LOCK_STATE_ADDR);
    lockEngaged = (saved != 0);
    lockServo.write(lockEngaged ? SERVO_LOCK_ANGLE : SERVO_UNLOCK_ANGLE);
    Serial.printf("[Lock] Initialized — %s\n", lockEngaged ? "LOCKED" : "UNLOCKED");
}

void setLock(bool lock) {
    lockEngaged = lock;
    lockServo.write(lock ? SERVO_LOCK_ANGLE : SERVO_UNLOCK_ANGLE);
    EEPROM.write(EEPROM_LOCK_STATE_ADDR, lock ? 1 : 0);
    EEPROM.commit();

    StaticJsonDocument<128> doc;
    doc["event"] = "lock";
    doc["state"] = lock ? "locked" : "unlocked";
    doc["timestamp"] = millis();
    char buf[128];
    serializeJson(doc, buf);
    mqttMgr.publish(TOPIC_JARVIS_LOCK, buf);

    ws.textAll("{\"type\":\"lock\",\"state\":\"" + String(lock ? "locked" : "unlocked") + "\"}");
    gpioMgr.buzzPattern(lock ? "relay" : "success");
    Serial.printf("[Lock] %s\n", lock ? "LOCKED" : "UNLOCKED");
}

// ============================================
// Schedule System
// ============================================
void loadSchedules() {
    for (int i = 0; i < MAX_SCHEDULES; i++) {
        int addr = EEPROM_SCHEDULE_ADDR + i * 8;
        schedules[i].relay    = EEPROM.read(addr + 0);
        schedules[i].hour     = EEPROM.read(addr + 1);
        schedules[i].minute   = EEPROM.read(addr + 2);
        schedules[i].daysMask = EEPROM.read(addr + 3);
        schedules[i].action   = EEPROM.read(addr + 4);
        schedules[i].enabled  = EEPROM.read(addr + 5);
        schedules[i].repeat   = EEPROM.read(addr + 6);
        schedules[i].sceneIdx = EEPROM.read(addr + 7);
        if (schedules[i].enabled == 1) scheduleCount++;
    }
    Serial.printf("[Sched] Loaded %d active schedules\n", scheduleCount);
}

void saveSchedule(int idx) {
    if (idx < 0 || idx >= MAX_SCHEDULES) return;
    int addr = EEPROM_SCHEDULE_ADDR + idx * 8;
    EEPROM.write(addr + 0, schedules[idx].relay);
    EEPROM.write(addr + 1, schedules[idx].hour);
    EEPROM.write(addr + 2, schedules[idx].minute);
    EEPROM.write(addr + 3, schedules[idx].daysMask);
    EEPROM.write(addr + 4, schedules[idx].action);
    EEPROM.write(addr + 5, schedules[idx].enabled);
    EEPROM.write(addr + 6, schedules[idx].repeat);
    EEPROM.write(addr + 7, schedules[idx].sceneIdx);
    EEPROM.commit();
}

String getSchedulesJSON() {
    String json = "[";
    bool first = true;
    for (int i = 0; i < MAX_SCHEDULES; i++) {
        if (schedules[i].enabled != 1) continue;
        if (!first) json += ",";
        first = false;
        json += "{\"id\":" + String(i) +
                ",\"relay\":" + String(schedules[i].relay) +
                ",\"hour\":" + String(schedules[i].hour) +
                ",\"minute\":" + String(schedules[i].minute) +
                ",\"days\":" + String(schedules[i].daysMask) +
                ",\"action\":" + String(schedules[i].action) +
                ",\"repeat\":" + String(schedules[i].repeat) +
                ",\"scene\":" + String(schedules[i].sceneIdx) + "}";
    }
    json += "]";
    return json;
}

void checkSchedules() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return;

    int wday = timeinfo.tm_wday; // 0=Sun
    int hour = timeinfo.tm_hour;
    int minute = timeinfo.tm_min;

    for (int i = 0; i < MAX_SCHEDULES; i++) {
        if (schedules[i].enabled != 1) continue;
        if (schedules[i].hour != hour || schedules[i].minute != minute) continue;
        if (!(schedules[i].daysMask & (1 << wday))) continue;

        // Execute
        if (schedules[i].sceneIdx != 0xFF) {
            gpioMgr.loadScene(schedules[i].sceneIdx);
            sysMon.log("INFO", "Schedule: loaded scene " + String(schedules[i].sceneIdx));
        } else {
            uint8_t r = schedules[i].relay;
            uint8_t a = schedules[i].action;
            if (r == 0xFF) {
                gpioMgr.setAllRelays(a == 1);
            } else if (a == 2) {
                gpioMgr.toggleRelay(r);
            } else {
                gpioMgr.setRelay(r, a == 1);
            }
            sysMon.log("INFO", "Schedule: relay " + String(r) + " → " + String(a));
        }

        // If one-shot, disable
        if (schedules[i].repeat == 0) {
            schedules[i].enabled = 0;
            saveSchedule(i);
        }

        // Publish event
        StaticJsonDocument<128> doc;
        doc["event"] = "schedule_fired";
        doc["id"] = i;
        char buf[128];
        serializeJson(doc, buf);
        mqttMgr.publish(TOPIC_JARVIS_SCHED, buf);
    }
}

// Schedule FreeRTOS task — checks once per minute
void scheduleTask(void* parameter) {
    Serial.println("[Task] Schedule task started on core " + String(xPortGetCoreID()));
    int lastMinute = -1;
    for (;;) {
        struct tm ti;
        if (getLocalTime(&ti) && ti.tm_min != lastMinute) {
            lastMinute = ti.tm_min;
            checkSchedules();
        }
        vTaskDelay(pdMS_TO_TICKS(10000)); // check every 10 s
    }
}

// ============================================
// Heartbeat — periodic ping to Jarvis server
// ============================================
void sendHeartbeat() {
    StaticJsonDocument<512> doc;
    doc["device"]   = MQTT_CLIENT_ID;
    doc["firmware"]  = FIRMWARE_VERSION;
    doc["uptime"]    = millis() / 1000;
    doc["free_heap"] = ESP.getFreeHeap();
    doc["rssi"]      = WiFi.RSSI();
    doc["ip"]        = wifiMgr.getLocalIP();
    doc["door"]      = doorOpen ? "open" : "closed";
    doc["lock"]      = lockEngaged ? "locked" : "unlocked";
    doc["boot_count"]= bootCount;
    doc["relays"]    = gpioMgr.getRelayBitmask();
    doc["temperature"] = sensorMgr.getTemperature();
    doc["humidity"]    = sensorMgr.getHumidity();
    doc["motion"]      = sensorMgr.getMotion();
    doc["voltage"]     = sensorMgr.getVoltage();
    doc["current"]     = sensorMgr.getCurrent();
    doc["light"]       = sensorMgr.getLight();

    char buf[512];
    serializeJson(doc, buf);
    mqttMgr.publish(TOPIC_JARVIS_HEARTBEAT, buf);
}

// ============================================
// WebSocket Event Handler (Feature 9)
// ============================================
void onWsEvent(AsyncWebSocket* server, AsyncWebSocketClient* client,
               AwsEventType type, void* arg, uint8_t* data, size_t len) {
    switch (type) {
        case WS_EVT_CONNECT:
            Serial.printf("[WS] Client %u connected from %s\n", 
                         client->id(), client->remoteIP().toString().c_str());
            // Send initial state
            client->text("{\"type\":\"connected\",\"id\":" + String(client->id()) + "}");
            break;
            
        case WS_EVT_DISCONNECT:
            Serial.printf("[WS] Client %u disconnected\n", client->id());
            break;
            
        case WS_EVT_DATA: {
            AwsFrameInfo* info = (AwsFrameInfo*)arg;
            if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
                String msg = String((char*)data).substring(0, len);
                handleWebSocketMessage(client, msg);
            }
            break;
        }
        
        case WS_EVT_PONG:
            break;
            
        case WS_EVT_ERROR:
            Serial.printf("[WS] Client %u error\n", client->id());
            break;
    }
}

void handleWebSocketMessage(AsyncWebSocketClient* client, const String& message) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, message);
    if (error) {
        client->text("{\"error\":\"Invalid JSON\"}");
        return;
    }
    
    const char* action = doc["action"];
    if (!action) return;
    
    if (strcmp(action, "get_sensors") == 0) {
        client->text("{\"type\":\"sensors\",\"data\":" + sensorMgr.getDataJSON() + "}");
    }
    else if (strcmp(action, "get_status") == 0) {
        client->text("{\"type\":\"status\",\"data\":" + sysMon.getStatusJSON() + "}");
    }
    else if (strcmp(action, "set_relay") == 0) {
        int relay = doc["relay"] | 1;
        bool state = doc["state"] | false;
        gpioMgr.setRelay(relay, state);
        gpioMgr.buzzPattern("relay");
        client->text("{\"type\":\"relay\",\"relay\":" + String(relay) + 
                     ",\"room\":\"" + String(gpioMgr.getRelayRoom(relay)) + 
                     "\",\"state\":" + String(state ? "true" : "false") + "}");
    }
    else if (strcmp(action, "set_relay_by_room") == 0) {
        const char* room = doc["room"] | "";
        bool state = doc["state"] | false;
        gpioMgr.setRelayByRoom(room, state);
        gpioMgr.buzzPattern("relay");
        client->text("{\"type\":\"relay_room\",\"room\":\"" + String(room) + 
                     "\",\"state\":" + String(state ? "true" : "false") + "}");
    }
    else if (strcmp(action, "set_all_relays") == 0) {
        bool state = doc["state"] | false;
        gpioMgr.setAllRelays(state);
        client->text("{\"type\":\"all_relays\",\"state\":" + String(state ? "true" : "false") + "}");
    }
    else if (strcmp(action, "get_relays") == 0) {
        client->text("{\"type\":\"relays\",\"data\":" + gpioMgr.getStatusJSON() + "}");
    }
    else if (strcmp(action, "load_scene") == 0) {
        int scene = doc["scene"] | 0;
        gpioMgr.loadScene(scene);
        client->text("{\"type\":\"scene_loaded\",\"scene\":" + String(scene) + "}");
    }
    else if (strcmp(action, "save_scene") == 0) {
        int scene = doc["scene"] | 0;
        bool states[RELAY_COUNT];
        for (int i = 0; i < RELAY_COUNT; i++) {
            states[i] = gpioMgr.getRelayState(i + 1);
        }
        gpioMgr.saveScene(scene, states);
        client->text("{\"type\":\"scene_saved\",\"scene\":" + String(scene) + "}");
    }
    else if (strcmp(action, "buzz") == 0) {
        const char* pattern = doc["pattern"] | "alert";
        gpioMgr.buzzPattern(pattern);
        client->text("{\"type\":\"buzzer\",\"pattern\":\"" + String(pattern) + "\"}");
    }
    else if (strcmp(action, "ping") == 0) {
        client->text("{\"type\":\"pong\",\"timestamp\":" + String(millis()) + "}");
    }
    else if (strcmp(action, "set_lock") == 0) {
        bool state = doc["state"] | false;
        setLock(state);
        client->text("{\"type\":\"lock\",\"state\":\"" + String(state ? "locked" : "unlocked") + "\"}");
    }
    else if (strcmp(action, "get_door") == 0) {
        client->text("{\"type\":\"door\",\"state\":\"" + String(doorOpen ? "open" : "closed") + "\"}");
    }
    else if (strcmp(action, "get_schedules") == 0) {
        client->text("{\"type\":\"schedules\",\"data\":" + getSchedulesJSON() + "}");
    }
}

void broadcastSensorData() {
    if (ws.count() > 0) {
        String data = "{\"type\":\"sensor_update\",\"data\":" + sensorMgr.getDataJSON() + "}";
        ws.textAll(data);
    }
}

// ============================================
// MQTT Message Handler
// ============================================
void onMQTTMessage(const char* topic, const char* payload) {
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, payload);
    if (error) return;
    
    String topicStr = String(topic);
    
    if (topicStr == TOPIC_CAMERA_STATUS) {
        // Forward camera status to WebSocket clients
        ws.textAll("{\"type\":\"camera_status\",\"data\":" + String(payload) + "}");
    }
    else if (topicStr == TOPIC_AI_RESULT) {
        // Forward AI results to WebSocket clients
        ws.textAll("{\"type\":\"ai_result\",\"data\":" + String(payload) + "}");
        
        // Check for alerts
        if (doc.containsKey("alert") && doc["alert"].as<bool>()) {
            gpioMgr.buzzPattern("alert");
            gpioMgr.blinkStatusLED(5, 100);
        }
    }
    else if (topicStr == TOPIC_CONFIG) {
        sysMon.log("INFO", "Config update received");
    }
    // ---- Jarvis Commands ----
    else if (topicStr == TOPIC_JARVIS_CMD) {
        const char* cmd = doc["command"];
        if (!cmd) return;

        if (strcmp(cmd, "relay") == 0) {
            int relay = doc["relay"] | 1;
            bool state = doc["state"] | false;
            gpioMgr.setRelay(relay, state);
            gpioMgr.buzzPattern("relay");
            sysMon.log("INFO", "Jarvis: relay " + String(relay) + " → " + String(state));
        }
        else if (strcmp(cmd, "relay_room") == 0) {
            const char* room = doc["room"] | "";
            bool state = doc["state"] | false;
            gpioMgr.setRelayByRoom(room, state);
            gpioMgr.buzzPattern("relay");
        }
        else if (strcmp(cmd, "all_relays") == 0) {
            bool state = doc["state"] | false;
            gpioMgr.setAllRelays(state);
        }
        else if (strcmp(cmd, "lock") == 0) {
            bool state = doc["state"] | true;
            setLock(state);
        }
        else if (strcmp(cmd, "unlock") == 0) {
            setLock(false);
        }
        else if (strcmp(cmd, "buzz") == 0) {
            const char* pattern = doc["pattern"] | "alert";
            gpioMgr.buzzPattern(pattern);
        }
        else if (strcmp(cmd, "scene") == 0) {
            int scene = doc["scene"] | 0;
            gpioMgr.loadScene(scene);
        }
        else if (strcmp(cmd, "status") == 0) {
            sendHeartbeat(); // reply with full status
        }
        else if (strcmp(cmd, "restart") == 0) {
            mqttMgr.publish(TOPIC_JARVIS_EVENT, "{\"event\":\"restarting\"}");
            delay(500);
            ESP.restart();
        }

        // Publish relay state back
        StaticJsonDocument<256> reply;
        reply["device"] = MQTT_CLIENT_ID;
        reply["event"]  = "command_executed";
        reply["command"] = cmd;
        char rbuf[256];
        serializeJson(reply, rbuf);
        mqttMgr.publish(TOPIC_JARVIS_EVENT, rbuf);
    }
}

// ============================================
// REST API Setup (Feature 10)
// ============================================
void setupAPI() {
    // CORS headers
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Origin", CORS_ORIGIN);
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
    DefaultHeaders::Instance().addHeader("Access-Control-Allow-Headers", "Content-Type, X-API-Key, Authorization");
    
    // ---- System Endpoints ----
    server.on((String(API_PREFIX) + "/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!checkRateLimit()) { request->send(429, "application/json", "{\"error\":\"Rate limit exceeded\"}"); return; }
        request->send(200, "application/json", sysMon.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/health").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        String health = "{\"status\":\"healthy\",\"uptime\":" + String(sysMon.getUptime()) + 
                        ",\"free_heap\":" + String(ESP.getFreeHeap()) + "}";
        request->send(200, "application/json", health);
    });

    server.on((String(API_PREFIX) + "/memory").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        request->send(200, "application/json", sysMon.getMemoryInfo());
    });

    server.on((String(API_PREFIX) + "/logs").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int count = 20;
        if (request->hasParam("count")) count = request->getParam("count")->value().toInt();
        request->send(200, "application/json", sysMon.getLogsJSON(count));
    });

    server.on((String(API_PREFIX) + "/firmware").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", otaMgr.getFirmwareInfo());
    });

    server.on((String(API_PREFIX) + "/restart").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        request->send(200, "application/json", "{\"status\":\"restarting\"}");
        delay(1000);
        ESP.restart();
    });

    // ---- WiFi Endpoints ----
    server.on((String(API_PREFIX) + "/wifi/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", wifiMgr.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/wifi/scan").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        request->send(200, "application/json", wifiMgr.scanNetworks());
    });

    // ---- Sensor Endpoints ----
    server.on((String(API_PREFIX) + "/sensors").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!checkRateLimit()) { request->send(429); return; }
        request->send(200, "application/json", sensorMgr.getDataJSON());
    });

    server.on((String(API_PREFIX) + "/sensors/temperature").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"temperature\":" + String(sensorMgr.getTemperature()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/humidity").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"humidity\":" + String(sensorMgr.getHumidity()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/motion").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"motion\":" + String(sensorMgr.getMotion() ? "true" : "false") + 
                      ",\"count\":" + String(sensorMgr.getMotionCount()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/distance").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"distance\":" + String(sensorMgr.getDistance()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/light").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", "{\"light\":" + String(sensorMgr.getLight()) + 
                      ",\"dark\":" + String(sensorMgr.isDark() ? "true" : "false") + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/reset").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        sensorMgr.resetStats();
        request->send(200, "application/json", "{\"status\":\"stats_reset\"}");
    });

    // ---- GPIO Endpoints (8-Relay + Room Control) ----
    server.on((String(API_PREFIX) + "/gpio/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", gpioMgr.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/gpio/relay").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int relay = 1, state = 0;
        if (request->hasParam("relay")) relay = request->getParam("relay")->value().toInt();
        if (request->hasParam("state")) state = request->getParam("state")->value().toInt();
        gpioMgr.setRelay(relay, state == 1);
        gpioMgr.buzzPattern("relay");
        request->send(200, "application/json", 
            "{\"relay\":" + String(relay) + ",\"room\":\"" + String(gpioMgr.getRelayRoom(relay)) + 
            "\",\"state\":" + String(state) + "}");
    });

    server.on((String(API_PREFIX) + "/gpio/relay/room").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        String room = "";
        int state = 0;
        if (request->hasParam("room")) room = request->getParam("room")->value();
        if (request->hasParam("state")) state = request->getParam("state")->value().toInt();
        gpioMgr.setRelayByRoom(room.c_str(), state == 1);
        gpioMgr.buzzPattern("relay");
        request->send(200, "application/json", 
            "{\"room\":\"" + room + "\",\"state\":" + String(state) + "}");
    });

    server.on((String(API_PREFIX) + "/gpio/relay/all").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int state = 0;
        if (request->hasParam("state")) state = request->getParam("state")->value().toInt();
        gpioMgr.setAllRelays(state == 1);
        request->send(200, "application/json", "{\"all_relays\":" + String(state) + "}");
    });

    server.on((String(API_PREFIX) + "/gpio/scene/save").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int sceneIdx = 0;
        if (request->hasParam("scene")) sceneIdx = request->getParam("scene")->value().toInt();
        bool states[RELAY_COUNT];
        for (int i = 0; i < RELAY_COUNT; i++) states[i] = gpioMgr.getRelayState(i + 1);
        gpioMgr.saveScene(sceneIdx, states);
        request->send(200, "application/json", "{\"scene_saved\":" + String(sceneIdx) + "}");
    });

    server.on((String(API_PREFIX) + "/gpio/scene/load").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int sceneIdx = 0;
        if (request->hasParam("scene")) sceneIdx = request->getParam("scene")->value().toInt();
        gpioMgr.loadScene(sceneIdx);
        request->send(200, "application/json", "{\"scene_loaded\":" + String(sceneIdx) + "}");
    });

    server.on((String(API_PREFIX) + "/gpio/buzzer").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        String pattern = "alert";
        if (request->hasParam("pattern")) pattern = request->getParam("pattern")->value();
        gpioMgr.buzzPattern(pattern.c_str());
        request->send(200, "application/json", "{\"pattern\":\"" + pattern + "\"}");
    });

    // ---- Sensor Endpoints: Voltage & Current ----
    server.on((String(API_PREFIX) + "/sensors/voltage").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", 
            "{\"voltage\":" + String(sensorMgr.getVoltage()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/current").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", 
            "{\"current\":" + String(sensorMgr.getCurrent()) + "}");
    });

    server.on((String(API_PREFIX) + "/sensors/power").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", 
            "{\"voltage\":" + String(sensorMgr.getVoltage()) + 
            ",\"current\":" + String(sensorMgr.getCurrent()) + 
            ",\"power\":" + String(sensorMgr.getPower()) + "}");
    });

    // ---- MQTT Endpoints ----
    server.on((String(API_PREFIX) + "/mqtt/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", mqttMgr.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/mqtt/publish").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        String topic = "", message = "";
        if (request->hasParam("topic")) topic = request->getParam("topic")->value();
        if (request->hasParam("message")) message = request->getParam("message")->value();
        bool result = mqttMgr.publish(topic.c_str(), message.c_str());
        request->send(200, "application/json", "{\"published\":" + String(result ? "true" : "false") + "}");
    });

    // ---- BLE Endpoints ----
    server.on((String(API_PREFIX) + "/ble/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", bleMgr.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/ble/scan").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        request->send(200, "application/json", bleMgr.scanDevices());
    });

    // ---- Power Endpoints ----
    server.on((String(API_PREFIX) + "/power/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", powerMgr.getStatusJSON());
    });

    server.on((String(API_PREFIX) + "/power/eco").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        bool enable = true;
        if (request->hasParam("enable")) enable = request->getParam("enable")->value() == "1";
        powerMgr.setEcoMode(enable);
        request->send(200, "application/json", "{\"eco_mode\":" + String(enable ? "true" : "false") + "}");
    });

    // ---- Camera Control (via MQTT) ----
    server.on((String(API_PREFIX) + "/camera/capture").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        mqttMgr.publish(TOPIC_CAMERA_CMD, "{\"command\":\"capture\"}");
        request->send(200, "application/json", "{\"status\":\"capture_requested\"}");
    });

    server.on((String(API_PREFIX) + "/camera/stream/start").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        mqttMgr.publish(TOPIC_CAMERA_CMD, "{\"command\":\"stream_start\"}");
        request->send(200, "application/json", "{\"status\":\"stream_start_requested\"}");
    });

    server.on((String(API_PREFIX) + "/camera/stream/stop").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        mqttMgr.publish(TOPIC_CAMERA_CMD, "{\"command\":\"stream_stop\"}");
        request->send(200, "application/json", "{\"status\":\"stream_stop_requested\"}");
    });

    server.on((String(API_PREFIX) + "/camera/settings").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        StaticJsonDocument<512> doc;
        doc["command"] = "settings";
        if (request->hasParam("resolution")) doc["resolution"] = request->getParam("resolution")->value();
        if (request->hasParam("quality")) doc["quality"] = request->getParam("quality")->value().toInt();
        if (request->hasParam("brightness")) doc["brightness"] = request->getParam("brightness")->value().toInt();
        if (request->hasParam("contrast")) doc["contrast"] = request->getParam("contrast")->value().toInt();
        
        char buffer[512];
        serializeJson(doc, buffer);
        mqttMgr.publish(TOPIC_CAMERA_CMD, buffer);
        request->send(200, "application/json", "{\"status\":\"settings_sent\"}");
    });

    // ---- Door Sensor Endpoints ----
    server.on((String(API_PREFIX) + "/door/status").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        String json = "{\"door\":\"" + String(doorOpen ? "open" : "closed") + 
                      "\",\"lock\":\"" + String(lockEngaged ? "locked" : "unlocked") + "\"}";
        request->send(200, "application/json", json);
    });

    // ---- Lock Endpoints ----
    server.on((String(API_PREFIX) + "/lock/set").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        bool state = true;
        if (request->hasParam("state")) state = request->getParam("state")->value() == "1";
        setLock(state);
        request->send(200, "application/json", "{\"lock\":\"" + String(state ? "locked" : "unlocked") + "\"}");
    });

    server.on((String(API_PREFIX) + "/lock/toggle").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        setLock(!lockEngaged);
        request->send(200, "application/json", "{\"lock\":\"" + String(lockEngaged ? "locked" : "unlocked") + "\"}");
    });

    // ---- Schedule Endpoints ----
    server.on((String(API_PREFIX) + "/schedules").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "application/json", getSchedulesJSON());
    });

    server.on((String(API_PREFIX) + "/schedules/add").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        // Find an empty slot
        int slot = -1;
        for (int i = 0; i < MAX_SCHEDULES; i++) {
            if (schedules[i].enabled != 1) { slot = i; break; }
        }
        if (slot < 0) {
            request->send(400, "application/json", "{\"error\":\"No free schedule slots\"}");
            return;
        }
        schedules[slot].relay    = request->hasParam("relay")  ? request->getParam("relay")->value().toInt()  : 0xFF;
        schedules[slot].hour     = request->hasParam("hour")   ? request->getParam("hour")->value().toInt()   : 0;
        schedules[slot].minute   = request->hasParam("minute") ? request->getParam("minute")->value().toInt() : 0;
        schedules[slot].daysMask = request->hasParam("days")   ? request->getParam("days")->value().toInt()   : 0x7F;
        schedules[slot].action   = request->hasParam("action") ? request->getParam("action")->value().toInt() : 1;
        schedules[slot].enabled  = 1;
        schedules[slot].repeat   = request->hasParam("repeat") ? request->getParam("repeat")->value().toInt() : 1;
        schedules[slot].sceneIdx = request->hasParam("scene")  ? request->getParam("scene")->value().toInt()  : 0xFF;
        saveSchedule(slot);
        scheduleCount++;
        request->send(200, "application/json", "{\"id\":" + String(slot) + ",\"status\":\"added\"}");
    });

    server.on((String(API_PREFIX) + "/schedules/delete").c_str(), HTTP_POST, [](AsyncWebServerRequest* request) {
        if (!authenticate(request)) return;
        int id = 0;
        if (request->hasParam("id")) id = request->getParam("id")->value().toInt();
        if (id >= 0 && id < MAX_SCHEDULES) {
            schedules[id].enabled = 0;
            saveSchedule(id);
            scheduleCount--;
            request->send(200, "application/json", "{\"id\":" + String(id) + ",\"status\":\"deleted\"}");
        } else {
            request->send(400, "application/json", "{\"error\":\"Invalid schedule id\"}");
        }
    });

    // ---- Jarvis Heartbeat Endpoint (AI server can pull) ----
    server.on((String(API_PREFIX) + "/jarvis/heartbeat").c_str(), HTTP_GET, [](AsyncWebServerRequest* request) {
        StaticJsonDocument<512> doc;
        doc["device"]     = MQTT_CLIENT_ID;
        doc["firmware"]   = FIRMWARE_VERSION;
        doc["uptime"]     = millis() / 1000;
        doc["free_heap"]  = ESP.getFreeHeap();
        doc["rssi"]       = WiFi.RSSI();
        doc["ip"]         = wifiMgr.getLocalIP();
        doc["door"]       = doorOpen ? "open" : "closed";
        doc["lock"]       = lockEngaged ? "locked" : "unlocked";
        doc["boot_count"] = bootCount;
        doc["relays"]     = gpioMgr.getRelayBitmask();
        doc["temperature"]= sensorMgr.getTemperature();
        doc["humidity"]   = sensorMgr.getHumidity();
        doc["motion"]     = sensorMgr.getMotion();
        doc["voltage"]    = sensorMgr.getVoltage();
        doc["current"]    = sensorMgr.getCurrent();
        doc["light"]      = sensorMgr.getLight();
        doc["schedules"]  = scheduleCount;

        char buf[512];
        serializeJson(doc, buf);
        request->send(200, "application/json", buf);
    });

    // ---- 404 Handler ----
    server.onNotFound([](AsyncWebServerRequest* request) {
        if (request->method() == HTTP_OPTIONS) {
            request->send(200);
        } else {
            request->send(404, "application/json", "{\"error\":\"Not Found\",\"path\":\"" + request->url() + "\"}");
        }
    });
}

// ============================================
// FreeRTOS Tasks (Feature 28-29)
// ============================================

// Sensor reading task - runs on Core 0
void sensorTask(void* parameter) {
    Serial.println("[Task] Sensor task started on core " + String(xPortGetCoreID()));
    for (;;) {
        sensorMgr.readAll();
        
        // Check for motion alerts
        if (sensorMgr.getMotion()) {
            mqttMgr.publishAlert("motion", "Motion detected!", 2);
            gpioMgr.showStatus("warning");
            gpioMgr.buzzPattern("motion");
        }
        
        // Check temperature alerts (buzzer warning)
        if (sensorMgr.isTemperatureAlert()) {
            mqttMgr.publishAlert("temperature", "Temperature alert!", 3);
            gpioMgr.showStatus("error");
            gpioMgr.buzzPattern("temperature");
        }

        // Check humidity alerts
        if (sensorMgr.isHumidityAlert()) {
            mqttMgr.publishAlert("humidity", "High humidity!", 2);
        }

        // Check voltage alerts (buzzer warning)
        if (sensorMgr.isVoltageAlert()) {
            mqttMgr.publishAlert("voltage", "Voltage out of range!", 3);
            gpioMgr.buzzPattern("voltage");
        }

        // Check current overload (buzzer warning)
        if (sensorMgr.isCurrentAlert()) {
            mqttMgr.publishAlert("current", "Current overload!", 3);
            gpioMgr.buzzPattern("alert");
        }
        
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

// MQTT publishing task - runs on Core 1
void mqttTask(void* parameter) {
    Serial.println("[Task] MQTT task started on core " + String(xPortGetCoreID()));
    for (;;) {
        if (mqttMgr.connected()) {
            // Publish sensor data periodically
            mqttMgr.publishSensorData(
                sensorMgr.getTemperature(),
                sensorMgr.getHumidity(),
                sensorMgr.getMotion(),
                sensorMgr.getDistance(),
                sensorMgr.getLight()
            );
            
            // Publish system status
            mqttMgr.publishStatus();
            
            // Broadcast to WebSocket clients
            broadcastSensorData();
        }
        
        vTaskDelay(pdMS_TO_TICKS(SENSOR_READ_INTERVAL));
    }
}

// System monitor task
void monitorTask(void* parameter) {
    Serial.println("[Task] Monitor task started on core " + String(xPortGetCoreID()));
    for (;;) {
        sysMon.checkHealth();
        
        // Send BLE notifications
        if (bleMgr.isConnected()) {
            bleMgr.sendSensorData(
                sensorMgr.getTemperature(),
                sensorMgr.getHumidity(),
                sensorMgr.getMotion()
            );
        }
        
        vTaskDelay(pdMS_TO_TICKS(HEALTH_CHECK_INTERVAL));
    }
}

// ============================================
// NTP Time Sync (Feature 13)
// ============================================
void setupNTP() {
    configTime(NTP_GMT_OFFSET, NTP_DAYLIGHT_OFFSET, NTP_SERVER_1, NTP_SERVER_2);
    Serial.println("[NTP] Time sync configured");
    
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
        Serial.printf("[NTP] Time: %04d-%02d-%02d %02d:%02d:%02d\n",
            timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
            timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    }
}

// ============================================
// SPIFFS Setup (Feature 15)
// ============================================
void setupSPIFFS() {
    if (SPIFFS.begin(true)) {
        Serial.printf("[SPIFFS] Mounted. Total: %d, Used: %d\n", 
                      SPIFFS.totalBytes(), SPIFFS.usedBytes());
    } else {
        Serial.println("[SPIFFS] Mount failed!");
    }
}

// ============================================
// Setup
// ============================================
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(1000);
    
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════╗");
    Serial.println("║     Vision-AI ESP32 Server v" FIRMWARE_VERSION "     ║");
    Serial.println("╠══════════════════════════════════════╣");
    Serial.println("║  Intelligent Vision System           ║");
    Serial.println("╚══════════════════════════════════════╝");
    Serial.println();

    // Initialize system monitor
    sysMon.begin();
    sysMon.log("INFO", "Starting Vision-AI Server...");

    // Initialize SPIFFS
    setupSPIFFS();

    // Initialize EEPROM (must be before GPIO so relay states can be restored)
    EEPROM.begin(EEPROM_SIZE);
    sysMon.log("INFO", "EEPROM initialized (" + String(EEPROM_SIZE) + " bytes)");
    
    // Initialize GPIO (restores relay states from EEPROM)
    gpioMgr.begin();
    gpioMgr.showStatus("connecting");
    
    // Initialize sensors
    sensorMgr.begin();

    // Initialize door sensor with interrupt
    pinMode(PIN_DOOR_SENSOR, INPUT_PULLUP);
    doorOpen = (digitalRead(PIN_DOOR_SENSOR) == LOW);
    attachInterrupt(digitalPinToInterrupt(PIN_DOOR_SENSOR), doorISR, CHANGE);
    sysMon.log("INFO", "Door sensor initialized (" + String(doorOpen ? "OPEN" : "CLOSED") + ")");

    // Initialize servo lock (restores state from EEPROM)
    initServoLock();
    sysMon.log("INFO", "Servo lock initialized (" + String(lockEngaged ? "LOCKED" : "UNLOCKED") + ")");

    // Load schedules from EEPROM
    loadSchedules();
    sysMon.log("INFO", "Loaded " + String(scheduleCount) + " schedules");

    // Increment boot counter
    bootCount = EEPROM.read(BOOT_COUNT_ADDR) | (EEPROM.read(BOOT_COUNT_ADDR + 1) << 8);
    bootCount++;
    EEPROM.write(BOOT_COUNT_ADDR, bootCount & 0xFF);
    EEPROM.write(BOOT_COUNT_ADDR + 1, (bootCount >> 8) & 0xFF);
    EEPROM.commit();
    sysMon.log("INFO", "Boot count: " + String(bootCount));
    
    // Initialize WiFi (try STA first, fallback to AP)
    if (!wifiMgr.connectSTA()) {
        Serial.println("[Setup] STA failed, starting dual mode...");
        wifiMgr.startDualMode();
    }
    
    // Start mDNS
    wifiMgr.startMDNS();
    
    // Setup NTP
    setupNTP();
    
    // Initialize MQTT
    mqttMgr.begin();
    mqttMgr.setCallback(onMQTTMessage);
    mqttMgr.connect();

    // Subscribe to Jarvis command topic
    mqttMgr.subscribe(TOPIC_JARVIS_CMD);
    sysMon.log("INFO", "Subscribed to Jarvis command topic");
    
    // Initialize OTA
    otaMgr.begin();
    
    // Initialize BLE
    bleMgr.begin();
    
    // Initialize Power Manager
    powerMgr.begin();
    
    // Setup WebSocket
    ws.onEvent(onWsEvent);
    server.addHandler(&ws);
    
    // Setup REST API
    setupAPI();
    
    // Start web server
    server.begin();
    Serial.printf("[HTTP] Server started on port %d\n", HTTP_PORT);
    
    // Create FreeRTOS tasks
    xTaskCreatePinnedToCore(sensorTask, "SensorTask", 4096, NULL, 2, &sensorTaskHandle, 0);
    xTaskCreatePinnedToCore(mqttTask, "MQTTTask", 4096, NULL, 1, &mqttTaskHandle, 1);
    xTaskCreatePinnedToCore(monitorTask, "MonitorTask", 4096, NULL, 1, &monitorTaskHandle, 0);
    xTaskCreatePinnedToCore(scheduleTask, "ScheduleTask", 4096, NULL, 1, &scheduleTaskHandle, 0);
    sysMon.log("INFO", "Schedule task created");
    
    // Setup watchdog
    esp_task_wdt_init(WATCHDOG_TIMEOUT, true);
    esp_task_wdt_add(NULL);
    
    // Show ready status
    gpioMgr.showStatus("ok");
    gpioMgr.buzzPattern("success");
    
    sysMon.log("INFO", "Server ready! IP: " + wifiMgr.getLocalIP());
    Serial.println("\n[Setup] ✓ All systems initialized successfully!\n");
}

// ============================================
// Main Loop
// ============================================
void loop() {
    // Reset watchdog
    esp_task_wdt_reset();
    
    // Increment loop counter for CPU monitoring
    sysMon.incrementLoop();
    
    // Handle OTA updates
    otaMgr.handle();
    
    // Handle MQTT
    mqttMgr.loop();
    
    // Handle WiFi reconnection
    wifiMgr.handleReconnect();
    
    // Handle BLE
    bleMgr.handle();

    // Handle door sensor events (ISR-triggered)
    handleDoorEvent();

    // Periodic heartbeat to Jarvis
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat >= HEARTBEAT_INTERVAL) {
        lastHeartbeat = millis();
        sendHeartbeat();
    }
    
    // Handle button events (single button cycles through relays)
    if (gpioMgr.isButtonPressed()) {
        int relayIdx = gpioMgr.getButtonRelayIndex();
        gpioMgr.toggleRelay(relayIdx);
        gpioMgr.buzzPattern("relay");
        sysMon.log("INFO", "Button: toggled relay " + String(relayIdx) + " (" + String(gpioMgr.getRelayRoom(relayIdx)) + ")");
        mqttMgr.publishAlert("button", "Relay " + String(relayIdx) + " toggled", 1);
    }
    
    // WebSocket cleanup
    ws.cleanupClients();
    
    // Small delay to prevent watchdog issues
    delay(1);
}
