/*
 * =============================================================
 * Feature 78: ESP-NOW Mesh Networking
 * Feature 79: Advanced Power Management (Deep Sleep Schedules)
 * Feature 80: Enhanced Watchdog Timer Service
 * =============================================================
 */

#ifndef MESH_POWER_H
#define MESH_POWER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_now.h>
#include <esp_sleep.h>
#include <esp_task_wdt.h>

// ==== Feature 78: ESP-NOW Mesh Networking ====
class MeshNetwork {
private:
    struct MeshPeer {
        uint8_t mac[6];
        String name;
        bool active;
        unsigned long lastSeen;
        int rssi;
    };
    static const int MAX_PEERS = 10;
    MeshPeer peers[MAX_PEERS];
    int peerCount;
    bool initialized;
    String nodeId;

    struct MeshMessage {
        char type[16];  // "data", "command", "heartbeat", "broadcast"
        char sender[18]; // MAC as string
        char payload[200];
        uint32_t timestamp;
        uint8_t ttl;     // time-to-live for multi-hop
    };

    static MeshNetwork* instance;
    static void onDataRecvStatic(const uint8_t *mac, const uint8_t *data, int len) {
        if (instance) instance->onDataReceived(mac, data, len);
    }
    static void onDataSentStatic(const uint8_t *mac, esp_now_send_status_t status) {
        if (instance) instance->onDataSent(mac, status);
    }

    void onDataReceived(const uint8_t *mac, const uint8_t *data, int len) {
        MeshMessage msg;
        if (len <= (int)sizeof(MeshMessage)) {
            memcpy(&msg, data, len);
            Serial.printf("[Mesh] Received %s from %s\n", msg.type, msg.sender);

            // Update peer last seen
            for (int i = 0; i < peerCount; i++) {
                if (memcmp(peers[i].mac, mac, 6) == 0) {
                    peers[i].lastSeen = millis();
                    peers[i].active = true;
                    break;
                }
            }

            // Forward if TTL > 0 (multi-hop mesh)
            if (msg.ttl > 0 && strcmp(msg.type, "broadcast") == 0) {
                msg.ttl--;
                broadcast(String(msg.payload));
            }
        }
    }

    void onDataSent(const uint8_t *mac, esp_now_send_status_t status) {
        Serial.printf("[Mesh] Send status: %s\n", status == ESP_NOW_SEND_SUCCESS ? "OK" : "FAIL");
    }

public:
    MeshNetwork() : peerCount(0), initialized(false) { instance = this; }

    bool begin(const String& id) {
        nodeId = id;
        if (esp_now_init() != ESP_OK) {
            Serial.println("[Mesh] ESP-NOW init failed!");
            return false;
        }
        esp_now_register_recv_cb(onDataRecvStatic);
        esp_now_register_send_cb(onDataSentStatic);
        initialized = true;
        Serial.println("[Mesh] ESP-NOW Mesh initialized, node: " + nodeId);
        return true;
    }

    bool addPeer(const uint8_t* mac, const String& name) {
        if (peerCount >= MAX_PEERS) return false;
        esp_now_peer_info_t peerInfo = {};
        memcpy(peerInfo.peer_addr, mac, 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        if (esp_now_add_peer(&peerInfo) != ESP_OK) return false;

        memcpy(peers[peerCount].mac, mac, 6);
        peers[peerCount].name = name;
        peers[peerCount].active = false;
        peers[peerCount].lastSeen = 0;
        peerCount++;
        return true;
    }

    bool sendTo(const uint8_t* mac, const String& type, const String& payload) {
        MeshMessage msg = {};
        strncpy(msg.type, type.c_str(), 15);
        strncpy(msg.sender, nodeId.c_str(), 17);
        strncpy(msg.payload, payload.c_str(), 199);
        msg.timestamp = millis();
        msg.ttl = 3;
        return esp_now_send(mac, (uint8_t*)&msg, sizeof(MeshMessage)) == ESP_OK;
    }

    void broadcast(const String& payload) {
        for (int i = 0; i < peerCount; i++) {
            sendTo(peers[i].mac, "broadcast", payload);
        }
    }

    void sendHeartbeat() {
        broadcast("{\"type\":\"heartbeat\",\"node\":\"" + nodeId + "\"}");
    }

    int getActivePeerCount() {
        int count = 0;
        unsigned long now = millis();
        for (int i = 0; i < peerCount; i++) {
            if (now - peers[i].lastSeen < 30000) {
                peers[i].active = true;
                count++;
            } else {
                peers[i].active = false;
            }
        }
        return count;
    }

    void toJson(JsonObject& obj) {
        obj["node_id"] = nodeId;
        obj["initialized"] = initialized;
        obj["peer_count"] = peerCount;
        obj["active_peers"] = getActivePeerCount();
        JsonArray arr = obj.createNestedArray("peers");
        for (int i = 0; i < peerCount; i++) {
            JsonObject p = arr.createNestedObject();
            char macStr[18];
            sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
                peers[i].mac[0], peers[i].mac[1], peers[i].mac[2],
                peers[i].mac[3], peers[i].mac[4], peers[i].mac[5]);
            p["mac"] = macStr;
            p["name"] = peers[i].name;
            p["active"] = peers[i].active;
            p["last_seen"] = peers[i].lastSeen;
        }
    }
};

