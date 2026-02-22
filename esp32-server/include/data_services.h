/*
 * =============================================================
 * Feature 92: WiFi Manager v2 - enhanced WiFi management
 * Feature 93: Captive Portal - initial WiFi setup
 * Feature 94: Sensor Calibration - per-sensor calibration
 * Feature 95: Data Logger - SPIFFS/SD data logging
 * Feature 96: IR Remote Service - infrared remote control
 * Feature 97: BLE Beacon Service - presence detection beacons
 * Feature 98: NTP Time Sync - accurate time synchronization
 * Feature 99: Environmental Index Calculator - comfort/AQI
 * Feature 100: Smart Power Strip Controller - outlet control
 * =============================================================
 */

#ifndef DATA_SERVICES_H
#define DATA_SERVICES_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <SPIFFS.h>
#include <time.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>

// ==== Feature 92: WiFi Manager v2 ====
class WiFiManagerV2 {
private:
    struct NetworkProfile {
        String ssid;
        String password;
        int8_t lastRSSI;
        int priority;
        bool autoConnect;
        unsigned long lastConnected;
    };
    static const int MAX_PROFILES = 8;
    NetworkProfile profiles[MAX_PROFILES];
    int profileCount;
    int reconnectAttempts;
    unsigned long lastReconnect;
    bool scanning;
    int scanResultCount;

public:
    WiFiManagerV2() : profileCount(0), reconnectAttempts(0),
        lastReconnect(0), scanning(false), scanResultCount(0) {}

    void begin() {
        WiFi.mode(WIFI_STA);
        WiFi.setAutoReconnect(true);
        Serial.println("[WiFi-v2] WiFi Manager v2 initialized");
    }

    int addNetwork(const String& ssid, const String& password, int priority = 0) {
        if (profileCount >= MAX_PROFILES) return -1;
        profiles[profileCount] = { ssid, password, 0, priority, true, 0 };
        return profileCount++;
    }

    bool connectToBest() {
        int bestIdx = -1;
        int bestPrio = -1;
        // Scan for available networks
        int n = WiFi.scanNetworks(false, true);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < profileCount; j++) {
                if (WiFi.SSID(i) == profiles[j].ssid && profiles[j].autoConnect) {
                    profiles[j].lastRSSI = WiFi.RSSI(i);
                    if (profiles[j].priority > bestPrio ||
                        (profiles[j].priority == bestPrio && profiles[j].lastRSSI > (bestIdx >= 0 ? profiles[bestIdx].lastRSSI : -100))) {
                        bestIdx = j;
                        bestPrio = profiles[j].priority;
                    }
                }
            }
        }
        WiFi.scanDelete();

        if (bestIdx >= 0) {
            Serial.printf("[WiFi-v2] Connecting to %s (RSSI: %d, Priority: %d)\n",
                profiles[bestIdx].ssid.c_str(), profiles[bestIdx].lastRSSI, profiles[bestIdx].priority);
            WiFi.begin(profiles[bestIdx].ssid.c_str(), profiles[bestIdx].password.c_str());
            unsigned long start = millis();
            while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
                delay(100);
            }
            if (WiFi.status() == WL_CONNECTED) {
                profiles[bestIdx].lastConnected = millis();
                reconnectAttempts = 0;
                return true;
            }
        }
        reconnectAttempts++;
        return false;
    }

    void monitor() {
        if (WiFi.status() != WL_CONNECTED && millis() - lastReconnect > 30000) {
            Serial.println("[WiFi-v2] Connection lost, attempting reconnect...");
            connectToBest();
            lastReconnect = millis();
        }
    }

    void toJson(JsonObject& obj) {
        obj["connected"] = WiFi.status() == WL_CONNECTED;
        obj["ssid"] = WiFi.SSID();
        obj["rssi"] = WiFi.RSSI();
        obj["ip"] = WiFi.localIP().toString();
        obj["mac"] = WiFi.macAddress();
        obj["channel"] = WiFi.channel();
        obj["reconnect_attempts"] = reconnectAttempts;
        obj["profile_count"] = profileCount;
        JsonArray arr = obj.createNestedArray("profiles");
        for (int i = 0; i < profileCount; i++) {
            JsonObject p = arr.createNestedObject();
            p["ssid"] = profiles[i].ssid;
            p["priority"] = profiles[i].priority;
            p["last_rssi"] = profiles[i].lastRSSI;
            p["auto_connect"] = profiles[i].autoConnect;
        }
    }
};

