#ifndef GPIO_MANAGER_H
#define GPIO_MANAGER_H

#include <Arduino.h>
#include <EEPROM.h>
#include "config.h"

class GPIOManager {
private:
    // 8-Relay states
    bool _relayStates[RELAY_COUNT];
    bool _buzzerState;
    bool _statusLedState;

    // PWM channels
    static const int LEDC_BUZZER_CHANNEL = 0;
    static const int LEDC_FREQ = 5000;
    static const int LEDC_RESOLUTION = 8;

    // Button state
    volatile bool _buttonPressed;
    unsigned long _buttonLastPress;
    static const unsigned long DEBOUNCE_TIME = 200;
    int _currentRelayToggleIndex; // which relay the button cycles through

    static GPIOManager* _instance;

    static void IRAM_ATTR buttonISR() {
        if (_instance) {
            unsigned long now = millis();
            if (now - _instance->_buttonLastPress > DEBOUNCE_TIME) {
                _instance->_buttonPressed = true;
                _instance->_buttonLastPress = now;
            }
        }
    }

public:
    GPIOManager() : _buzzerState(false), _statusLedState(false),
                    _buttonPressed(false), _buttonLastPress(0),
                    _currentRelayToggleIndex(0) {
        _instance = this;
        for (int i = 0; i < RELAY_COUNT; i++) {
            _relayStates[i] = false;
        }
    }

    void begin() {
        // Initialize all 8 relay pins
        for (int i = 0; i < RELAY_COUNT; i++) {
            pinMode(RELAY_PINS[i], OUTPUT);
            digitalWrite(RELAY_PINS[i], LOW);
        }
        Serial.printf("[GPIO] %d Relay pins initialized\n", RELAY_COUNT);

        // Status LED
        pinMode(PIN_STATUS_LED, OUTPUT);
        digitalWrite(PIN_STATUS_LED, LOW);

        // Buzzer (PWM)
        ledcSetup(LEDC_BUZZER_CHANNEL, 2000, LEDC_RESOLUTION);
        ledcAttachPin(PIN_BUZZER, LEDC_BUZZER_CHANNEL);

        // Button with interrupt
        pinMode(PIN_BUTTON, INPUT_PULLUP);
        attachInterrupt(digitalPinToInterrupt(PIN_BUTTON), buttonISR, FALLING);

        // Load last relay states from EEPROM
        loadRelayStatesFromEEPROM();

        Serial.println("[GPIO] Initialized with EEPROM restore");
    }

    // ============================================
    // EEPROM Relay State Persistence
    // ============================================
    void saveRelayStatesToEEPROM() {
        for (int i = 0; i < RELAY_COUNT; i++) {
            EEPROM.write(EEPROM_RELAY_ADDR + i, _relayStates[i] ? 1 : 0);
        }
        EEPROM.commit();
        Serial.println("[EEPROM] Relay states saved");
    }

    void loadRelayStatesFromEEPROM() {
        Serial.println("[EEPROM] Loading relay states...");
        for (int i = 0; i < RELAY_COUNT; i++) {
            uint8_t val = EEPROM.read(EEPROM_RELAY_ADDR + i);
            // Only treat as ON if value is exactly 1 (protect against uninitialized EEPROM)
            _relayStates[i] = (val == 1);
            digitalWrite(RELAY_PINS[i], _relayStates[i] ? HIGH : LOW);
            if (_relayStates[i]) {
                Serial.printf("[EEPROM] Relay %d (%s): ON (restored)\n", i + 1, ROOM_NAMES[i]);
            }
        }
    }

    // ============================================
    // 8-Relay Control with Room Mapping
    // ============================================
    void setRelay(int relay, bool state) {
        // relay is 1-indexed (1 to RELAY_COUNT)
        if (relay < 1 || relay > RELAY_COUNT) {
            Serial.printf("[GPIO] Invalid relay number: %d\n", relay);
            return;
        }
        int idx = relay - 1;
        _relayStates[idx] = state;
        digitalWrite(RELAY_PINS[idx], state ? HIGH : LOW);
        Serial.printf("[GPIO] Relay %d (%s): %s\n", relay, ROOM_NAMES[idx], state ? "ON" : "OFF");

        // Save to EEPROM
        saveRelayStatesToEEPROM();
    }