MeshNetwork* MeshNetwork::instance = nullptr;

// ==== Feature 79: Advanced Power Management ====
class AdvancedPowerManager {
private:
    struct SleepSchedule {
        uint8_t startHour;
        uint8_t startMinute;
        uint8_t endHour;
        uint8_t endMinute;
        uint64_t sleepDurationUs;
        bool enabled;
    };
    static const int MAX_SLEEP_SCHEDULES = 4;
    SleepSchedule sleepSchedules[MAX_SLEEP_SCHEDULES];
    int scheduleCount;

    float batteryVoltage;
    float batteryPercent;
    int batteryPin;
    bool onBattery;
    unsigned long lastBatteryRead;

    enum PowerMode { NORMAL, ECO, ULTRA_LOW, PERFORMANCE };
    PowerMode currentMode;

    struct PowerStats {
        unsigned long totalAwakeMs;
        unsigned long totalSleepMs;
        int sleepCycles;
        float avgCurrentMa;
    };
    PowerStats stats;

public:
    AdvancedPowerManager() : scheduleCount(0), batteryVoltage(0), batteryPercent(100),
        batteryPin(34), onBattery(false), lastBatteryRead(0), currentMode(NORMAL) {
        stats = {0, 0, 0, 0};
    }

    void begin(int batPin = 34) {
        batteryPin = batPin;
        pinMode(batteryPin, INPUT);
        readBattery();
        Serial.println("[Power] Advanced Power Manager initialized");
    }

    void readBattery() {
        int raw = analogRead(batteryPin);
        batteryVoltage = (raw / 4095.0) * 3.3 * 2; // voltage divider factor
        batteryPercent = constrain(map(batteryVoltage * 100, 320, 420, 0, 100), 0, 100);
        onBattery = batteryVoltage > 2.5 && batteryVoltage < 4.5;
        lastBatteryRead = millis();
    }

    void setPowerMode(PowerMode mode) {
        currentMode = mode;
        switch (mode) {
            case ECO:
                setCpuFrequencyMhz(80);
                WiFi.setSleep(true);
                Serial.println("[Power] ECO mode: CPU 80MHz, WiFi sleep ON");
                break;
            case ULTRA_LOW:
                setCpuFrequencyMhz(40);
                WiFi.setSleep(true);
                Serial.println("[Power] ULTRA LOW mode: CPU 40MHz");
                break;
            case PERFORMANCE:
                setCpuFrequencyMhz(240);
                WiFi.setSleep(false);
                Serial.println("[Power] PERFORMANCE mode: CPU 240MHz");
                break;
            default:
                setCpuFrequencyMhz(160);
                WiFi.setSleep(false);
                Serial.println("[Power] NORMAL mode: CPU 160MHz");
                break;
        }
    }

    void addSleepSchedule(uint8_t startH, uint8_t startM, uint8_t endH, uint8_t endM) {
        if (scheduleCount >= MAX_SLEEP_SCHEDULES) return;
        uint64_t durationMin = ((endH * 60 + endM) - (startH * 60 + startM));
        if (durationMin <= 0) durationMin += 1440;
        sleepSchedules[scheduleCount++] = {
            startH, startM, endH, endM,
            durationMin * 60ULL * 1000000ULL, true
        };
    }

    void enterDeepSleep(uint64_t durationUs) {
        Serial.printf("[Power] Entering deep sleep for %llu us\n", durationUs);
        stats.sleepCycles++;
        esp_sleep_enable_timer_wakeup(durationUs);
        esp_deep_sleep_start();
    }

    void enterLightSleep(uint64_t durationUs) {
        Serial.printf("[Power] Light sleep for %llu us\n", durationUs);
        esp_sleep_enable_timer_wakeup(durationUs);
        esp_light_sleep_start();
    }

