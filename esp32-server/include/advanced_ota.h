/*
 * =============================================================
 * Feature 76: OTA Update Manager v2 - Enhanced over-the-air firmware updates
 * Feature 77: Device Grouping - Group devices by room/function
 * Feature 84: Device Twins - Digital twin representation
 * =============================================================
 */

#ifndef ADVANCED_OTA_H
#define ADVANCED_OTA_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>

// ==== Feature 76: Advanced OTA Manager ====
class AdvancedOTAManager {
private:
    String currentVersion;
    String updateUrl;
    bool autoUpdate;
    unsigned long lastCheckTime;
    unsigned long checkInterval;
    int updateProgress;
    String updateStatus;
    bool rollbackAvailable;
    String previousVersion;

    struct UpdateHistory {
        String version;
        unsigned long timestamp;
        bool success;
        String notes;
    };
    static const int MAX_HISTORY = 10;
    UpdateHistory history[MAX_HISTORY];
    int historyCount;

public:
    AdvancedOTAManager() : currentVersion("3.0.0"), autoUpdate(false),
        lastCheckTime(0), checkInterval(86400000), updateProgress(0),
        updateStatus("idle"), rollbackAvailable(false), historyCount(0) {}

    void begin(const String& version) {
        currentVersion = version;
        loadHistory();
        Serial.println("[OTA-v2] Advanced OTA Manager initialized, v" + currentVersion);
    }

    bool checkForUpdate() {
        lastCheckTime = millis();
        updateStatus = "checking";
        // Simulated check - in production would HTTP GET from update server
        Serial.println("[OTA-v2] Checking for firmware updates...");
        updateStatus = "up-to-date";
        return false;
    }

    void startUpdate(const String& url) {
        updateUrl = url;
        updateStatus = "downloading";
        updateProgress = 0;
        Serial.println("[OTA-v2] Starting firmware update from: " + url);
    }

    int getProgress() const { return updateProgress; }
    String getStatus() const { return updateStatus; }
    String getVersion() const { return currentVersion; }
    bool canRollback() const { return rollbackAvailable; }

    void rollback() {
        if (rollbackAvailable) {
            Serial.println("[OTA-v2] Rolling back to version: " + previousVersion);
            updateStatus = "rolling_back";
        }
    }

    void setAutoUpdate(bool enabled, unsigned long interval = 86400000) {
        autoUpdate = enabled;
        checkInterval = interval;
    }

    void addHistoryEntry(const String& ver, bool success, const String& notes) {
        if (historyCount < MAX_HISTORY) {
            history[historyCount++] = { ver, millis(), success, notes };
        }
    }

    void loadHistory() {
        if (SPIFFS.exists("/ota_history.json")) {
            File f = SPIFFS.open("/ota_history.json", "r");
            DynamicJsonDocument doc(2048);
            deserializeJson(doc, f);
            f.close();
            historyCount = 0;
            JsonArray arr = doc["history"].as<JsonArray>();
            for (JsonObject obj : arr) {
                if (historyCount < MAX_HISTORY) {
                    history[historyCount++] = {
                        obj["version"].as<String>(),
                        obj["timestamp"].as<unsigned long>(),
                        obj["success"].as<bool>(),
                        obj["notes"].as<String>()
                    };
                }
            }
        }
    }

    void toJson(JsonObject& obj) {
        obj["version"] = currentVersion;
        obj["status"] = updateStatus;
        obj["progress"] = updateProgress;
        obj["auto_update"] = autoUpdate;
        obj["rollback_available"] = rollbackAvailable;
        obj["check_interval_ms"] = checkInterval;
        obj["last_check"] = lastCheckTime;
        JsonArray hist = obj.createNestedArray("history");
        for (int i = 0; i < historyCount; i++) {
            JsonObject h = hist.createNestedObject();
            h["version"] = history[i].version;
            h["timestamp"] = history[i].timestamp;
            h["success"] = history[i].success;
            h["notes"] = history[i].notes;
        }
    }

    void loop() {
        if (autoUpdate && millis() - lastCheckTime > checkInterval) {
            checkForUpdate();
        }
    }
};

// ==== Feature 77: Device Grouping ====
class DeviceGroupManager {
private:
    struct DeviceGroup {
        String name;
        String room;
        String type; // "lighting", "security", "climate", "entertainment"
        String deviceIds[8];
        int deviceCount;
        bool enabled;
    };
    static const int MAX_GROUPS = 16;
    DeviceGroup groups[MAX_GROUPS];
    int groupCount;

public:
    DeviceGroupManager() : groupCount(0) {}

    void begin() {
        loadGroups();
        Serial.println("[Groups] Device Group Manager initialized");
    }

    int createGroup(const String& name, const String& room, const String& type) {
        if (groupCount >= MAX_GROUPS) return -1;
        groups[groupCount] = { name, room, type, {}, 0, true };
        return groupCount++;
    }

    bool addDeviceToGroup(int groupIdx, const String& deviceId) {
        if (groupIdx < 0 || groupIdx >= groupCount) return false;
        DeviceGroup& g = groups[groupIdx];
        if (g.deviceCount >= 8) return false;
        g.deviceIds[g.deviceCount++] = deviceId;
        return true;
    }

