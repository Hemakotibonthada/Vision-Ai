#ifndef BLE_MANAGER_H
#define BLE_MANAGER_H

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include "config.h"

class BLEManager {
private:
    BLEServer* _pServer;
    BLECharacteristic* _pCharacteristic;
    BLEAdvertising* _pAdvertising;
    bool _deviceConnected;
    bool _oldDeviceConnected;
    int _connectedDevices;
    String _lastReceivedData;

    class ServerCallbacks : public BLEServerCallbacks {
        BLEManager* _manager;
    public:
        ServerCallbacks(BLEManager* manager) : _manager(manager) {}
        void onConnect(BLEServer* pServer) {
            _manager->_deviceConnected = true;
            _manager->_connectedDevices++;
            Serial.println("[BLE] Device connected");
        }
        void onDisconnect(BLEServer* pServer) {
            _manager->_deviceConnected = false;
            _manager->_connectedDevices--;
            Serial.println("[BLE] Device disconnected");
            // Restart advertising
            pServer->startAdvertising();
        }
    };

    class CharacteristicCallbacks : public BLECharacteristicCallbacks {
        BLEManager* _manager;
    public:
        CharacteristicCallbacks(BLEManager* manager) : _manager(manager) {}
        void onWrite(BLECharacteristic* pCharacteristic) {
            std::string value = pCharacteristic->getValue();
            if (value.length() > 0) {
                _manager->_lastReceivedData = String(value.c_str());
                Serial.printf("[BLE] Received: %s\n", value.c_str());
            }
        }
    };

public:
    BLEManager() : _pServer(nullptr), _pCharacteristic(nullptr),
                   _deviceConnected(false), _oldDeviceConnected(false),
                   _connectedDevices(0) {}

    // Feature 16-18: BLE initialization
    void begin() {
        BLEDevice::init(BLE_DEVICE_NAME);
        
        _pServer = BLEDevice::createServer();
        _pServer->setCallbacks(new ServerCallbacks(this));
        
        BLEService* pService = _pServer->createService(BLE_SERVICE_UUID);
        
        _pCharacteristic = pService->createCharacteristic(
            BLE_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE |
            BLECharacteristic::PROPERTY_NOTIFY |
            BLECharacteristic::PROPERTY_INDICATE
        );
        
        _pCharacteristic->addDescriptor(new BLE2902());
        _pCharacteristic->setCallbacks(new CharacteristicCallbacks(this));
        
        pService->start();
        
        _pAdvertising = BLEDevice::getAdvertising();
        _pAdvertising->addServiceUUID(BLE_SERVICE_UUID);
        _pAdvertising->setScanResponse(true);
        _pAdvertising->setMinPreferred(0x06);
        _pAdvertising->setMinPreferred(0x12);
        
        BLEDevice::startAdvertising();
        Serial.println("[BLE] Advertising started");
    }

    // Send data via BLE notification
    void sendNotification(const String& data) {
        if (_deviceConnected) {
            _pCharacteristic->setValue(data.c_str());
            _pCharacteristic->notify();
        }
    }

    // Send sensor data
    void sendSensorData(float temp, float humidity, bool motion) {
        if (_deviceConnected) {
            String data = "{\"t\":" + String(temp, 1) + 
                         ",\"h\":" + String(humidity, 1) + 
                         ",\"m\":" + String(motion ? 1 : 0) + "}";
            sendNotification(data);
        }
    }

    // BLE scan for nearby devices
    String scanDevices(int duration = 5) {
        Serial.println("[BLE] Scanning...");
        BLEScan* pBLEScan = BLEDevice::getScan();
        pBLEScan->setActiveScan(true);
        pBLEScan->setInterval(100);
        pBLEScan->setWindow(99);
        
        BLEScanResults results = pBLEScan->start(duration, false);
        
        String json = "[";
        for (int i = 0; i < results.getCount(); i++) {
            BLEAdvertisedDevice device = results.getDevice(i);
            if (i > 0) json += ",";
            json += "{\"name\":\"" + String(device.getName().c_str()) + "\",";
            json += "\"address\":\"" + String(device.getAddress().toString().c_str()) + "\",";
            json += "\"rssi\":" + String(device.getRSSI()) + "}";
        }
        json += "]";
        
        pBLEScan->clearResults();
        return json;
    }

    void handle() {
        if (!_deviceConnected && _oldDeviceConnected) {
            delay(500);
            _pServer->startAdvertising();
            _oldDeviceConnected = _deviceConnected;
        }
        if (_deviceConnected && !_oldDeviceConnected) {
            _oldDeviceConnected = _deviceConnected;
        }
    }

    bool isConnected() { return _deviceConnected; }
    int getConnectedCount() { return _connectedDevices; }
    String getLastData() { return _lastReceivedData; }

    String getStatusJSON() {
        String json = "{";
        json += "\"enabled\":true,";
        json += "\"connected\":" + String(_deviceConnected ? "true" : "false") + ",";
        json += "\"devices\":" + String(_connectedDevices) + ",";
        json += "\"name\":\"" + String(BLE_DEVICE_NAME) + "\"";
        json += "}";
        return json;
    }
};

#endif // BLE_MANAGER_H
