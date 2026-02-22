/*
 * =============================================================
 * Feature 81: Sensor Fusion - combine multiple sensor inputs
 * Feature 82: Edge AI Pipeline - on-device preprocessing
 * Feature 83: Firmware Version Tracker
 * Feature 85: Network Scanner - discover devices
 * Feature 86: Bandwidth Monitor - track data usage
 * =============================================================
 */

#ifndef SENSOR_FUSION_H
#define SENSOR_FUSION_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>

// ==== Feature 81: Sensor Fusion Engine ====
class SensorFusionEngine {
private:
    struct SensorReading {
        String sensorId;
        String type; // "temperature", "humidity", "motion", "light", "sound", "gas", "pressure"
        float value;
        float confidence;
        unsigned long timestamp;
    };
    static const int MAX_READINGS = 32;
    SensorReading readings[MAX_READINGS];
    int readingCount;

    // Kalman filter state per sensor type
    struct KalmanState {
        float estimate;
        float errorEstimate;
        float errorMeasure;
        float gain;
        String type;
    };
    static const int MAX_KALMAN = 8;
    KalmanState kalman[MAX_KALMAN];
    int kalmanCount;

    // Fused environmental state
    struct EnvironmentState {
        float temperature;
        float humidity;
        float lightLevel;
        float soundLevel;
        float airQuality;
        float comfortIndex;
        bool motionDetected;
        bool occupied;
        int occupantCount;
        unsigned long lastUpdated;
    };
    EnvironmentState environment;

public:
    SensorFusionEngine() : readingCount(0), kalmanCount(0) {
        environment = { 22.0, 50.0, 500.0, 30.0, 100.0, 75.0, false, false, 0, 0 };
    }

    void begin() { Serial.println("[Fusion] Sensor Fusion Engine initialized"); }

    float kalmanFilter(const String& type, float measurement) {
        int idx = -1;
        for (int i = 0; i < kalmanCount; i++) {
            if (kalman[i].type == type) { idx = i; break; }
        }
        if (idx < 0) {
            if (kalmanCount >= MAX_KALMAN) return measurement;
            idx = kalmanCount++;
            kalman[idx] = { measurement, 2.0, 4.0, 0, type };
        }

        KalmanState& k = kalman[idx];
        k.gain = k.errorEstimate / (k.errorEstimate + k.errorMeasure);
        k.estimate = k.estimate + k.gain * (measurement - k.estimate);
        k.errorEstimate = (1.0 - k.gain) * k.errorEstimate + fabs(k.estimate - measurement) * 0.1;
        return k.estimate;
    }

    void addReading(const String& sensorId, const String& type, float value, float confidence = 1.0) {
        float filtered = kalmanFilter(type, value);

        if (readingCount >= MAX_READINGS) {
            // Shift old readings
            for (int i = 0; i < MAX_READINGS - 1; i++)
                readings[i] = readings[i + 1];
            readingCount = MAX_READINGS - 1;
        }
        readings[readingCount++] = { sensorId, type, filtered, confidence, millis() };

        // Update fused environment
        if (type == "temperature") environment.temperature = filtered;
        else if (type == "humidity") environment.humidity = filtered;
        else if (type == "light") environment.lightLevel = filtered;
        else if (type == "sound") environment.soundLevel = filtered;
        else if (type == "gas") environment.airQuality = filtered;
        else if (type == "motion" && filtered > 0) environment.motionDetected = true;

        updateComfortIndex();
        environment.lastUpdated = millis();
    }

    void updateComfortIndex() {
        // Heat Index + humidity comfort
        float t = environment.temperature;
        float h = environment.humidity;
        float comfort = 100;
        if (t < 18 || t > 28) comfort -= abs(t - 23) * 3;
        if (h < 30 || h > 70) comfort -= abs(h - 50);
        if (environment.soundLevel > 60) comfort -= (environment.soundLevel - 60);
        if (environment.airQuality < 50) comfort -= (50 - environment.airQuality);
        environment.comfortIndex = constrain(comfort, 0, 100);
    }

    EnvironmentState getEnvironment() const { return environment; }

