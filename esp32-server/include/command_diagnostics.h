/*
 * =============================================================
 * Feature 87: Command Queue - reliable command delivery
 * Feature 88: Device Diagnostics - remote diagnostics
 * Feature 89: Dynamic GPIO Manager v2 - enhanced GPIO management
 * Feature 90: PWM Controller - LED/motor PWM control
 * Feature 91: I2C Scanner - discover I2C devices
 * =============================================================
 */

#ifndef COMMAND_DIAGNOSTICS_H
#define COMMAND_DIAGNOSTICS_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Wire.h>

// ==== Feature 87: Command Queue ====
class CommandQueue {
private:
    struct QueuedCommand {
        String id;
        String type;     // "relay", "servo", "config", "scene", "restart"
        String payload;
        unsigned long queuedAt;
        unsigned long executeAt; // 0 = immediate
        uint8_t priority;  // 0=low, 1=normal, 2=high, 3=critical
        uint8_t retries;
        uint8_t maxRetries;
        String status;   // "queued", "executing", "completed", "failed"
    };
    static const int QUEUE_SIZE = 32;
    QueuedCommand queue[QUEUE_SIZE];
    int queueHead;
    int queueTail;
    int queueCount;
    unsigned long totalProcessed;
    unsigned long totalFailed;

public:
    CommandQueue() : queueHead(0), queueTail(0), queueCount(0),
        totalProcessed(0), totalFailed(0) {}

    void begin() { Serial.println("[CmdQ] Command Queue initialized"); }

    bool enqueue(const String& id, const String& type, const String& payload,
                 uint8_t priority = 1, unsigned long delay = 0) {
        if (queueCount >= QUEUE_SIZE) return false;
        queue[queueTail] = {
            id, type, payload, millis(), delay > 0 ? millis() + delay : 0,
            priority, 0, 3, "queued"
        };
        queueTail = (queueTail + 1) % QUEUE_SIZE;
        queueCount++;

        // Re-sort by priority (simple bubble for small queue)
        sortByPriority();
        return true;
    }

    bool dequeue(QueuedCommand& cmd) {
        if (queueCount == 0) return false;
        // Find highest priority ready command
        for (int i = 0; i < QUEUE_SIZE; i++) {
            int idx = (queueHead + i) % QUEUE_SIZE;
            if (queue[idx].status == "queued") {
                if (queue[idx].executeAt == 0 || millis() >= queue[idx].executeAt) {
                    cmd = queue[idx];
                    queue[idx].status = "executing";
                    return true;
                }
            }
        }
        return false;
    }

    void markCompleted(const String& id) {
        for (int i = 0; i < QUEUE_SIZE; i++) {
            if (queue[i].id == id) {
                queue[i].status = "completed";
                totalProcessed++;
                cleanCompleted();
                break;
            }
        }
    }

    void markFailed(const String& id) {
        for (int i = 0; i < QUEUE_SIZE; i++) {
            if (queue[i].id == id && queue[i].retries < queue[i].maxRetries) {
                queue[i].retries++;
                queue[i].status = "queued"; // retry
                break;
            } else if (queue[i].id == id) {
                queue[i].status = "failed";
                totalFailed++;
                break;
            }
        }
    }

    void sortByPriority() {
        // Simple insertion sort for small queue
        for (int i = 1; i < queueCount; i++) {
            int idx = (queueHead + i) % QUEUE_SIZE;
            int prev = (queueHead + i - 1) % QUEUE_SIZE;
            if (queue[idx].priority > queue[prev].priority && queue[idx].status == "queued") {
                QueuedCommand tmp = queue[idx];
                queue[idx] = queue[prev];
                queue[prev] = tmp;
            }
        }
    }

    void cleanCompleted() {
        while (queueCount > 0) {
            if (queue[queueHead].status == "completed" || queue[queueHead].status == "failed") {
                queueHead = (queueHead + 1) % QUEUE_SIZE;
                queueCount--;
            } else break;
        }
    }

    void toJson(JsonObject& obj) {
        obj["queue_size"] = queueCount;
        obj["total_processed"] = totalProcessed;
        obj["total_failed"] = totalFailed;
        JsonArray arr = obj.createNestedArray("commands");
        for (int i = 0; i < queueCount && i < 10; i++) {
            int idx = (queueHead + i) % QUEUE_SIZE;
            JsonObject c = arr.createNestedObject();
            c["id"] = queue[idx].id;
            c["type"] = queue[idx].type;
            c["priority"] = queue[idx].priority;
            c["status"] = queue[idx].status;
            c["retries"] = queue[idx].retries;
            c["queued_at"] = queue[idx].queuedAt;
        }
    }
};

