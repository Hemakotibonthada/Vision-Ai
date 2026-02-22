#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>
#include <ESPmDNS.h>
#include "config.h"

class WiFiManager {
private:
    bool _isConnected;
    bool _isAPMode;
    bool _isDualMode;
    int _retryCount;
    unsigned long _lastReconnectAttempt;
    int _currentChannel;
    String _hostname;
    
    static void WiFiEvent(WiFiEvent_t event) {
        switch (event) {
            case ARDUINO_EVENT_WIFI_STA_CONNECTED:
                Serial.println("[WiFi] Connected to AP");
                break;
            case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
                Serial.println("[WiFi] Disconnected from AP");
                break;
            case ARDUINO_EVENT_WIFI_STA_GOT_IP:
                Serial.printf("[WiFi] Got IP: %s\n", WiFi.localIP().toString().c_str());
                break;
            case ARDUINO_EVENT_WIFI_AP_STACONNECTED:
                Serial.println("[WiFi] Client connected to AP");
                break;
            case ARDUINO_EVENT_WIFI_AP_STADISCONNECTED:
                Serial.println("[WiFi] Client disconnected from AP");
                break;
            default:
                break;
        }
    }

public:
    WiFiManager() : _isConnected(false), _isAPMode(false), _isDualMode(false),
                    _retryCount(0), _lastReconnectAttempt(0), _currentChannel(WIFI_AP_CHANNEL),
                    _hostname(DEVICE_NAME) {}

    // Feature 1: WiFi Station Mode
    bool connectSTA(const char* ssid = WIFI_SSID, const char* password = WIFI_PASSWORD) {
        Serial.printf("[WiFi] Connecting to %s...\n", ssid);
        WiFi.mode(WIFI_STA);
        WiFi.setHostname(_hostname.c_str());
        WiFi.onEvent(WiFiEvent);
        WiFi.begin(ssid, password);
        
        unsigned long startTime = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_CONNECT_TIMEOUT) {
            delay(500);
            Serial.print(".");
        }
        
        if (WiFi.status() == WL_CONNECTED) {
            _isConnected = true;
            _retryCount = 0;
            Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
            Serial.printf("[WiFi] Signal: %d dBm, Channel: %d\n", WiFi.RSSI(), WiFi.channel());
            return true;
        }
        