    void setRelayByRoom(const char* roomName, bool state) {
        for (int i = 0; i < RELAY_COUNT; i++) {
            if (strcasecmp(ROOM_NAMES[i], roomName) == 0) {
                setRelay(i + 1, state);
                return;
            }
        }
        Serial.printf("[GPIO] Room not found: %s\n", roomName);
    }

    void toggleRelay(int relay) {
        if (relay >= 1 && relay <= RELAY_COUNT) {
            setRelay(relay, !_relayStates[relay - 1]);
        }
    }

    void setAllRelays(bool state) {
        for (int i = 0; i < RELAY_COUNT; i++) {
            _relayStates[i] = state;
            digitalWrite(RELAY_PINS[i], state ? HIGH : LOW);
        }
        saveRelayStatesToEEPROM();
        Serial.printf("[GPIO] All relays: %s\n", state ? "ON" : "OFF");
    }

    bool getRelayState(int relay) {
        if (relay >= 1 && relay <= RELAY_COUNT) {
            return _relayStates[relay - 1];
        }
        return false;
    }

    const char* getRelayRoom(int relay) {
        if (relay >= 1 && relay <= RELAY_COUNT) {
            return ROOM_NAMES[relay - 1];
        }
        return "Unknown";
    }

    // ============================================
    // Status LED Control
    // ============================================
    void setStatusLED(bool state) {
        _statusLedState = state;
        digitalWrite(PIN_STATUS_LED, state ? HIGH : LOW);
    }

    void blinkStatusLED(int times = 3, int delayMs = 200) {
        for (int i = 0; i < times; i++) {
            setStatusLED(true);
            delay(delayMs);
            setStatusLED(false);
            delay(delayMs);
        }
    }

    // Status indicator patterns using status LED + buzzer
    void showStatus(const char* status) {
        if (strcmp(status, "ok") == 0) {
            setStatusLED(true);
        } else if (strcmp(status, "warning") == 0) {
            blinkStatusLED(2, 300);
        } else if (strcmp(status, "error") == 0) {
            blinkStatusLED(5, 100);
        } else if (strcmp(status, "connecting") == 0) {
            blinkStatusLED(1, 500);
        } else if (strcmp(status, "processing") == 0) {
            blinkStatusLED(3, 150);
        }
    }

    // ============================================
    // Buzzer Control
    // ============================================
    void buzz(int frequency = 2000, int durationMs = 200) {
        ledcWriteTone(LEDC_BUZZER_CHANNEL, frequency);
        delay(durationMs);
        ledcWriteTone(LEDC_BUZZER_CHANNEL, 0);
    }

    void buzzPattern(const char* pattern) {
        if (strcmp(pattern, "alert") == 0) {
            // Urgent alert: 3 fast high-pitch beeps
            for (int i = 0; i < 3; i++) {
                buzz(3000, 100); delay(100);
            }
        } else if (strcmp(pattern, "success") == 0) {
            // Rising tone
            buzz(1000, 100); delay(50);
            buzz(1500, 100); delay(50);
            buzz(2000, 200);
        } else if (strcmp(pattern, "error") == 0) {
            // Long low tone
            buzz(500, 500);
        } else if (strcmp(pattern, "motion") == 0) {
            // Double quick beep
            buzz(2500, 50); delay(50);
            buzz(2500, 50);
        } else if (strcmp(pattern, "temperature") == 0) {
            // High temp warning: alternating tones
            buzz(2000, 150); delay(100);
            buzz(3000, 150); delay(100);
            buzz(2000, 150);
        } else if (strcmp(pattern, "voltage") == 0) {
            // Voltage alert: descending tone
            buzz(3000, 100); delay(50);
            buzz(2000, 100); delay(50);
            buzz(1000, 200);
        } else if (strcmp(pattern, "relay") == 0) {
            // Short click sound for relay toggle
            buzz(1500, 50);
        }
    }

    void setBuzzer(bool state) {
        _buzzerState = state;
        ledcWriteTone(LEDC_BUZZER_CHANNEL, state ? 2000 : 0);
    }