// ==== Feature 93: Captive Portal ====
class CaptivePortal {
private:
    bool active;
    String apSSID;
    String apPassword;
    String configuredSSID;
    String configuredPassword;
    bool configReceived;
    unsigned long startTime;

public:
    CaptivePortal() : active(false), configReceived(false), startTime(0) {}

    void begin(const String& apName = "ESP32-Setup", const String& apPass = "setup1234") {
        apSSID = apName;
        apPassword = apPass;
        Serial.println("[Portal] Captive Portal ready");
    }

    bool startAP() {
        WiFi.mode(WIFI_AP_STA);
        WiFi.softAP(apSSID.c_str(), apPassword.c_str());
        active = true;
        startTime = millis();
        Serial.printf("[Portal] AP started: %s @ %s\n",
            apSSID.c_str(), WiFi.softAPIP().toString().c_str());
        return true;
    }

    void stopAP() {
        WiFi.softAPdisconnect(true);
        WiFi.mode(WIFI_STA);
        active = false;
        Serial.println("[Portal] AP stopped");
    }

    void setCredentials(const String& ssid, const String& password) {
        configuredSSID = ssid;
        configuredPassword = password;
        configReceived = true;
    }

    String getPortalHTML() {
        return "<!DOCTYPE html><html><head><title>ESP32 Setup</title>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<style>body{font-family:Arial;margin:40px;background:#1a1a2e;color:#e0e0e0;}"
            "h1{color:#00d4ff;}input{width:100%;padding:10px;margin:8px 0;box-sizing:border-box;"
            "background:#16213e;color:#fff;border:1px solid #0f3460;border-radius:4px;}"
            "button{background:#00d4ff;color:#1a1a2e;padding:12px;border:none;border-radius:4px;"
            "width:100%;cursor:pointer;font-size:16px;font-weight:bold;}"
            "button:hover{background:#00b4d8;}"
            ".card{background:#16213e;padding:20px;border-radius:8px;max-width:400px;margin:0 auto;}"
            "</style></head><body>"
            "<div class='card'><h1>Vision AI Setup</h1>"
            "<form action='/configure' method='POST'>"
            "<label>WiFi SSID:</label><input name='ssid' required>"
            "<label>WiFi Password:</label><input name='pass' type='password' required>"
            "<label>Device Name:</label><input name='device' value='ESP32-Vision'>"
            "<button type='submit'>Connect</button></form></div></body></html>";
    }

    void toJson(JsonObject& obj) {
        obj["active"] = active;
        obj["ap_ssid"] = apSSID;
        obj["ap_ip"] = WiFi.softAPIP().toString();
        obj["clients_connected"] = WiFi.softAPgetStationNum();
        obj["config_received"] = configReceived;
        obj["uptime"] = active ? (millis() - startTime) / 1000 : 0;
    }
};

// ==== Feature 94: Sensor Calibration ====
class SensorCalibration {
private:
    struct CalibrationProfile {
        String sensorName;
        float offset;
        float scale;
        float minVal;
        float maxVal;
        unsigned long calibratedAt;
        bool isCalibrated;
        float rawSamples[16];
        int sampleCount;
    };
    static const int MAX_SENSORS = 8;
    CalibrationProfile sensors[MAX_SENSORS];
    int sensorCount;

public:
    SensorCalibration() : sensorCount(0) {}

    void begin() { Serial.println("[Cal] Sensor Calibration initialized"); }

