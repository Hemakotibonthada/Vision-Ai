#ifndef MQTT_CLIENT_MGR_H
#define MQTT_CLIENT_MGR_H

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "config.h"

typedef void (*MQTTMessageCallback)(const char* topic, const char* payload);

class MQTTClientManager {
private:
    WiFiClient _wifiClient;
    PubSubClient _mqttClient;
    bool _isConnected;
    unsigned long _lastReconnectAttempt;
    unsigned long _messageCount;
    unsigned long _lastMessageTime;
    int _reconnectAttempts;
    MQTTMessageCallback _userCallback;
    
    struct Subscription {
        String topic;
        uint8_t qos;
        bool active;
    };
    Subscription _subscriptions[20];
    int _subCount;

    static MQTTClientManager* _instance;
    
    static void staticCallback(char* topic, byte* payload, unsigned int length) {
        if (_instance) {
            char message[length + 1];
            memcpy(message, payload, length);
            message[length] = '\0';
            _instance->handleMessage(topic, message);
        }
    }

    void handleMessage(const char* topic, const char* payload) {
        Serial.printf("[MQTT] Message on %s: %s\n", topic, payload);
        _messageCount++;
        _lastMessageTime = millis();
        
        // Handle system commands
        if (String(topic) == TOPIC_COMMAND) {
            handleCommand(payload);
        }
        
        // Forward to user callback
        if (_userCallback) {
            _userCallback(topic, payload);
        }
    }

    void handleCommand(const char* payload) {
        StaticJsonDocument<512> doc;
        DeserializationError error = deserializeJson(doc, payload);
        if (error) return;
        
        const char* cmd = doc["command"];
        if (!cmd) return;
        
        if (strcmp(cmd, "restart") == 0) {
            publish(TOPIC_STATUS, "{\"status\":\"restarting\"}");
            delay(1000);
            ESP.restart();
        } else if (strcmp(cmd, "status") == 0) {
            publishStatus();
        } else if (strcmp(cmd, "ping") == 0) {
            publish(TOPIC_STATUS, "{\"status\":\"pong\"}");
        }
    }

public:
    MQTTClientManager() : _mqttClient(_wifiClient), _isConnected(false),
                          _lastReconnectAttempt(0), _messageCount(0),
                          _lastMessageTime(0), _reconnectAttempts(0),
                          _userCallback(nullptr), _subCount(0) {
        _instance = this;
    }

    void begin() {
        _mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
        _mqttClient.setCallback(staticCallback);
        _mqttClient.setKeepAlive(MQTT_KEEPALIVE);
        _mqttClient.setBufferSize(MQTT_MAX_PACKET);
        Serial.println("[MQTT] Initialized");
    }

    // Feature 6: MQTT Client with QoS
    bool connect() {
        Serial.printf("[MQTT] Connecting to %s:%d...\n", MQTT_BROKER, MQTT_PORT);
        
        String willMessage = "{\"status\":\"offline\",\"device\":\"" + String(MQTT_CLIENT_ID) + "\"}";
        
        bool result = _mqttClient.connect(
            MQTT_CLIENT_ID,
            MQTT_USER,
            MQTT_PASSWORD,
            TOPIC_STATUS,
            MQTT_QOS,
            true,
            willMessage.c_str()
        );
        
        if (result) {
            _isConnected = true;
            _reconnectAttempts = 0;
            Serial.println("[MQTT] Connected!");
            
            // Subscribe to default topics
            subscribe(TOPIC_COMMAND, MQTT_QOS);
            subscribe(TOPIC_CONFIG, MQTT_QOS);
            subscribe(TOPIC_CAMERA_STATUS, MQTT_QOS);
            subscribe(TOPIC_AI_RESULT, MQTT_QOS);
            subscribe(TOPIC_OTA, MQTT_QOS);
            
            // Publish online status
            publishStatus();
            publishDiscovery();
        } else {
            Serial.printf("[MQTT] Failed, rc=%d\n", _mqttClient.state());
        }
        
        return result;
    }

    // Feature 7: MQTT Auto-reconnect
    void handleReconnect() {
        if (!_mqttClient.connected()) {
            unsigned long now = millis();
            // Exponential backoff
            unsigned long delay_ms = min((unsigned long)(MQTT_RECONNECT_DELAY * pow(2, _reconnectAttempts)), (unsigned long)30000);
            
            if (now - _lastReconnectAttempt > delay_ms) {
                _lastReconnectAttempt = now;
                _reconnectAttempts++;
                
                if (connect()) {
                    // Resubscribe to all topics
                    for (int i = 0; i < _subCount; i++) {
                        if (_subscriptions[i].active) {
                            _mqttClient.subscribe(_subscriptions[i].topic.c_str(), _subscriptions[i].qos);
                        }
                    }
                }
            }
        }
    }

