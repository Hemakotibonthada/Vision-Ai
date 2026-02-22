/*
 * =============================================================
 * Vision-AI ESP32 Server - Main Controller
 * =============================================================
 * Features: WiFi AP/STA, MQTT, WebSocket, REST API, OTA,
 *           Sensors, GPIO, BLE, Power Management, System Monitor
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

// ============================================
// Task Handles (FreeRTOS)
// ============================================
TaskHandle_t sensorTaskHandle = NULL;
TaskHandle_t mqttTaskHandle = NULL;
TaskHandle_t monitorTaskHandle = NULL;

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
        // Handle configuration updates
        sysMon.log("INFO", "Config update received");
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