    void toJson(JsonObject& obj) {
        obj["temperature"] = environment.temperature;
        obj["humidity"] = environment.humidity;
        obj["light_level"] = environment.lightLevel;
        obj["sound_level"] = environment.soundLevel;
        obj["air_quality"] = environment.airQuality;
        obj["comfort_index"] = environment.comfortIndex;
        obj["motion_detected"] = environment.motionDetected;
        obj["occupied"] = environment.occupied;
        obj["occupant_count"] = environment.occupantCount;
        obj["reading_count"] = readingCount;
        obj["last_updated"] = environment.lastUpdated;
    }
};

// ==== Feature 82: Edge AI Pipeline ====
class EdgeAIPipeline {
private:
    struct ProcessingStage {
        String name;
        bool enabled;
        unsigned long avgProcessTimeUs;
        int processCount;
    };
    static const int MAX_STAGES = 8;
    ProcessingStage stages[MAX_STAGES];
    int stageCount;

    // Frame buffer for edge preprocessing
    uint8_t* frameBuffer;
    size_t frameSize;
    int frameWidth;
    int frameHeight;
    bool hasFrame;

    // Detection results
    struct EdgeDetection {
        int classId;
        float confidence;
        int x, y, w, h;
    };
    static const int MAX_DETECTIONS = 20;
    EdgeDetection detections[MAX_DETECTIONS];
    int detectionCount;

    // Motion detection state
    uint8_t* prevFrame;
    float motionScore;
    float motionThreshold;

public:
    EdgeAIPipeline() : stageCount(0), frameBuffer(nullptr), frameSize(0),
        frameWidth(0), frameHeight(0), hasFrame(false),
        detectionCount(0), prevFrame(nullptr), motionScore(0), motionThreshold(10.0) {
        // Register default processing stages
        addStage("grayscale");
        addStage("resize");
        addStage("normalize");
        addStage("motion_detect");
        addStage("roi_extract");
        addStage("threshold");
    }

    void begin() { Serial.println("[Edge-AI] Edge AI Pipeline initialized"); }

    void addStage(const String& name) {
        if (stageCount < MAX_STAGES) {
            stages[stageCount++] = { name, true, 0, 0 };
        }
    }

    void enableStage(const String& name, bool enabled) {
        for (int i = 0; i < stageCount; i++) {
            if (stages[i].name == name) {
                stages[i].enabled = enabled;
                break;
            }
        }
    }

    // Simple grayscale conversion (in-place)
    void toGrayscale(uint8_t* rgb, int pixels) {
        for (int i = 0; i < pixels; i++) {
            int idx = i * 3;
            uint8_t gray = (uint8_t)(rgb[idx] * 0.299 + rgb[idx+1] * 0.587 + rgb[idx+2] * 0.114);
            rgb[idx] = rgb[idx+1] = rgb[idx+2] = gray;
        }
    }

    // Simple frame difference motion detection
    float detectMotion(uint8_t* frame, int size) {
        if (!prevFrame) {
            prevFrame = (uint8_t*)malloc(size);
            if (prevFrame) memcpy(prevFrame, frame, size);
            return 0;
        }
        long diff = 0;
        for (int i = 0; i < size; i += 4) {
            diff += abs((int)frame[i] - (int)prevFrame[i]);
        }
        memcpy(prevFrame, frame, size);
        motionScore = (float)diff / (size / 4);
        return motionScore;
    }

    // Simple thresholding for binary mask
    void threshold(uint8_t* frame, int size, uint8_t thresh) {
        for (int i = 0; i < size; i++) {
            frame[i] = frame[i] > thresh ? 255 : 0;
        }
    }

    float getMotionScore() const { return motionScore; }
    bool isMotionDetected() const { return motionScore > motionThreshold; }
    void setMotionThreshold(float t) { motionThreshold = t; }

    void toJson(JsonObject& obj) {
        obj["stage_count"] = stageCount;
        obj["motion_score"] = motionScore;
        obj["motion_detected"] = isMotionDetected();
        obj["motion_threshold"] = motionThreshold;
        obj["detection_count"] = detectionCount;
        JsonArray arr = obj.createNestedArray("stages");
        for (int i = 0; i < stageCount; i++) {
            JsonObject s = arr.createNestedObject();
            s["name"] = stages[i].name;
            s["enabled"] = stages[i].enabled;
            s["avg_process_us"] = stages[i].avgProcessTimeUs;
            s["process_count"] = stages[i].processCount;
        }
    }
};