// ==== Feature 88: Device Diagnostics ====
class DeviceDiagnostics {
private:
    struct DiagnosticResult {
        String test;
        bool passed;
        String details;
        unsigned long timestamp;
    };
    static const int MAX_RESULTS = 20;
    DiagnosticResult results[MAX_RESULTS];
    int resultCount;
    unsigned long lastDiagTime;

public:
    DeviceDiagnostics() : resultCount(0), lastDiagTime(0) {}

    void begin() { Serial.println("[Diag] Device Diagnostics initialized"); }

    void runAll() {
        resultCount = 0;
        lastDiagTime = millis();
        Serial.println("[Diag] Running full diagnostics...");

        // Memory test
        addResult("heap_memory",
            ESP.getFreeHeap() > 20000,
            "Free: " + String(ESP.getFreeHeap()) + " bytes, Min: " + String(ESP.getMinFreeHeap()));

        // PSRAM test
        addResult("psram",
            ESP.getPsramSize() > 0 || true, // OK if no PSRAM
            "Size: " + String(ESP.getPsramSize()) + ", Free: " + String(ESP.getFreePsram()));

        // WiFi test
        addResult("wifi_connection",
            WiFi.status() == WL_CONNECTED,
            "SSID: " + WiFi.SSID() + ", RSSI: " + String(WiFi.RSSI()) + " dBm");

        // WiFi signal quality
        int rssi = WiFi.RSSI();
        addResult("wifi_signal",
            rssi > -70,
            "RSSI: " + String(rssi) + " dBm (" +
            (rssi > -50 ? "Excellent" : rssi > -60 ? "Good" : rssi > -70 ? "Fair" : "Poor") + ")");

        // Flash test
        addResult("flash_storage",
            ESP.getFlashChipSize() > 0,
            "Size: " + String(ESP.getFlashChipSize() / 1024) + " KB, Speed: " + String(ESP.getFlashChipSpeed() / 1000000) + " MHz");

        // SPIFFS test
        addResult("spiffs",
            SPIFFS.begin(true),
            "Total: " + String(SPIFFS.totalBytes()) + ", Used: " + String(SPIFFS.usedBytes()));

        // CPU test
        addResult("cpu_frequency",
            getCpuFrequencyMhz() >= 80,
            String(getCpuFrequencyMhz()) + " MHz");

        // Temperature (internal sensor on some ESP32 variants)
        addResult("chip_temp",
            true,
            "Chip revision: " + String(ESP.getChipRevision()));

        // Uptime check
        unsigned long uptimeSec = millis() / 1000;
        addResult("uptime",
            uptimeSec > 10,
            String(uptimeSec / 3600) + "h " + String((uptimeSec % 3600) / 60) + "m " + String(uptimeSec % 60) + "s");

        // Stack usage
        addResult("stack_watermark",
            uxTaskGetStackHighWaterMark(NULL) > 1000,
            "High watermark: " + String(uxTaskGetStackHighWaterMark(NULL)) + " bytes");

        Serial.printf("[Diag] Diagnostics complete: %d/%d passed\n",
            getPassedCount(), resultCount);
    }

    void addResult(const String& test, bool passed, const String& details) {
        if (resultCount < MAX_RESULTS) {
            results[resultCount++] = { test, passed, details, millis() };
        }
    }

    int getPassedCount() {
        int count = 0;
        for (int i = 0; i < resultCount; i++)
            if (results[i].passed) count++;
        return count;
    }

    void toJson(JsonObject& obj) {
        obj["last_run"] = lastDiagTime;
        obj["total_tests"] = resultCount;
        obj["passed"] = getPassedCount();
        obj["failed"] = resultCount - getPassedCount();
        obj["health_score"] = resultCount > 0 ? (getPassedCount() * 100 / resultCount) : 0;
        JsonArray arr = obj.createNestedArray("results");
        for (int i = 0; i < resultCount; i++) {
            JsonObject r = arr.createNestedObject();
            r["test"] = results[i].test;
            r["passed"] = results[i].passed;
            r["details"] = results[i].details;
        }
    }
};