    int addSensor(const String& name, float offset = 0, float scale = 1.0) {
        if (sensorCount >= MAX_SENSORS) return -1;
        sensors[sensorCount] = { name, offset, scale, -999, 999, 0, offset != 0 || scale != 1.0, {}, 0 };
        return sensorCount++;
    }

    void addSample(int sensorIdx, float rawValue) {
        if (sensorIdx < 0 || sensorIdx >= sensorCount) return;
        CalibrationProfile& s = sensors[sensorIdx];
        if (s.sampleCount < 16) {
            s.rawSamples[s.sampleCount++] = rawValue;
        }
    }

    bool calibrate(int sensorIdx, float knownLow, float knownHigh) {
        if (sensorIdx < 0 || sensorIdx >= sensorCount) return false;
        CalibrationProfile& s = sensors[sensorIdx];
        if (s.sampleCount < 2) return false;

        // Find min/max of raw samples
        float rawMin = s.rawSamples[0], rawMax = s.rawSamples[0];
        for (int i = 1; i < s.sampleCount; i++) {
            if (s.rawSamples[i] < rawMin) rawMin = s.rawSamples[i];
            if (s.rawSamples[i] > rawMax) rawMax = s.rawSamples[i];
        }

        if (rawMax - rawMin < 0.001) return false;
        s.scale = (knownHigh - knownLow) / (rawMax - rawMin);
        s.offset = knownLow - rawMin * s.scale;
        s.minVal = knownLow;
        s.maxVal = knownHigh;
        s.isCalibrated = true;
        s.calibratedAt = millis();
        s.sampleCount = 0;
        return true;
    }

    float apply(int sensorIdx, float rawValue) {
        if (sensorIdx < 0 || sensorIdx >= sensorCount) return rawValue;
        CalibrationProfile& s = sensors[sensorIdx];
        float result = rawValue * s.scale + s.offset;
        return constrain(result, s.minVal, s.maxVal);
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < sensorCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["name"] = sensors[i].sensorName;
            obj["offset"] = sensors[i].offset;
            obj["scale"] = sensors[i].scale;
            obj["calibrated"] = sensors[i].isCalibrated;
            obj["calibrated_at"] = sensors[i].calibratedAt;
            obj["samples"] = sensors[i].sampleCount;
        }
    }

    void saveToSPIFFS() {
        DynamicJsonDocument doc(2048);
        JsonArray arr = doc.to<JsonArray>();
        toJson(arr);
        File f = SPIFFS.open("/calibration.json", "w");
        if (f) { serializeJson(doc, f); f.close(); }
    }

    void loadFromSPIFFS() {
        File f = SPIFFS.open("/calibration.json", "r");
        if (!f) return;
        DynamicJsonDocument doc(2048);
        deserializeJson(doc, f);
        f.close();
        JsonArray arr = doc.as<JsonArray>();
        for (JsonObject obj : arr) {
            int idx = addSensor(obj["name"].as<String>(), obj["offset"] | 0.0, obj["scale"] | 1.0);
            if (idx >= 0) {
                sensors[idx].isCalibrated = obj["calibrated"] | false;
                sensors[idx].calibratedAt = obj["calibrated_at"] | 0;
            }
        }
    }
};

// ==== Feature 95: Data Logger ====
class DataLogger {
private:
    String logFilePath;
    unsigned long totalEntries;
    unsigned long maxFileSize;
    bool enabled;
    unsigned long lastFlush;

    struct LogBuffer {
        String data[16];
        int count;
    };
    LogBuffer buffer;

public:
    DataLogger() : logFilePath("/datalog.csv"), totalEntries(0),
        maxFileSize(500000), enabled(true), lastFlush(0) {
        buffer.count = 0;
    }