    // ============================================
    // Button Handling (single button cycles relays)
    // ============================================
    bool isButtonPressed() {
        if (_buttonPressed) {
            _buttonPressed = false;
            return true;
        }
        return false;
    }

    // Get which relay index the button should toggle next
    int getButtonRelayIndex() {
        int idx = _currentRelayToggleIndex;
        _currentRelayToggleIndex = (_currentRelayToggleIndex + 1) % RELAY_COUNT;
        return idx + 1; // return 1-indexed
    }

    // ============================================
    // EEPROM Helper: Save/Load credentials & scenes
    // ============================================
    void saveUsername(const char* username) {
        for (int i = 0; i < 32; i++) {
            EEPROM.write(EEPROM_USERNAME_ADDR + i, i < strlen(username) ? username[i] : 0);
        }
        EEPROM.commit();
    }

    String loadUsername() {
        char buf[33] = {0};
        for (int i = 0; i < 32; i++) buf[i] = EEPROM.read(EEPROM_USERNAME_ADDR + i);
        buf[32] = '\0';
        return String(buf);
    }

    void savePassword(const char* password) {
        for (int i = 0; i < 32; i++) {
            EEPROM.write(EEPROM_PASSWORD_ADDR + i, i < strlen(password) ? password[i] : 0);
        }
        EEPROM.commit();
    }

    String loadPassword() {
        char buf[33] = {0};
        for (int i = 0; i < 32; i++) buf[i] = EEPROM.read(EEPROM_PASSWORD_ADDR + i);
        buf[32] = '\0';
        return String(buf);
    }

    void saveBirthday(const char* birthday) {
        for (int i = 0; i < 32; i++) {
            EEPROM.write(EEPROM_BIRTHDAY_ADDR + i, i < strlen(birthday) ? birthday[i] : 0);
        }
        EEPROM.commit();
    }

    String loadBirthday() {
        char buf[33] = {0};
        for (int i = 0; i < 32; i++) buf[i] = EEPROM.read(EEPROM_BIRTHDAY_ADDR + i);
        buf[32] = '\0';
        return String(buf);
    }

    // Save a scene (all 8 relay states as a named preset)
    void saveScene(uint8_t sceneIndex, const bool states[RELAY_COUNT]) {
        int addr = EEPROM_SCENE_ADDR + (sceneIndex * RELAY_COUNT);
        for (int i = 0; i < RELAY_COUNT; i++) {
            EEPROM.write(addr + i, states[i] ? 1 : 0);
        }
        EEPROM.commit();
        Serial.printf("[EEPROM] Scene %d saved\n", sceneIndex);
    }

    void loadScene(uint8_t sceneIndex) {
        int addr = EEPROM_SCENE_ADDR + (sceneIndex * RELAY_COUNT);
        for (int i = 0; i < RELAY_COUNT; i++) {
            uint8_t val = EEPROM.read(addr + i);
            setRelay(i + 1, val == 1);
        }
        Serial.printf("[EEPROM] Scene %d loaded\n", sceneIndex);
    }

    // ============================================
    // ADC/DAC & Digital Pin Control
    // ============================================
    int readAnalog(int pin) { return analogRead(pin); }
    void writeAnalog(int pin, int value) { dacWrite(pin, value); }
    void setPin(int pin, bool state) { digitalWrite(pin, state ? HIGH : LOW); }
    bool readPin(int pin) { return digitalRead(pin) == HIGH; }
    void setPinMode(int pin, int mode) { pinMode(pin, mode); }

    // ============================================
    // Status JSON (all 8 relays with room names)
    // ============================================
    String getStatusJSON() {
        StaticJsonDocument<1024> doc;

        // Relay states with room mapping
        JsonArray relays = doc.createNestedArray("relays");
        for (int i = 0; i < RELAY_COUNT; i++) {
            JsonObject r = relays.createNestedObject();
            r["id"] = i + 1;
            r["room"] = ROOM_NAMES[i];
            r["pin"] = RELAY_PINS[i];
            r["state"] = _relayStates[i];
        }

        doc["buzzer"] = _buzzerState;
        doc["status_led"] = _statusLedState;

        String result;
        serializeJson(doc, result);
        return result;
    }
};

GPIOManager* GPIOManager::_instance = nullptr;

#endif // GPIO_MANAGER_H