    // Feature 8: Topic-based routing
    bool subscribe(const char* topic, uint8_t qos = MQTT_QOS) {
        if (_subCount < 20) {
            _subscriptions[_subCount].topic = topic;
            _subscriptions[_subCount].qos = qos;
            _subscriptions[_subCount].active = true;
            _subCount++;
        }
        return _mqttClient.subscribe(topic, qos);
    }

    bool unsubscribe(const char* topic) {
        for (int i = 0; i < _subCount; i++) {
            if (_subscriptions[i].topic == topic) {
                _subscriptions[i].active = false;
            }
        }
        return _mqttClient.unsubscribe(topic);
    }

    bool publish(const char* topic, const char* payload, bool retain = MQTT_RETAIN) {
        if (!_mqttClient.connected()) return false;
        return _mqttClient.publish(topic, payload, retain);
    }

    bool publishJSON(const char* topic, StaticJsonDocument<1024>& doc) {
        char buffer[1024];
        serializeJson(doc, buffer);
        return publish(topic, buffer);
    }

    void publishStatus() {
        StaticJsonDocument<512> doc;
        doc["status"] = "online";
        doc["device"] = MQTT_CLIENT_ID;
        doc["firmware"] = FIRMWARE_VERSION;
        doc["uptime"] = millis() / 1000;
        doc["free_heap"] = ESP.getFreeHeap();
        doc["messages"] = _messageCount;
        doc["rssi"] = WiFi.RSSI();
        
        char buffer[512];
        serializeJson(doc, buffer);
        publish(TOPIC_STATUS, buffer, true);
    }

    void publishDiscovery() {
        StaticJsonDocument<512> doc;
        doc["device_id"] = MQTT_CLIENT_ID;
        doc["name"] = DEVICE_NAME;
        doc["type"] = "esp32-server";
        doc["firmware"] = FIRMWARE_VERSION;
        doc["ip"] = WiFi.localIP().toString();
        doc["mac"] = WiFi.macAddress();
        
        JsonArray caps = doc.createNestedArray("capabilities");
        caps.add("sensors");
        caps.add("gpio");
        caps.add("relay");
        caps.add("ota");
        caps.add("ble");
        
        char buffer[512];
        serializeJson(doc, buffer);
        publish(TOPIC_DEVICE_DISC, buffer, true);
    }

    void publishSensorData(float temp, float humidity, bool motion, float distance, int light) {
        StaticJsonDocument<512> doc;
        doc["temperature"] = temp;
        doc["humidity"] = humidity;
        doc["motion"] = motion;
        doc["distance"] = distance;
        doc["light"] = light;
        doc["timestamp"] = millis();
        
        char buffer[512];
        serializeJson(doc, buffer);
        publish(TOPIC_SENSOR, buffer);
    }

    void publishAlert(const char* type, const char* message, int severity = 1) {
        StaticJsonDocument<256> doc;
        doc["type"] = type;
        doc["message"] = message;
        doc["severity"] = severity;
        doc["device"] = MQTT_CLIENT_ID;
        doc["timestamp"] = millis();
        
        char buffer[256];
        serializeJson(doc, buffer);
        publish(TOPIC_ALERT, buffer);
    }

    void setCallback(MQTTMessageCallback callback) { _userCallback = callback; }
    void loop() { _mqttClient.loop(); handleReconnect(); }
    bool connected() { return _mqttClient.connected(); }
    unsigned long getMessageCount() { return _messageCount; }

    String getStatusJSON() {
        String json = "{";
        json += "\"connected\":" + String(connected() ? "true" : "false") + ",";
        json += "\"broker\":\"" + String(MQTT_BROKER) + "\",";
        json += "\"port\":" + String(MQTT_PORT) + ",";
        json += "\"client_id\":\"" + String(MQTT_CLIENT_ID) + "\",";
        json += "\"messages\":" + String(_messageCount) + ",";
        json += "\"subscriptions\":" + String(_subCount) + ",";
        json += "\"reconnect_attempts\":" + String(_reconnectAttempts);
        json += "}";
        return json;
    }
};

MQTTClientManager* MQTTClientManager::_instance = nullptr;

#endif // MQTT_CLIENT_MGR_H