// ==== Feature 83: Firmware Version Tracker ====
class FirmwareTracker {
private:
    struct FirmwareInfo {
        String deviceId;
        String currentVersion;
        String targetVersion;
        String buildDate;
        String boardType;
        unsigned long flashSize;
        unsigned long sketchSize;
        unsigned long freeSketchSpace;
        bool needsUpdate;
    };
    static const int MAX_TRACKED = 8;
    FirmwareInfo tracked[MAX_TRACKED];
    int trackedCount;

public:
    FirmwareTracker() : trackedCount(0) {}

    void begin() {
        // Register self
        registerDevice(
            WiFi.macAddress(),
            "3.0.0",
            __DATE__ " " __TIME__,
            "ESP32-Server"
        );
        Serial.println("[FW] Firmware Version Tracker initialized");
    }

    void registerDevice(const String& deviceId, const String& version,
                        const String& buildDate, const String& boardType) {
        if (trackedCount >= MAX_TRACKED) return;
        tracked[trackedCount++] = {
            deviceId, version, version, buildDate, boardType,
            ESP.getFlashChipSize(), ESP.getSketchSize(), ESP.getFreeSketchSpace(),
            false
        };
    }

    void setTargetVersion(const String& deviceId, const String& version) {
        for (int i = 0; i < trackedCount; i++) {
            if (tracked[i].deviceId == deviceId) {
                tracked[i].targetVersion = version;
                tracked[i].needsUpdate = (tracked[i].currentVersion != version);
                break;
            }
        }
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < trackedCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["device_id"] = tracked[i].deviceId;
            obj["current_version"] = tracked[i].currentVersion;
            obj["target_version"] = tracked[i].targetVersion;
            obj["build_date"] = tracked[i].buildDate;
            obj["board_type"] = tracked[i].boardType;
            obj["flash_size"] = tracked[i].flashSize;
            obj["sketch_size"] = tracked[i].sketchSize;
            obj["free_sketch_space"] = tracked[i].freeSketchSpace;
            obj["needs_update"] = tracked[i].needsUpdate;
        }
    }
};

// ==== Feature 85: Network Scanner ====
class NetworkScanner {
private:
    struct NetworkDevice {
        String ip;
        String mac;
        String hostname;
        String type; // "esp32", "camera", "gateway", "unknown"
        bool reachable;
        int responseTimeMs;
        unsigned long lastScan;
    };
    static const int MAX_NET_DEVICES = 32;
    NetworkDevice devices[MAX_NET_DEVICES];
    int deviceCount;
    bool scanning;
    unsigned long lastScanTime;

public:
    NetworkScanner() : deviceCount(0), scanning(false), lastScanTime(0) {}

    void begin() { Serial.println("[NetScan] Network Scanner initialized"); }

    void startScan() {
        scanning = true;
        deviceCount = 0;
        lastScanTime = millis();
        Serial.println("[NetScan] Starting network scan...");

        // Add gateway
        IPAddress gw = WiFi.gatewayIP();
        addDevice(gw.toString(), "", "Gateway", "gateway");

        // ARP scan local subnet
        IPAddress local = WiFi.localIP();
        IPAddress subnet = WiFi.subnetMask();
        // Scan first 20 IPs for demo (full scan would be slow)
        for (int i = 1; i <= 20 && deviceCount < MAX_NET_DEVICES; i++) {
            IPAddress target(local[0], local[1], local[2], i);
            if (target == local) {
                addDevice(target.toString(), WiFi.macAddress(), "Self", "esp32");
                continue;
            }
            // Quick connectivity check via WiFiClient
            WiFiClient client;
            unsigned long start = millis();
            if (client.connect(target, 80, 100)) {
                int respTime = millis() - start;
                addDevice(target.toString(), "", "Unknown", "unknown");
                devices[deviceCount - 1].responseTimeMs = respTime;
                devices[deviceCount - 1].reachable = true;
                client.stop();
            }
        }
        scanning = false;
    }