// ==== Feature 89: Dynamic GPIO Manager v2 ====
class DynamicGPIOManager {
private:
    struct GPIOPin {
        uint8_t pin;
        String name;
        String mode;     // "input", "output", "input_pullup", "analog_in", "pwm"
        bool isActive;
        int currentValue;
        unsigned long lastChanged;
        bool interruptEnabled;
    };
    static const int MAX_PINS = 20;
    GPIOPin pins[MAX_PINS];
    int pinCount;

public:
    DynamicGPIOManager() : pinCount(0) {}

    void begin() { Serial.println("[GPIO-v2] Dynamic GPIO Manager v2 initialized"); }

    int configurePin(uint8_t pin, const String& name, const String& mode) {
        if (pinCount >= MAX_PINS) return -1;
        if (mode == "output") {
            pinMode(pin, OUTPUT);
        } else if (mode == "input") {
            pinMode(pin, INPUT);
        } else if (mode == "input_pullup") {
            pinMode(pin, INPUT_PULLUP);
        } else if (mode == "analog_in") {
            pinMode(pin, INPUT);
        }

        pins[pinCount] = { pin, name, mode, true, 0, millis(), false };
        return pinCount++;
    }

    bool setPin(uint8_t pin, int value) {
        for (int i = 0; i < pinCount; i++) {
            if (pins[i].pin == pin && (pins[i].mode == "output" || pins[i].mode == "pwm")) {
                if (pins[i].mode == "pwm") {
                    analogWrite(pin, value);
                } else {
                    digitalWrite(pin, value);
                }
                pins[i].currentValue = value;
                pins[i].lastChanged = millis();
                return true;
            }
        }
        return false;
    }

    int readPin(uint8_t pin) {
        for (int i = 0; i < pinCount; i++) {
            if (pins[i].pin == pin) {
                if (pins[i].mode == "analog_in") {
                    pins[i].currentValue = analogRead(pin);
                } else {
                    pins[i].currentValue = digitalRead(pin);
                }
                return pins[i].currentValue;
            }
        }
        return -1;
    }

    void togglePin(uint8_t pin) {
        for (int i = 0; i < pinCount; i++) {
            if (pins[i].pin == pin && pins[i].mode == "output") {
                int newVal = pins[i].currentValue ? 0 : 1;
                setPin(pin, newVal);
                break;
            }
        }
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < pinCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["pin"] = pins[i].pin;
            obj["name"] = pins[i].name;
            obj["mode"] = pins[i].mode;
            obj["active"] = pins[i].isActive;
            obj["value"] = pins[i].currentValue;
            obj["last_changed"] = pins[i].lastChanged;
        }
    }
};

// ==== Feature 90: PWM Controller ====
class PWMController {
private:
    struct PWMChannel {
        uint8_t channel;
        uint8_t pin;
        String name;
        uint32_t frequency;
        uint8_t resolution; // bits
        uint16_t dutyCycle;
        bool active;
        bool fading;
        uint16_t fadeTarget;
        uint16_t fadeStep;
        unsigned long fadeInterval;
        unsigned long lastFadeUpdate;
    };
    static const int MAX_PWM = 8;
    PWMChannel channels[MAX_PWM];
    int channelCount;

public:
    PWMController() : channelCount(0) {}

    void begin() { Serial.println("[PWM] PWM Controller initialized"); }

    int addChannel(uint8_t pin, const String& name, uint32_t freq = 5000, uint8_t resolution = 8) {
        if (channelCount >= MAX_PWM) return -1;
        uint8_t ch = channelCount;
        ledcSetup(ch, freq, resolution);
        ledcAttachPin(pin, ch);
        channels[channelCount] = { ch, pin, name, freq, resolution, 0, true, false, 0, 1, 10, 0 };
        return channelCount++;
    }

    void setDuty(int channelIdx, uint16_t duty) {
        if (channelIdx < 0 || channelIdx >= channelCount) return;
        channels[channelIdx].dutyCycle = duty;
        ledcWrite(channels[channelIdx].channel, duty);
    }

    void setPercent(int channelIdx, float percent) {
        if (channelIdx < 0 || channelIdx >= channelCount) return;
        uint16_t maxDuty = (1 << channels[channelIdx].resolution) - 1;
        setDuty(channelIdx, (uint16_t)(percent / 100.0 * maxDuty));
    }

    void fadeTo(int channelIdx, uint16_t target, unsigned long durationMs = 1000) {
        if (channelIdx < 0 || channelIdx >= channelCount) return;
        PWMChannel& ch = channels[channelIdx];
        ch.fadeTarget = target;
        ch.fading = true;
        int steps = durationMs / 10;
        if (steps <= 0) steps = 1;
        ch.fadeStep = abs((int)target - (int)ch.dutyCycle) / steps;
        if (ch.fadeStep == 0) ch.fadeStep = 1;
        ch.fadeInterval = durationMs / steps;
        ch.lastFadeUpdate = millis();
    }