    void begin(const String& path = "/datalog.csv") {
        logFilePath = path;
        SPIFFS.begin(true);
        // Count existing entries
        File f = SPIFFS.open(logFilePath, "r");
        if (f) {
            while (f.available()) {
                if (f.read() == '\n') totalEntries++;
            }
            f.close();
        }
        Serial.printf("[Logger] Data Logger initialized (%lu entries)\n", totalEntries);
    }

    void log(const String& category, const String& value, const String& unit = "") {
        if (!enabled) return;
        String entry = String(millis() / 1000) + "," + category + "," + value + "," + unit;
        if (buffer.count < 16) {
            buffer.data[buffer.count++] = entry;
        }
        if (buffer.count >= 8 || millis() - lastFlush > 30000) {
            flush();
        }
    }

    void flush() {
        if (buffer.count == 0) return;
        // Check file size
        File f = SPIFFS.open(logFilePath, "r");
        if (f && f.size() > maxFileSize) {
            f.close();
            rotate();
        } else if (f) {
            f.close();
        }

        f = SPIFFS.open(logFilePath, "a");
        if (f) {
            for (int i = 0; i < buffer.count; i++) {
                f.println(buffer.data[i]);
                totalEntries++;
            }
            f.close();
            buffer.count = 0;
            lastFlush = millis();
        }
    }

    void rotate() {
        SPIFFS.remove("/datalog_old.csv");
        SPIFFS.rename(logFilePath, "/datalog_old.csv");
        Serial.println("[Logger] Log rotated");
    }

    void clear() {
        SPIFFS.remove(logFilePath);
        totalEntries = 0;
    }

    void toJson(JsonObject& obj) {
        obj["enabled"] = enabled;
        obj["file"] = logFilePath;
        obj["total_entries"] = totalEntries;
        obj["buffer_count"] = buffer.count;
        File f = SPIFFS.open(logFilePath, "r");
        if (f) {
            obj["file_size"] = f.size();
            obj["max_size"] = maxFileSize;
            f.close();
        }
        // Read last 5 entries
        JsonArray last = obj.createNestedArray("recent");
        f = SPIFFS.open(logFilePath, "r");
        if (f) {
            String lines[5];
            int lineIdx = 0;
            while (f.available()) {
                String line = f.readStringUntil('\n');
                lines[lineIdx % 5] = line;
                lineIdx++;
            }
            f.close();
            for (int i = 0; i < min(5, lineIdx); i++) {
                last.add(lines[(lineIdx - min(5, lineIdx) + i) % 5]);
            }
        }
    }
};

// ==== Feature 96: IR Remote Service ====
class IRRemoteService {
private:
    struct IRCommand {
        String name;
        String protocol;  // "NEC", "Sony", "RC5", "Raw"
        uint32_t code;
        uint8_t bits;
    };
    static const int MAX_COMMANDS = 24;
    IRCommand commands[MAX_COMMANDS];
    int commandCount;
    uint8_t sendPin;
    uint8_t recvPin;
    uint32_t lastReceived;

public:
    IRRemoteService() : commandCount(0), sendPin(4), recvPin(15), lastReceived(0) {}

    void begin(uint8_t txPin = 4, uint8_t rxPin = 15) {
        sendPin = txPin;
        recvPin = rxPin;
        pinMode(sendPin, OUTPUT);
        Serial.println("[IR] IR Remote Service initialized");
    }

    int learnCommand(const String& name, uint32_t code, const String& protocol = "NEC", uint8_t bits = 32) {
        if (commandCount >= MAX_COMMANDS) return -1;
        commands[commandCount] = { name, protocol, code, bits };
        return commandCount++;
    }

    bool sendCommand(int cmdIdx) {
        if (cmdIdx < 0 || cmdIdx >= commandCount) return false;
        // Simulate NEC protocol send via GPIO toggle
        IRCommand& cmd = commands[cmdIdx];
        Serial.printf("[IR] Sending %s: 0x%08X (%s, %d bits)\n",
            cmd.name.c_str(), cmd.code, cmd.protocol.c_str(), cmd.bits);
        // Toggle send pin to simulate IR output
        for (int i = cmd.bits - 1; i >= 0; i--) {
            bool bit = (cmd.code >> i) & 1;
            digitalWrite(sendPin, HIGH);
            delayMicroseconds(bit ? 1687 : 562);
            digitalWrite(sendPin, LOW);
            delayMicroseconds(562);
        }
        return true;
    }