    void toJson(JsonObject& obj) {
        obj["battery_voltage"] = batteryVoltage;
        obj["battery_percent"] = batteryPercent;
        obj["on_battery"] = onBattery;
        obj["power_mode"] = currentMode == NORMAL ? "normal" :
            currentMode == ECO ? "eco" : currentMode == ULTRA_LOW ? "ultra_low" : "performance";
        obj["cpu_mhz"] = getCpuFrequencyMhz();
        obj["free_heap"] = ESP.getFreeHeap();
        obj["min_free_heap"] = ESP.getMinFreeHeap();
        obj["total_awake_ms"] = stats.totalAwakeMs + millis();
        obj["sleep_cycles"] = stats.sleepCycles;
        JsonArray sched = obj.createNestedArray("sleep_schedules");
        for (int i = 0; i < scheduleCount; i++) {
            JsonObject s = sched.createNestedObject();
            char buf[6];
            sprintf(buf, "%02d:%02d", sleepSchedules[i].startHour, sleepSchedules[i].startMinute);
            s["start"] = String(buf);
            sprintf(buf, "%02d:%02d", sleepSchedules[i].endHour, sleepSchedules[i].endMinute);
            s["end"] = String(buf);
            s["enabled"] = sleepSchedules[i].enabled;
        }
    }

    void loop() {
        if (millis() - lastBatteryRead > 60000) readBattery();
        stats.totalAwakeMs = millis();
        // Auto eco mode if battery low
        if (onBattery && batteryPercent < 20 && currentMode != ECO) {
            setPowerMode(ECO);
        }
    }
};

// ==== Feature 80: Enhanced Watchdog Timer ====
class WatchdogManager {
private:
    unsigned long lastFeedTime;
    unsigned long timeoutMs;
    bool enabled;
    int resetCount;
    String lastResetReason;

    struct WatchdogTask {
        String name;
        unsigned long lastFeed;
        unsigned long timeout;
        bool active;
    };
    static const int MAX_WD_TASKS = 8;
    WatchdogTask tasks[MAX_WD_TASKS];
    int taskCount;

public:
    WatchdogManager() : lastFeedTime(0), timeoutMs(30000), enabled(false),
        resetCount(0), taskCount(0) {}

    void begin(unsigned long timeout = 30000) {
        timeoutMs = timeout;
        enabled = true;
        lastFeedTime = millis();

        // Get last reset reason
        esp_reset_reason_t reason = esp_reset_reason();
        switch (reason) {
            case ESP_RST_POWERON: lastResetReason = "power_on"; break;
            case ESP_RST_SW: lastResetReason = "software"; break;
            case ESP_RST_PANIC: lastResetReason = "panic"; resetCount++; break;
            case ESP_RST_INT_WDT: lastResetReason = "int_watchdog"; resetCount++; break;
            case ESP_RST_TASK_WDT: lastResetReason = "task_watchdog"; resetCount++; break;
            case ESP_RST_WDT: lastResetReason = "watchdog"; resetCount++; break;
            case ESP_RST_BROWNOUT: lastResetReason = "brownout"; resetCount++; break;
            default: lastResetReason = "unknown"; break;
        }

        // Enable hardware WDT
        esp_task_wdt_init(timeout / 1000, true);
        esp_task_wdt_add(NULL);

        Serial.printf("[WDT] Watchdog initialized, timeout=%lums, last_reset=%s\n",
            timeout, lastResetReason.c_str());
    }

    void feed() {
        lastFeedTime = millis();
        esp_task_wdt_reset();
    }

    int registerTask(const String& name, unsigned long timeout) {
        if (taskCount >= MAX_WD_TASKS) return -1;
        tasks[taskCount] = { name, millis(), timeout, true };
        return taskCount++;
    }

    void feedTask(int taskId) {
        if (taskId >= 0 && taskId < taskCount) {
            tasks[taskId].lastFeed = millis();
        }
    }

    bool checkTasks() {
        unsigned long now = millis();
        for (int i = 0; i < taskCount; i++) {
            if (tasks[i].active && (now - tasks[i].lastFeed > tasks[i].timeout)) {
                Serial.printf("[WDT] Task '%s' timed out!\n", tasks[i].name.c_str());
                return false;
            }
        }
        return true;
    }

    void toJson(JsonObject& obj) {
        obj["enabled"] = enabled;
        obj["timeout_ms"] = timeoutMs;
        obj["last_feed_ms"] = lastFeedTime;
        obj["reset_count"] = resetCount;
        obj["last_reset_reason"] = lastResetReason;
        obj["uptime_ms"] = millis();
        JsonArray arr = obj.createNestedArray("tasks");
        for (int i = 0; i < taskCount; i++) {
            JsonObject t = arr.createNestedObject();
            t["name"] = tasks[i].name;
            t["active"] = tasks[i].active;
            t["timeout_ms"] = tasks[i].timeout;
            t["time_since_feed"] = millis() - tasks[i].lastFeed;
        }
    }

    void loop() {
        if (enabled) {
            feed();
            if (!checkTasks()) {
                Serial.println("[WDT] Task watchdog violation detected!");
            }
        }
    }
};

#endif // MESH_POWER_H