    void addDevice(const String& ip, const String& mac, const String& hostname, const String& type) {
        if (deviceCount < MAX_NET_DEVICES) {
            devices[deviceCount++] = { ip, mac, hostname, type, true, 0, millis() };
        }
    }

    void toJson(JsonObject& obj) {
        obj["scanning"] = scanning;
        obj["device_count"] = deviceCount;
        obj["last_scan"] = lastScanTime;
        obj["local_ip"] = WiFi.localIP().toString();
        obj["gateway"] = WiFi.gatewayIP().toString();
        obj["subnet"] = WiFi.subnetMask().toString();
        JsonArray arr = obj.createNestedArray("devices");
        for (int i = 0; i < deviceCount; i++) {
            JsonObject d = arr.createNestedObject();
            d["ip"] = devices[i].ip;
            d["mac"] = devices[i].mac;
            d["hostname"] = devices[i].hostname;
            d["type"] = devices[i].type;
            d["reachable"] = devices[i].reachable;
            d["response_ms"] = devices[i].responseTimeMs;
        }
    }
};

// ==== Feature 86: Bandwidth Monitor ====
class BandwidthMonitor {
private:
    unsigned long bytesSent;
    unsigned long bytesReceived;
    unsigned long startTime;
    unsigned long lastUpdateTime;

    struct BandwidthSample {
        unsigned long timestamp;
        unsigned long txBytes;
        unsigned long rxBytes;
    };
    static const int MAX_SAMPLES = 60; // 1 minute history at 1s intervals
    BandwidthSample samples[MAX_SAMPLES];
    int sampleIndex;
    int sampleCount;

    unsigned long prevTx;
    unsigned long prevRx;

public:
    BandwidthMonitor() : bytesSent(0), bytesReceived(0), startTime(0),
        lastUpdateTime(0), sampleIndex(0), sampleCount(0), prevTx(0), prevRx(0) {}

    void begin() {
        startTime = millis();
        lastUpdateTime = startTime;
        Serial.println("[BW] Bandwidth Monitor initialized");
    }

    void addTx(unsigned long bytes) { bytesSent += bytes; }
    void addRx(unsigned long bytes) { bytesReceived += bytes; }

    void takeSample() {
        unsigned long txDelta = bytesSent - prevTx;
        unsigned long rxDelta = bytesReceived - prevRx;
        prevTx = bytesSent;
        prevRx = bytesReceived;

        samples[sampleIndex] = { millis(), txDelta, rxDelta };
        sampleIndex = (sampleIndex + 1) % MAX_SAMPLES;
        if (sampleCount < MAX_SAMPLES) sampleCount++;
        lastUpdateTime = millis();
    }

    float getAvgTxBps() {
        unsigned long elapsed = (millis() - startTime) / 1000;
        return elapsed > 0 ? (float)bytesSent / elapsed : 0;
    }

    float getAvgRxBps() {
        unsigned long elapsed = (millis() - startTime) / 1000;
        return elapsed > 0 ? (float)bytesReceived / elapsed : 0;
    }

    void toJson(JsonObject& obj) {
        obj["total_tx_bytes"] = bytesSent;
        obj["total_rx_bytes"] = bytesReceived;
        obj["avg_tx_bps"] = getAvgTxBps();
        obj["avg_rx_bps"] = getAvgRxBps();
        obj["uptime_seconds"] = (millis() - startTime) / 1000;
        obj["rssi"] = WiFi.RSSI();
        obj["channel"] = WiFi.channel();
        obj["sample_count"] = sampleCount;
        JsonArray arr = obj.createNestedArray("recent");
        for (int i = 0; i < min(sampleCount, 10); i++) {
            int idx = (sampleIndex - 1 - i + MAX_SAMPLES) % MAX_SAMPLES;
            JsonObject s = arr.createNestedObject();
            s["tx"] = samples[idx].txBytes;
            s["rx"] = samples[idx].rxBytes;
        }
    }

    void loop() {
        if (millis() - lastUpdateTime > 1000) takeSample();
    }
};

#endif // SENSOR_FUSION_H
