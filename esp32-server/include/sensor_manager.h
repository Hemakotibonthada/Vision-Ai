#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <DHT.h>
#include <ArduinoJson.h>
#include "config.h"

class SensorManager {
private:
    DHT _dht;
    float _temperature;
    float _humidity;
    float _heatIndex;
    bool _motionDetected;
    float _distance;
    int _lightLevel;
    float _voltage;       // Mains/supply voltage reading
    float _current;       // Current reading (ACS712)
    float _power;         // Calculated power (V * I)
    float _batteryVoltage;
    unsigned long _lastReadTime;
    unsigned long _lastMotionTime;
    bool _sensorsReady;
    
    // Sensor statistics
    float _tempMin, _tempMax, _tempAvg;
    float _humMin, _humMax, _humAvg;
    int _motionCount;
    int _readCount;
    float _tempSum, _humSum;

    // Alert thresholds
    float _tempAlertHigh;
    float _tempAlertLow;
    float _humAlertHigh;
    float _voltageAlertHigh;
    float _voltageAlertLow;
    float _currentAlertHigh;

public:
    SensorManager() : _dht(PIN_DHT, DHT_TYPE), _temperature(0), _humidity(0),
                      _heatIndex(0), _motionDetected(false), _distance(0),
                      _lightLevel(0), _voltage(0), _current(0), _power(0),
                      _batteryVoltage(0), _lastReadTime(0),
                      _lastMotionTime(0), _sensorsReady(false),
                      _tempMin(999), _tempMax(-999), _tempAvg(0),
                      _humMin(999), _humMax(-999), _humAvg(0),
                      _motionCount(0), _readCount(0), _tempSum(0), _humSum(0),
                      _tempAlertHigh(45.0), _tempAlertLow(5.0),
                      _humAlertHigh(85.0),
                      _voltageAlertHigh(260.0), _voltageAlertLow(180.0),
                      _currentAlertHigh(10.0) {}

    void begin() {
        // DHT11 sensor
        _dht.begin();
        Serial.println("[Sensors] DHT11 initialized on pin " + String(PIN_DHT));
        
        // PIR motion sensor
        pinMode(PIN_PIR, INPUT);
        
        // Ultrasonic sensor
        pinMode(PIN_TRIGGER, OUTPUT);
        pinMode(PIN_ECHO, INPUT);
        
        // LDR
        pinMode(PIN_LDR, INPUT);
        
        // Voltage sensor ADC
        pinMode(PIN_VOLTAGE_SENSOR, INPUT);
        
        // Current sensor ADC
        pinMode(PIN_CURRENT_SENSOR, INPUT);
        
        _sensorsReady = true;
        Serial.println("[Sensors] Initialized (DHT11 + Voltage + Current)");
    }

    // ---- Temperature & Humidity (DHT11) ----
    float readTemperature() {
        float t = _dht.readTemperature();
        if (!isnan(t)) {
            _temperature = t;
            if (t < _tempMin) _tempMin = t;
            if (t > _tempMax) _tempMax = t;
            _tempSum += t;
        }
        return _temperature;
    }

    float readHumidity() {
        float h = _dht.readHumidity();
        if (!isnan(h)) {
            _humidity = h;
            if (h < _humMin) _humMin = h;
            if (h > _humMax) _humMax = h;
            _humSum += h;
        }
        return _humidity;
    }

    float readHeatIndex() {
        _heatIndex = _dht.computeHeatIndex(_temperature, _humidity, false);
        return _heatIndex;
    }

    // ---- PIR Motion ----
    bool readMotion() {
        bool motion = digitalRead(PIN_PIR) == HIGH;
        
        if (motion && !_motionDetected) {
            unsigned long now = millis();
            if (now - _lastMotionTime > MOTION_DEBOUNCE) {
                _motionDetected = true;
                _lastMotionTime = now;
                _motionCount++;
                Serial.println("[Sensors] Motion detected!");
            }
        } else if (!motion) {
            _motionDetected = false;
        }
        
        return _motionDetected;
    }

    // ---- Ultrasonic Distance ----
    float readDistance() {
        digitalWrite(PIN_TRIGGER, LOW);
        delayMicroseconds(2);
        digitalWrite(PIN_TRIGGER, HIGH);
        delayMicroseconds(10);
        digitalWrite(PIN_TRIGGER, LOW);
        
        long duration = pulseIn(PIN_ECHO, HIGH, ULTRASONIC_TIMEOUT);
        _distance = duration * 0.034 / 2.0;
        
        return _distance;
    }

    // ---- Light Sensor ----
    int readLight() {
        _lightLevel = analogRead(PIN_LDR);
        return _lightLevel;
    }

    bool isDark() {
        return _lightLevel < LDR_THRESHOLD;
    }

    // ============================================
    // Voltage Reading (via voltage divider)
    // ============================================
    float readVoltage() {
        // Read multiple samples and average for stability
        long sum = 0;
        const int samples = 20;
        for (int i = 0; i < samples; i++) {
            sum += analogRead(PIN_VOLTAGE_SENSOR);
            delayMicroseconds(100);
        }
        float avgRaw = (float)sum / samples;
        
        // Convert ADC value to actual voltage
        // V_adc = raw * Vref / ADC_resolution
        // V_actual = V_adc * (R1 + R2) / R2
        float adcVoltage = avgRaw * ADC_VREF / ADC_RESOLUTION;
        _voltage = adcVoltage * (VOLTAGE_DIVIDER_R1 + VOLTAGE_DIVIDER_R2) / VOLTAGE_DIVIDER_R2;
        
        return _voltage;
    }