    bool removeDeviceFromGroup(int groupIdx, const String& deviceId) {
        if (groupIdx < 0 || groupIdx >= groupCount) return false;
        DeviceGroup& g = groups[groupIdx];
        for (int i = 0; i < g.deviceCount; i++) {
            if (g.deviceIds[i] == deviceId) {
                for (int j = i; j < g.deviceCount - 1; j++)
                    g.deviceIds[j] = g.deviceIds[j + 1];
                g.deviceCount--;
                return true;
            }
        }
        return false;
    }

    void deleteGroup(int groupIdx) {
        if (groupIdx < 0 || groupIdx >= groupCount) return;
        for (int i = groupIdx; i < groupCount - 1; i++)
            groups[i] = groups[i + 1];
        groupCount--;
    }

    void loadGroups() {
        if (SPIFFS.exists("/device_groups.json")) {
            File f = SPIFFS.open("/device_groups.json", "r");
            DynamicJsonDocument doc(4096);
            deserializeJson(doc, f);
            f.close();
            groupCount = 0;
            JsonArray arr = doc["groups"].as<JsonArray>();
            for (JsonObject obj : arr) {
                if (groupCount < MAX_GROUPS) {
                    groups[groupCount].name = obj["name"].as<String>();
                    groups[groupCount].room = obj["room"].as<String>();
                    groups[groupCount].type = obj["type"].as<String>();
                    groups[groupCount].enabled = obj["enabled"] | true;
                    groups[groupCount].deviceCount = 0;
                    JsonArray devs = obj["devices"].as<JsonArray>();
                    for (const char* d : devs) {
                        if (groups[groupCount].deviceCount < 8)
                            groups[groupCount].deviceIds[groups[groupCount].deviceCount++] = d;
                    }
                    groupCount++;
                }
            }
        }
    }

    void saveGroups() {
        DynamicJsonDocument doc(4096);
        JsonArray arr = doc.createNestedArray("groups");
        for (int i = 0; i < groupCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["name"] = groups[i].name;
            obj["room"] = groups[i].room;
            obj["type"] = groups[i].type;
            obj["enabled"] = groups[i].enabled;
            JsonArray devs = obj.createNestedArray("devices");
            for (int j = 0; j < groups[i].deviceCount; j++)
                devs.add(groups[i].deviceIds[j]);
        }
        File f = SPIFFS.open("/device_groups.json", "w");
        serializeJson(doc, f);
        f.close();
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < groupCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["id"] = i;
            obj["name"] = groups[i].name;
            obj["room"] = groups[i].room;
            obj["type"] = groups[i].type;
            obj["enabled"] = groups[i].enabled;
            obj["device_count"] = groups[i].deviceCount;
            JsonArray devs = obj.createNestedArray("devices");
            for (int j = 0; j < groups[i].deviceCount; j++)
                devs.add(groups[i].deviceIds[j]);
        }
    }
};

// ==== Feature 84: Device Twins ====
class DeviceTwinManager {
private:
    struct DeviceTwin {
        String deviceId;
        DynamicJsonDocument* reportedState;
        DynamicJsonDocument* desiredState;
        unsigned long lastSynced;
        bool synced;
    };
    static const int MAX_TWINS = 8;
    DeviceTwin twins[MAX_TWINS];
    int twinCount;

public:
    DeviceTwinManager() : twinCount(0) {
        for (int i = 0; i < MAX_TWINS; i++) {
            twins[i].reportedState = nullptr;
            twins[i].desiredState = nullptr;
        }
    }

    void begin() { Serial.println("[Twins] Device Twin Manager initialized"); }

    int registerTwin(const String& deviceId) {
        if (twinCount >= MAX_TWINS) return -1;
        twins[twinCount].deviceId = deviceId;
        twins[twinCount].reportedState = new DynamicJsonDocument(1024);
        twins[twinCount].desiredState = new DynamicJsonDocument(1024);
        twins[twinCount].lastSynced = millis();
        twins[twinCount].synced = true;
        return twinCount++;
    }

    bool updateReported(const String& deviceId, const String& key, const String& value) {
        for (int i = 0; i < twinCount; i++) {
            if (twins[i].deviceId == deviceId) {
                (*twins[i].reportedState)[key] = value;
                twins[i].lastSynced = millis();
                checkSync(i);
                return true;
            }
        }
        return false;
    }

    bool setDesired(const String& deviceId, const String& key, const String& value) {
        for (int i = 0; i < twinCount; i++) {
            if (twins[i].deviceId == deviceId) {
                (*twins[i].desiredState)[key] = value;
                twins[i].synced = false;
                return true;
            }
        }
        return false;
    }

    void checkSync(int idx) {
        twins[idx].synced = (*twins[idx].reportedState) == (*twins[idx].desiredState);
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < twinCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["device_id"] = twins[i].deviceId;
            obj["synced"] = twins[i].synced;
            obj["last_synced"] = twins[i].lastSynced;
            JsonObject reported = obj.createNestedObject("reported");
            for (JsonPair kv : twins[i].reportedState->as<JsonObject>())
                reported[kv.key()] = kv.value();
            JsonObject desired = obj.createNestedObject("desired");
            for (JsonPair kv : twins[i].desiredState->as<JsonObject>())
                desired[kv.key()] = kv.value();
        }
    }
};

#endif // ADVANCED_OTA_H
