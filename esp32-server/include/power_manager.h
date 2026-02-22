#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <esp_sleep.h>
#include <esp_wifi.h>
#include <driver/rtc_io.h>
#include "config.h"

class PowerManager {
private:
    unsigned long _lastActivityTime;
    bool _lowPowerMode;
    float _batteryVoltage;
    int _cpuFrequency;
    
    enum PowerState {
        POWER_NORMAL,
        POWER_ECO,
        POWER_LOW,
        POWER_CRITICAL
    };
    PowerState _currentState;

public:
    PowerManager() : _lastActivityTime(0), _lowPowerMode(false),
                     _batteryVoltage(4.2), _cpuFrequency(240),
                     _currentState(POWER_NORMAL) {}

    void begin() {
        _lastActivityTime = millis();
        _cpuFrequency = getCpuFrequencyMhz();
        Serial.printf("[Power] CPU: %d MHz\n", _cpuFrequency);
    }

    // Feature 25: Deep sleep
    void enterDeepSleep(int seconds = DEEP_SLEEP_TIME) {
        Serial.printf("[Power] entering deep sleep for %d sec\n", seconds);
        esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
        esp_deep_sleep_start();
    }

    // Feature 26: Light sleep
    void enterLightSleep(int seconds = LIGHT_SLEEP_TIME) {
        Serial.printf("[Power] entering light sleep for %d sec\n", seconds);
        esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
        esp_light_sleep_start();
    }

    // Feature 27: Wake on motion (GPIO wakeup)
    void enableMotionWakeup() {
        esp_sleep_enable_ext0_wakeup((gpio_num_t)PIN_PIR, 1);
        Serial.println("[Power] Motion wakeup enabled");
    }

    // CPU frequency management
    void setCPUFrequency(int mhz) {
        if (mhz == 80 || mhz == 160 || mhz == 240) {
            setCpuFrequencyMhz(mhz);
            _cpuFrequency = mhz;
            Serial.printf("[Power] CPU frequency: %d MHz\n", mhz);
        }
    }

    void setEcoMode(bool enable) {
        _lowPowerMode = enable;
        if (enable) {
            setCPUFrequency(80);
            esp_wifi_set_ps(WIFI_PS_MAX_MODEM);
            _currentState = POWER_ECO;
        } else {
            setCPUFrequency(240);
            esp_wifi_set_ps(WIFI_PS_NONE);
            _currentState = POWER_NORMAL;
        }
    }

    void updateBatteryVoltage(float voltage) {
        _batteryVoltage = voltage;
        
        if (voltage < 3.0) {
            _currentState = POWER_CRITICAL;
            setCPUFrequency(80);
        } else if (voltage < 3.3) {
            _currentState = POWER_LOW;
            setCPUFrequency(160);
        } else if (_lowPowerMode) {
            _currentState = POWER_ECO;
        } else {
            _currentState = POWER_NORMAL;
        }
    }

    void resetActivityTimer() { _lastActivityTime = millis(); }

    // Get wakeup reason
    String getWakeupReason() {
        esp_sleep_wakeup_cause_t reason = esp_sleep_get_wakeup_cause();
        switch (reason) {
            case ESP_SLEEP_WAKEUP_EXT0: return "External (GPIO)";
            case ESP_SLEEP_WAKEUP_EXT1: return "External (RTC)";
            case ESP_SLEEP_WAKEUP_TIMER: return "Timer";
            case ESP_SLEEP_WAKEUP_TOUCHPAD: return "Touchpad";
            case ESP_SLEEP_WAKEUP_ULP: return "ULP";
            default: return "Normal boot";
        }
    }

    String getStatusJSON() {
        String stateStr;
        switch (_currentState) {
            case POWER_NORMAL: stateStr = "normal"; break;
            case POWER_ECO: stateStr = "eco"; break;
            case POWER_LOW: stateStr = "low"; break;
            case POWER_CRITICAL: stateStr = "critical"; break;
        }
        
        String json = "{";
        json += "\"state\":\"" + stateStr + "\",";
        json += "\"cpu_mhz\":" + String(getCpuFrequencyMhz()) + ",";
        json += "\"battery_v\":" + String(_batteryVoltage, 2) + ",";
        json += "\"low_power\":" + String(_lowPowerMode ? "true" : "false") + ",";
        json += "\"wakeup_reason\":\"" + getWakeupReason() + "\"";
        json += "}";
        return json;
    }
};

#endif // POWER_MANAGER_H