    bool sendByName(const String& name) {
        for (int i = 0; i < commandCount; i++) {
            if (commands[i].name == name) return sendCommand(i);
        }
        return false;
    }

    void toJson(JsonObject& obj) {
        obj["tx_pin"] = sendPin;
        obj["rx_pin"] = recvPin;
        obj["command_count"] = commandCount;
        obj["last_received"] = lastReceived;
        JsonArray arr = obj.createNestedArray("commands");
        for (int i = 0; i < commandCount; i++) {
            JsonObject c = arr.createNestedObject();
            c["name"] = commands[i].name;
            c["protocol"] = commands[i].protocol;
            char codeBuf[12];
            sprintf(codeBuf, "0x%08X", commands[i].code);
            c["code"] = codeBuf;
            c["bits"] = commands[i].bits;
        }
    }
};

// ==== Feature 97: BLE Beacon Service ====
class BLEBeaconService {
private:
    struct BeaconDevice {
        String address;
        String name;
        int rssi;
        float distance; // estimated in meters
        unsigned long lastSeen;
        bool isPresent;
        int txPower;
    };
    static const int MAX_BEACONS = 16;
    BeaconDevice knownBeacons[MAX_BEACONS];
    int beaconCount;
    BLEScan* pBLEScan;
    unsigned long lastScan;
    int scanDuration;
    unsigned long presenceTimeout;

    float estimateDistance(int rssi, int txPower) {
        if (rssi == 0 || txPower == 0) return -1;
        float ratio = (float)(txPower - rssi) / 20.0;
        return pow(10.0, ratio);
    }

public:
    BLEBeaconService() : beaconCount(0), pBLEScan(nullptr),
        lastScan(0), scanDuration(3), presenceTimeout(60000) {}

    void begin() {
        BLEDevice::init("ESP32-Vision-Beacon");
        pBLEScan = BLEDevice::getScan();
        pBLEScan->setActiveScan(true);
        pBLEScan->setInterval(100);
        pBLEScan->setWindow(99);
        Serial.println("[BLE-Beacon] BLE Beacon Service initialized");
    }

    int addKnownBeacon(const String& address, const String& name, int txPower = -59) {
        if (beaconCount >= MAX_BEACONS) return -1;
        knownBeacons[beaconCount] = { address, name, 0, -1, 0, false, txPower };
        return beaconCount++;
    }

    void scan() {
        if (!pBLEScan) return;
        BLEScanResults results = pBLEScan->start(scanDuration, false);
        unsigned long now = millis();

        for (int i = 0; i < results.getCount(); i++) {
            BLEAdvertisedDevice device = results.getDevice(i);
            String addr = device.getAddress().toString().c_str();
            // Check against known beacons
            for (int j = 0; j < beaconCount; j++) {
                if (addr.equalsIgnoreCase(knownBeacons[j].address)) {
                    knownBeacons[j].rssi = device.getRSSI();
                    knownBeacons[j].distance = estimateDistance(device.getRSSI(), knownBeacons[j].txPower);
                    knownBeacons[j].lastSeen = now;
                    knownBeacons[j].isPresent = true;
                }
            }
        }

        // Mark absent beacons
        for (int i = 0; i < beaconCount; i++) {
            if (now - knownBeacons[i].lastSeen > presenceTimeout) {
                knownBeacons[i].isPresent = false;
            }
        }

        pBLEScan->clearResults();
        lastScan = now;
    }

    int getPresentCount() {
        int count = 0;
        for (int i = 0; i < beaconCount; i++)
            if (knownBeacons[i].isPresent) count++;
        return count;
    }