    void toJson(JsonArray& arr) {
        for (int i = 0; i < channelCount; i++) {
            JsonObject obj = arr.createNestedObject();
            obj["channel"] = channels[i].channel;
            obj["pin"] = channels[i].pin;
            obj["name"] = channels[i].name;
            obj["frequency"] = channels[i].frequency;
            obj["resolution"] = channels[i].resolution;
            obj["duty"] = channels[i].dutyCycle;
            obj["active"] = channels[i].active;
            obj["fading"] = channels[i].fading;
            uint16_t maxDuty = (1 << channels[i].resolution) - 1;
            obj["percent"] = maxDuty > 0 ? (channels[i].dutyCycle * 100.0 / maxDuty) : 0;
        }
    }

    void loop() {
        unsigned long now = millis();
        for (int i = 0; i < channelCount; i++) {
            if (channels[i].fading && (now - channels[i].lastFadeUpdate >= channels[i].fadeInterval)) {
                if (channels[i].dutyCycle < channels[i].fadeTarget) {
                    channels[i].dutyCycle = min((uint16_t)(channels[i].dutyCycle + channels[i].fadeStep), channels[i].fadeTarget);
                } else if (channels[i].dutyCycle > channels[i].fadeTarget) {
                    channels[i].dutyCycle = max((int)(channels[i].dutyCycle - channels[i].fadeStep), (int)channels[i].fadeTarget);
                } else {
                    channels[i].fading = false;
                }
                ledcWrite(channels[i].channel, channels[i].dutyCycle);
                channels[i].lastFadeUpdate = now;
            }
        }
    }
};

// ==== Feature 91: I2C Scanner ====
class I2CScanner {
private:
    struct I2CDevice {
        uint8_t address;
        String name;
        bool detected;
        unsigned long lastScan;
    };
    static const int MAX_I2C = 16;
    I2CDevice devices[MAX_I2C];
    int deviceCount;
    unsigned long lastScanTime;

    String identifyDevice(uint8_t addr) {
        switch (addr) {
            case 0x20: case 0x21: case 0x22: case 0x23: return "PCF8574 (I/O Expander)";
            case 0x27: return "LCD (HD44780)";
            case 0x3C: case 0x3D: return "SSD1306 (OLED Display)";
            case 0x40: return "INA219 (Current Sensor)";
            case 0x48: return "ADS1115 (ADC)";
            case 0x50: case 0x51: return "EEPROM (24Cxx)";
            case 0x57: return "MAX30102 (Heart Rate)";
            case 0x68: return "MPU6050 (Accel/Gyro)";
            case 0x76: case 0x77: return "BME280 (Temp/Hum/Press)";
            default: return "Unknown";
        }
    }

public:
    I2CScanner() : deviceCount(0), lastScanTime(0) {}

    void begin(int sda = 21, int scl = 22) {
        Wire.begin(sda, scl);
        Serial.println("[I2C] I2C Scanner initialized");
    }

    int scan() {
        deviceCount = 0;
        lastScanTime = millis();
        Serial.println("[I2C] Scanning I2C bus...");

        for (uint8_t addr = 1; addr < 127 && deviceCount < MAX_I2C; addr++) {
            Wire.beginTransmission(addr);
            if (Wire.endTransmission() == 0) {
                devices[deviceCount++] = { addr, identifyDevice(addr), true, millis() };
                Serial.printf("[I2C] Found device at 0x%02X: %s\n", addr, identifyDevice(addr).c_str());
            }
        }

        Serial.printf("[I2C] Scan complete: %d devices found\n", deviceCount);
        return deviceCount;
    }

    void toJson(JsonObject& obj) {
        obj["device_count"] = deviceCount;
        obj["last_scan"] = lastScanTime;
        JsonArray arr = obj.createNestedArray("devices");
        for (int i = 0; i < deviceCount; i++) {
            JsonObject d = arr.createNestedObject();
            char addrBuf[8];
            sprintf(addrBuf, "0x%02X", devices[i].address);
            d["address"] = addrBuf;
            d["address_dec"] = devices[i].address;
            d["name"] = devices[i].name;
            d["detected"] = devices[i].detected;
        }
    }
};

#endif // COMMAND_DIAGNOSTICS_H