    // ============================================
    // Current Reading (ACS712 sensor)
    // ============================================
    float readCurrent() {
        // Read multiple samples and average
        long sum = 0;
        const int samples = 50;
        for (int i = 0; i < samples; i++) {
            sum += analogRead(PIN_CURRENT_SENSOR);
            delayMicroseconds(100);
        }
        float avgRaw = (float)sum / samples;
        
        // Convert to voltage
        float sensorVoltage = avgRaw * ADC_VREF / ADC_RESOLUTION;
        
        // ACS712: Vout = Vcc/2 + (Sensitivity * I)
        // I = (Vout - Vcc/2) / Sensitivity
        _current = abs((sensorVoltage - ACS712_OFFSET) / ACS712_SENSITIVITY);
        
        return _current;
    }

    // ============================================
    // Power Calculation
    // ============================================
    float readPower() {
        _power = _voltage * _current;
        return _power;
    }

    // ---- Battery Voltage ----
    float readBatteryVoltage() {
        int raw = analogRead(PIN_VOLTAGE_SENSOR);
        _batteryVoltage = (raw / ADC_RESOLUTION) * ADC_VREF * 2; // Voltage divider factor
        return _batteryVoltage;
    }

    int getBatteryPercentage() {
        float voltage = readBatteryVoltage();
        int percentage = (int)((voltage - 3.0) / (4.2 - 3.0) * 100);
        return constrain(percentage, 0, 100);
    }

    // ============================================
    // Alert Checks
    // ============================================
    bool isTemperatureAlert() {
        return _temperature > _tempAlertHigh || _temperature < _tempAlertLow;
    }

    bool isHumidityAlert() {
        return _humidity > _humAlertHigh;
    }

    bool isVoltageAlert() {
        return _voltage > _voltageAlertHigh || _voltage < _voltageAlertLow;
    }

    bool isCurrentAlert() {
        return _current > _currentAlertHigh;
    }

    void setAlertThresholds(float tempHigh, float tempLow, float humHigh, 
                             float voltHigh, float voltLow, float currHigh) {
        _tempAlertHigh = tempHigh;
        _tempAlertLow = tempLow;
        _humAlertHigh = humHigh;
        _voltageAlertHigh = voltHigh;
        _voltageAlertLow = voltLow;
        _currentAlertHigh = currHigh;
    }

    // ============================================
    // Read All Sensors
    // ============================================
    void readAll() {
        unsigned long now = millis();
        if (now - _lastReadTime >= SENSOR_READ_INTERVAL) {
            _lastReadTime = now;
            _readCount++;
            
            readTemperature();
            readHumidity();
            readHeatIndex();
            readDistance();
            readLight();
            readVoltage();
            readCurrent();
            readPower();
        }
        readMotion(); // Always check motion
    }

    // ============================================
    // JSON Output (all sensor data)
    // ============================================
    String getDataJSON() {
        StaticJsonDocument<1536> doc;
        
        // DHT11 data
        doc["temperature"] = _temperature;
        doc["humidity"] = _humidity;
        doc["heat_index"] = _heatIndex;
        
        // Motion
        doc["motion"] = _motionDetected;
        
        // Distance
        doc["distance"] = _distance;
        
        // Light
        doc["light"] = _lightLevel;
        doc["is_dark"] = isDark();
        
        // Voltage & Current
        JsonObject power = doc.createNestedObject("power");
        power["voltage"] = _voltage;
        power["current"] = _current;
        power["watts"] = _power;
        
        // Alerts
        JsonObject alerts = doc.createNestedObject("alerts");
        alerts["temperature"] = isTemperatureAlert();
        alerts["humidity"] = isHumidityAlert();
        alerts["voltage"] = isVoltageAlert();
        alerts["current"] = isCurrentAlert();
        
        // Statistics
        JsonObject stats = doc.createNestedObject("stats");
        stats["temp_min"] = _tempMin;
        stats["temp_max"] = _tempMax;
        stats["temp_avg"] = _readCount > 0 ? _tempSum / _readCount : 0;
        stats["hum_min"] = _humMin;
        stats["hum_max"] = _humMax;
        stats["hum_avg"] = _readCount > 0 ? _humSum / _readCount : 0;
        stats["motion_count"] = _motionCount;
        stats["read_count"] = _readCount;
        
        doc["timestamp"] = millis();
        
        String result;
        serializeJson(doc, result);
        return result;
    }

    // Getters
    float getTemperature() { return _temperature; }
    float getHumidity() { return _humidity; }
    bool getMotion() { return _motionDetected; }
    float getDistance() { return _distance; }
    int getLight() { return _lightLevel; }
    int getMotionCount() { return _motionCount; }
    float getVoltage() { return _voltage; }
    float getCurrent() { return _current; }
    float getPower() { return _power; }

    void resetStats() {
        _tempMin = 999; _tempMax = -999; _tempSum = 0;
        _humMin = 999; _humMax = -999; _humSum = 0;
        _motionCount = 0; _readCount = 0;
    }
};

#endif // SENSOR_MANAGER_H