        Serial.println("\n[WiFi] Connection failed!");
        return false;
    }

    // Feature 2: WiFi Access Point Mode
    bool startAP(const char* ssid = WIFI_AP_SSID, const char* password = WIFI_AP_PASSWORD) {
        Serial.printf("[WiFi] Starting AP: %s\n", ssid);
        WiFi.mode(WIFI_AP);
        WiFi.softAPConfig(IPAddress(192,168,4,1), IPAddress(192,168,4,1), IPAddress(255,255,255,0));
        bool result = WiFi.softAP(ssid, password, _currentChannel, false, WIFI_AP_MAX_CONN);
        
        if (result) {
            _isAPMode = true;
            Serial.printf("[WiFi] AP started! IP: %s\n", WiFi.softAPIP().toString().c_str());
        }
        return result;
    }

    // Feature 3: Dual WiFi Mode (AP+STA)
    bool startDualMode() {
        Serial.println("[WiFi] Starting dual mode (AP+STA)...");
        WiFi.mode(WIFI_AP_STA);
        WiFi.onEvent(WiFiEvent);
        
        // Start AP
        WiFi.softAPConfig(IPAddress(192,168,4,1), IPAddress(192,168,4,1), IPAddress(255,255,255,0));
        WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASSWORD, _currentChannel, false, WIFI_AP_MAX_CONN);
        
        // Connect to STA
        WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
        
        unsigned long startTime = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_CONNECT_TIMEOUT) {
            delay(500);
            Serial.print(".");
        }
        
        _isDualMode = true;
        _isAPMode = true;
        _isConnected = (WiFi.status() == WL_CONNECTED);
        
        Serial.printf("\n[WiFi] Dual mode active\n");
        Serial.printf("[WiFi] STA IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WiFi] AP IP: %s\n", WiFi.softAPIP().toString().c_str());
        
        return _isConnected;
    }

    // Feature 4: WiFi Signal Strength Monitoring
    int getSignalStrength() { return WiFi.RSSI(); }
    
    String getSignalQuality() {
        int rssi = WiFi.RSSI();
        if (rssi > -50) return "Excellent";
        if (rssi > -60) return "Good";
        if (rssi > -70) return "Fair";
        if (rssi > -80) return "Weak";
        return "Very Weak";
    }

    // Feature 5: WiFi Channel Scanning
    String scanNetworks() {
        int n = WiFi.scanNetworks();
        String result = "[";
        for (int i = 0; i < n; i++) {
            if (i > 0) result += ",";
            result += "{\"ssid\":\"" + WiFi.SSID(i) + "\",";
            result += "\"rssi\":" + String(WiFi.RSSI(i)) + ",";
            result += "\"channel\":" + String(WiFi.channel(i)) + ",";
            result += "\"encryption\":" + String(WiFi.encryptionType(i)) + "}";
        }
        result += "]";
        WiFi.scanDelete();
        return result;
    }

    // Feature 19: mDNS Service Discovery
    bool startMDNS(const char* hostname = "vision-server") {
        if (MDNS.begin(hostname)) {
            MDNS.addService("http", "tcp", HTTP_PORT);
            MDNS.addService("ws", "tcp", WS_PORT);
            MDNS.addService("mqtt", "tcp", MQTT_PORT);
            Serial.printf("[mDNS] Started: %s.local\n", hostname);
            return true;
        }
        return false;
    }

    // Auto-reconnect handler
    void handleReconnect() {
        if (!_isConnected && WiFi.status() != WL_CONNECTED) {
            unsigned long now = millis();
            if (now - _lastReconnectAttempt > WIFI_RECONNECT_INTERVAL) {
                _lastReconnectAttempt = now;
                _retryCount++;
                
                if (_retryCount > WIFI_MAX_RETRIES) {
                    Serial.println("[WiFi] Max retries reached, starting AP mode");
                    startAP();
                    return;
                }
                
                Serial.printf("[WiFi] Reconnecting... (attempt %d/%d)\n", _retryCount, WIFI_MAX_RETRIES);
                WiFi.reconnect();
            }
        } else if (WiFi.status() == WL_CONNECTED && !_isConnected) {
            _isConnected = true;
            _retryCount = 0;
        }
    }

    // Getters
    bool isConnected() { return WiFi.status() == WL_CONNECTED; }
    bool isAPMode() { return _isAPMode; }
    String getLocalIP() { return WiFi.localIP().toString(); }
    String getAPIP() { return WiFi.softAPIP().toString(); }
    String getMacAddress() { return WiFi.macAddress(); }
    int getChannel() { return WiFi.channel(); }
    int getAPClients() { return WiFi.softAPgetStationNum(); }
    String getHostname() { return _hostname; }

    // Get full status JSON
    String getStatusJSON() {
        String json = "{";
        json += "\"connected\":" + String(_isConnected ? "true" : "false") + ",";
        json += "\"mode\":\"" + String(_isDualMode ? "AP+STA" : (_isAPMode ? "AP" : "STA")) + "\",";
        json += "\"ip\":\"" + getLocalIP() + "\",";
        json += "\"ap_ip\":\"" + getAPIP() + "\",";
        json += "\"mac\":\"" + getMacAddress() + "\",";
        json += "\"rssi\":" + String(getSignalStrength()) + ",";
        json += "\"quality\":\"" + getSignalQuality() + "\",";
        json += "\"channel\":" + String(getChannel()) + ",";
        json += "\"hostname\":\"" + _hostname + "\",";
        json += "\"ap_clients\":" + String(getAPClients());
        json += "}";
        return json;
    }
};

#endif // WIFI_MANAGER_H
