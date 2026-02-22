#ifndef SYSTEM_MONITOR_H
#define SYSTEM_MONITOR_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_system.h>
#include "config.h"

class SystemMonitor {
private:
    unsigned long _bootTime;
    unsigned long _lastHealthCheck;
    int _errorCount;
    int _warningCount;
    float _cpuLoad;
    unsigned long _loopCounter;
    unsigned long _lastLoopCount;
    unsigned long _lastLoopTime;
    
    struct LogEntry {
        unsigned long timestamp;
        String level;
        String message;
    };
    LogEntry _logs[MAX_LOG_ENTRIES];
    int _logIndex;
    int _logCount;

public:
    SystemMonitor() : _bootTime(0), _lastHealthCheck(0), _errorCount(0),
                      _warningCount(0), _cpuLoad(0), _loopCounter(0),
                      _lastLoopCount(0), _lastLoopTime(0), _logIndex(0), _logCount(0) {}

    void begin() {
        _bootTime = millis();
        Serial.println("[System] Monitor initialized");
        log("INFO", "System monitor started");
    }

    // Feature 46: System health monitoring
    void checkHealth() {
        unsigned long now = millis();
        if (now - _lastHealthCheck < HEALTH_CHECK_INTERVAL) return;
        _lastHealthCheck = now;

        // Calculate loop rate (CPU load indicator)
        unsigned long loops = _loopCounter - _lastLoopCount;
        unsigned long elapsed = now - _lastLoopTime;
        if (elapsed > 0) {
            _cpuLoad = 100.0 - (loops / (float)elapsed * 10.0);
            _cpuLoad = constrain(_cpuLoad, 0, 100);
        }
        _lastLoopCount = _loopCounter;
        _lastLoopTime = now;

        // Memory check
        if (ESP.getFreeHeap() < 10000) {
            log("WARN", "Low memory: " + String(ESP.getFreeHeap()) + " bytes");
            _warningCount++;
        }
    }

    void incrementLoop() { _loopCounter++; }

    // Feature 50: Error logging
    void log(const String& level, const String& message) {
        _logs[_logIndex].timestamp = millis();
        _logs[_logIndex].level = level;
        _logs[_logIndex].message = message;
        _logIndex = (_logIndex + 1) % MAX_LOG_ENTRIES;
        if (_logCount < MAX_LOG_ENTRIES) _logCount++;
        
        Serial.printf("[%s] %s\n", level.c_str(), message.c_str());
    }

    // Feature 47: Memory usage tracking
    String getMemoryInfo() {
        String json = "{";
        json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
        json += "\"min_free_heap\":" + String(ESP.getMinFreeHeap()) + ",";
        json += "\"max_alloc_heap\":" + String(ESP.getMaxAllocHeap()) + ",";
        json += "\"total_psram\":" + String(ESP.getPsramSize()) + ",";
        json += "\"free_psram\":" + String(ESP.getFreePsram()) + ",";
        json += "\"heap_usage_pct\":" + String(100.0 - (ESP.getFreeHeap() * 100.0 / 320000), 1);
        json += "}";
        return json;
    }

    // Feature 48: CPU load monitoring
    float getCPULoad() { return _cpuLoad; }

    // Feature 49: Uptime tracking
    unsigned long getUptime() { return (millis() - _bootTime) / 1000; }
    
    String getUptimeFormatted() {
        unsigned long secs = getUptime();
        int days = secs / 86400;
        int hours = (secs % 86400) / 3600;
        int mins = (secs % 3600) / 60;
        int s = secs % 60;
        
        char buf[32];
        snprintf(buf, sizeof(buf), "%dd %02dh %02dm %02ds", days, hours, mins, s);
        return String(buf);
    }

    // Get recent logs
    String getLogsJSON(int count = 20) {
        String json = "[";
        int start = _logCount < MAX_LOG_ENTRIES ? 0 : _logIndex;
        int total = min(count, _logCount);
        
        for (int i = 0; i < total; i++) {
            int idx = (start + _logCount - total + i) % MAX_LOG_ENTRIES;
            if (i > 0) json += ",";
            json += "{\"ts\":" + String(_logs[idx].timestamp) + ",";
            json += "\"level\":\"" + _logs[idx].level + "\",";
            json += "\"msg\":\"" + _logs[idx].message + "\"}";
        }
        json += "]";
        return json;
    }

    // Full system status
    String getStatusJSON() {
        String json = "{";
        json += "\"device\":\"" + String(DEVICE_NAME) + "\",";
        json += "\"firmware\":\"" + String(FIRMWARE_VERSION) + "\",";
        json += "\"uptime\":\"" + getUptimeFormatted() + "\",";
        json += "\"uptime_secs\":" + String(getUptime()) + ",";
        json += "\"cpu_mhz\":" + String(getCpuFrequencyMhz()) + ",";
        json += "\"cpu_load\":" + String(_cpuLoad, 1) + ",";
        json += "\"chip\":\"" + String(ESP.getChipModel()) + "\",";
        json += "\"cores\":" + String(ESP.getChipCores()) + ",";
        json += "\"revision\":" + String(ESP.getChipRevision()) + ",";
        json += "\"sdk\":\"" + String(ESP.getSdkVersion()) + "\",";
        json += "\"flash_size\":" + String(ESP.getFlashChipSize()) + ",";
        json += "\"sketch_size\":" + String(ESP.getSketchSize()) + ",";
        json += "\"free_sketch\":" + String(ESP.getFreeSketchSpace()) + ",";
        json += "\"free_heap\":" + String(ESP.getFreeHeap()) + ",";
        json += "\"min_heap\":" + String(ESP.getMinFreeHeap()) + ",";
        json += "\"psram\":" + String(ESP.getPsramSize()) + ",";
        json += "\"free_psram\":" + String(ESP.getFreePsram()) + ",";
        json += "\"loop_rate\":" + String(_loopCounter) + ",";
        json += "\"errors\":" + String(_errorCount) + ",";
        json += "\"warnings\":" + String(_warningCount) + ",";
        json += "\"temperature\":" + String(temperatureRead(), 1);
        json += "}";
        return json;
    }
};

#endif // SYSTEM_MONITOR_H