    void toJson(JsonObject& obj) {
        obj["beacon_count"] = beaconCount;
        obj["present_count"] = getPresentCount();
        obj["last_scan"] = lastScan;
        obj["scan_duration"] = scanDuration;
        JsonArray arr = obj.createNestedArray("beacons");
        for (int i = 0; i < beaconCount; i++) {
            JsonObject b = arr.createNestedObject();
            b["address"] = knownBeacons[i].address;
            b["name"] = knownBeacons[i].name;
            b["rssi"] = knownBeacons[i].rssi;
            b["distance_m"] = knownBeacons[i].distance;
            b["present"] = knownBeacons[i].isPresent;
            b["last_seen"] = knownBeacons[i].lastSeen;
        }
    }
};

// ==== Feature 98: NTP Time Sync ====
class NTPTimeSync {
private:
    String ntpServer1;
    String ntpServer2;
    long gmtOffset;
    int dstOffset;
    bool synced;
    unsigned long lastSync;
    unsigned long syncInterval;

public:
    NTPTimeSync() : ntpServer1("pool.ntp.org"), ntpServer2("time.nist.gov"),
        gmtOffset(0), dstOffset(0), synced(false), lastSync(0), syncInterval(3600000) {}

    void begin(long gmtOffsetSec = 0, int dstOffsetSec = 0) {
        gmtOffset = gmtOffsetSec;
        dstOffset = dstOffsetSec;
        configTime(gmtOffset, dstOffset, ntpServer1.c_str(), ntpServer2.c_str());
        Serial.println("[NTP] NTP Time Sync initialized");
        sync();
    }

    bool sync() {
        struct tm timeinfo;
        if (getLocalTime(&timeinfo, 5000)) {
            synced = true;
            lastSync = millis();
            Serial.printf("[NTP] Time synced: %04d-%02d-%02d %02d:%02d:%02d\n",
                timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
            return true;
        }
        synced = false;
        return false;
    }

    void loop() {
        if (millis() - lastSync > syncInterval) {
            sync();
        }
    }

    String getISO8601() {
        struct tm t;
        if (!getLocalTime(&t)) return "1970-01-01T00:00:00Z";
        char buf[32];
        strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
        return String(buf);
    }

    unsigned long getEpoch() {
        time_t now;
        time(&now);
        return (unsigned long)now;
    }

    String getFormatted(const String& format = "%H:%M:%S") {
        struct tm t;
        if (!getLocalTime(&t)) return "--:--:--";
        char buf[64];
        strftime(buf, sizeof(buf), format.c_str(), &t);
        return String(buf);
    }

    void toJson(JsonObject& obj) {
        obj["synced"] = synced;
        obj["iso8601"] = getISO8601();
        obj["epoch"] = getEpoch();
        obj["time"] = getFormatted();
        obj["date"] = getFormatted("%Y-%m-%d");
        obj["ntp_server"] = ntpServer1;
        obj["gmt_offset"] = gmtOffset;
        obj["dst_offset"] = dstOffset;
        obj["last_sync"] = lastSync;
    }
};

// ==== Feature 99: Environmental Index Calculator ====
class EnvironmentalIndex {
private:
    float temperature;   // Celsius
    float humidity;      // %
    float co2;           // ppm
    float pm25;          // ug/m3
    float noise;         // dB
    float light;         // lux

    float calcHeatIndex() {
        // Simplified heat index
        float T = temperature * 9.0 / 5.0 + 32; // to Fahrenheit
        float HI = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (humidity * 0.094));
        return (HI - 32) * 5.0 / 9.0; // back to Celsius
    }

