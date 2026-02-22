#ifndef OTA_MANAGER_H
#define OTA_MANAGER_H

#include <ArduinoOTA.h>
#include <Update.h>
#include "config.h"

class OTAManager {
private:
    bool _updating;
    int _progress;
    String _updateType;

public:
    OTAManager() : _updating(false), _progress(0) {}

    // Feature 11: OTA firmware updates
    void begin() {
        ArduinoOTA.setHostname(OTA_HOSTNAME);
        ArduinoOTA.setPassword(OTA_PASSWORD);
        ArduinoOTA.setPort(OTA_PORT);

        ArduinoOTA.onStart([this]() {
            _updating = true;
            _progress = 0;
            _updateType = (ArduinoOTA.getCommand() == U_FLASH) ? "firmware" : "filesystem";
            Serial.printf("[OTA] Start updating %s\n", _updateType.c_str());
        });

        ArduinoOTA.onEnd([this]() {
            _updating = false;
            _progress = 100;
            Serial.println("\n[OTA] Update complete!");
        });

        ArduinoOTA.onProgress([this](unsigned int progress, unsigned int total) {
            _progress = (progress / (total / 100));
            Serial.printf("[OTA] Progress: %u%%\r", _progress);
        });

        ArduinoOTA.onError([this](ota_error_t error) {
            _updating = false;
            Serial.printf("[OTA] Error[%u]: ", error);
            switch (error) {
                case OTA_AUTH_ERROR:    Serial.println("Auth Failed"); break;
                case OTA_BEGIN_ERROR:   Serial.println("Begin Failed"); break;
                case OTA_CONNECT_ERROR: Serial.println("Connect Failed"); break;
                case OTA_RECEIVE_ERROR: Serial.println("Receive Failed"); break;
                case OTA_END_ERROR:     Serial.println("End Failed"); break;
            }
        });

        ArduinoOTA.begin();
        Serial.printf("[OTA] Ready on port %d\n", OTA_PORT);
    }

    void handle() { ArduinoOTA.handle(); }
    bool isUpdating() { return _updating; }
    int getProgress() { return _progress; }

    // Feature 12: HTTP OTA update
    bool updateFromURL(const char* url) {
        Serial.printf("[OTA] Updating from URL: %s\n", url);
        // HTTP-based OTA would require HTTPClient
        return false; // Placeholder
    }

    // Feature: Firmware version info
    String getFirmwareInfo() {
        String json = "{";
        json += "\"version\":\"" + String(FIRMWARE_VERSION) + "\",";
        json += "\"hardware\":\"" + String(HARDWARE_VERSION) + "\",";
        json += "\"sdk\":\"" + String(ESP.getSdkVersion()) + "\",";
        json += "\"chip_model\":\"" + String(ESP.getChipModel()) + "\",";
        json += "\"chip_revision\":" + String(ESP.getChipRevision()) + ",";
        json += "\"flash_size\":" + String(ESP.getFlashChipSize()) + ",";
        json += "\"sketch_size\":" + String(ESP.getSketchSize()) + ",";
        json += "\"free_sketch_space\":" + String(ESP.getFreeSketchSpace()) + ",";
        json += "\"updating\":" + String(_updating ? "true" : "false") + ",";
        json += "\"update_progress\":" + String(_progress);
        json += "}";
        return json;
    }
};

#endif // OTA_MANAGER_H