    float calcComfortIndex() {
        float score = 100;
        // Temperature comfort (ideal: 20-24°C)
        if (temperature < 18) score -= (18 - temperature) * 5;
        else if (temperature > 26) score -= (temperature - 26) * 5;
        // Humidity comfort (ideal: 40-60%)
        if (humidity < 30) score -= (30 - humidity) * 1.5;
        else if (humidity > 70) score -= (humidity - 70) * 1.5;
        // CO2 (ideal: < 800 ppm)
        if (co2 > 800) score -= (co2 - 800) / 50.0;
        // PM2.5 (ideal: < 12 ug/m3)
        if (pm25 > 12) score -= (pm25 - 12) * 2;
        // Noise (ideal: < 40 dB)
        if (noise > 40) score -= (noise - 40) * 0.5;
        return constrain(score, 0, 100);
    }

    String calcAQI() {
        if (pm25 <= 12) return "Good";
        if (pm25 <= 35.4) return "Moderate";
        if (pm25 <= 55.4) return "Unhealthy for Sensitive";
        if (pm25 <= 150.4) return "Unhealthy";
        if (pm25 <= 250.4) return "Very Unhealthy";
        return "Hazardous";
    }

public:
    EnvironmentalIndex() : temperature(22), humidity(50), co2(400),
        pm25(5), noise(30), light(300) {}

    void begin() { Serial.println("[EnvIdx] Environmental Index Calculator initialized"); }

    void update(float temp, float hum, float co2ppm = 0, float pm = 0,
                float noisedB = 0, float luxVal = 0) {
        temperature = temp;
        humidity = hum;
        if (co2ppm > 0) co2 = co2ppm;
        if (pm > 0) pm25 = pm;
        if (noisedB > 0) noise = noisedB;
        if (luxVal > 0) light = luxVal;
    }

    void toJson(JsonObject& obj) {
        obj["temperature"] = temperature;
        obj["humidity"] = humidity;
        obj["co2"] = co2;
        obj["pm25"] = pm25;
        obj["noise_db"] = noise;
        obj["light_lux"] = light;
        obj["heat_index"] = calcHeatIndex();
        obj["comfort_index"] = calcComfortIndex();
        obj["aqi"] = calcAQI();
        // Recommendations
        JsonArray recs = obj.createNestedArray("recommendations");
        if (temperature > 26) recs.add("Temperature high - consider cooling");
        if (temperature < 18) recs.add("Temperature low - consider heating");
        if (humidity > 70) recs.add("Humidity high - use dehumidifier");
        if (humidity < 30) recs.add("Humidity low - use humidifier");
        if (co2 > 1000) recs.add("CO2 elevated - increase ventilation");
        if (pm25 > 35) recs.add("Poor air quality - use air purifier");
        if (noise > 60) recs.add("Noise level high");
        if (light < 100) recs.add("Low ambient light");
    }
};

// ==== Feature 100: Smart Power Strip Controller ====
class SmartPowerStrip {
private:
    struct Outlet {
        uint8_t pin;
        String name;
        bool isOn;
        float powerWatts;      // rated power
        float energyKWh;       // accumulated energy
        unsigned long onSince;
        unsigned long totalOnTime;
        uint8_t maxAmps;
        bool hasSchedule;
        uint8_t scheduleOnHour;
        uint8_t scheduleOnMin;
        uint8_t scheduleOffHour;
        uint8_t scheduleOffMin;
    };
    static const int MAX_OUTLETS = 8;
    Outlet outlets[MAX_OUTLETS];
    int outletCount;
    bool masterSwitch;
    float totalPowerBudget; // watts

public:
    SmartPowerStrip() : outletCount(0), masterSwitch(true), totalPowerBudget(2000) {}

    void begin() { Serial.println("[Strip] Smart Power Strip initialized"); }

    int addOutlet(uint8_t pin, const String& name, float ratedWatts = 100) {
        if (outletCount >= MAX_OUTLETS) return -1;
        pinMode(pin, OUTPUT);
        digitalWrite(pin, LOW);
        outlets[outletCount] = { pin, name, false, ratedWatts, 0, 0, 0, 10, false, 0, 0, 0, 0 };
        return outletCount++;
    }

    bool setOutlet(int idx, bool on) {
        if (idx < 0 || idx >= outletCount) return false;
        if (!masterSwitch && on) return false;

        // Power budget check
        if (on) {
            float currentTotal = 0;
            for (int i = 0; i < outletCount; i++)
                if (outlets[i].isOn) currentTotal += outlets[i].powerWatts;
            if (currentTotal + outlets[idx].powerWatts > totalPowerBudget) {
                Serial.println("[Strip] Power budget exceeded!");
                return false;
            }
        }

        outlets[idx].isOn = on;
        digitalWrite(outlets[idx].pin, on ? HIGH : LOW);
        if (on) {
            outlets[idx].onSince = millis();
        } else if (outlets[idx].onSince > 0) {
            unsigned long duration = millis() - outlets[idx].onSince;
            outlets[idx].totalOnTime += duration;
            outlets[idx].energyKWh += (outlets[idx].powerWatts * duration) / 3600000000.0;
        }
        Serial.printf("[Strip] Outlet %d (%s): %s\n", idx, outlets[idx].name.c_str(), on ? "ON" : "OFF");
        return true;
    }

    void setMaster(bool on) {
        masterSwitch = on;
        if (!on) {
            for (int i = 0; i < outletCount; i++) setOutlet(i, false);
        }
    }

    void setSchedule(int idx, uint8_t onH, uint8_t onM, uint8_t offH, uint8_t offM) {
        if (idx < 0 || idx >= outletCount) return;
        outlets[idx].hasSchedule = true;
        outlets[idx].scheduleOnHour = onH;
        outlets[idx].scheduleOnMin = onM;
        outlets[idx].scheduleOffHour = offH;
        outlets[idx].scheduleOffMin = offM;
    }

    void checkSchedules() {
        struct tm t;
        if (!getLocalTime(&t)) return;
        for (int i = 0; i < outletCount; i++) {
            if (!outlets[i].hasSchedule) continue;
            int currentMin = t.tm_hour * 60 + t.tm_min;
            int onMin = outlets[i].scheduleOnHour * 60 + outlets[i].scheduleOnMin;
            int offMin = outlets[i].scheduleOffHour * 60 + outlets[i].scheduleOffMin;
            if (currentMin == onMin && !outlets[i].isOn) setOutlet(i, true);
            if (currentMin == offMin && outlets[i].isOn) setOutlet(i, false);
        }
    }

    float getTotalPower() {
        float total = 0;
        for (int i = 0; i < outletCount; i++)
            if (outlets[i].isOn) total += outlets[i].powerWatts;
        return total;
    }

    void toJson(JsonObject& obj) {
        obj["master"] = masterSwitch;
        obj["outlet_count"] = outletCount;
        obj["total_power_w"] = getTotalPower();
        obj["power_budget_w"] = totalPowerBudget;
        obj["budget_used_pct"] = totalPowerBudget > 0 ? (getTotalPower() / totalPowerBudget * 100) : 0;
        float totalEnergy = 0;
        JsonArray arr = obj.createNestedArray("outlets");
        for (int i = 0; i < outletCount; i++) {
            JsonObject o = arr.createNestedObject();
            o["index"] = i;
            o["pin"] = outlets[i].pin;
            o["name"] = outlets[i].name;
            o["on"] = outlets[i].isOn;
            o["power_w"] = outlets[i].isOn ? outlets[i].powerWatts : 0;
            o["energy_kwh"] = outlets[i].energyKWh;
            o["total_on_hours"] = outlets[i].totalOnTime / 3600000.0;
            if (outlets[i].hasSchedule) {
                char sch[32];
                sprintf(sch, "%02d:%02d-%02d:%02d",
                    outlets[i].scheduleOnHour, outlets[i].scheduleOnMin,
                    outlets[i].scheduleOffHour, outlets[i].scheduleOffMin);
                o["schedule"] = sch;
            }
            totalEnergy += outlets[i].energyKWh;
        }
        obj["total_energy_kwh"] = totalEnergy;
    }
};

#endif // DATA_SERVICES_H
