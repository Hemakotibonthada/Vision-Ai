/*
 * =============================================================
 * Vision-AI ESP32-CAM Module v3.0 - Jarvis Vision Controller
 * =============================================================
 * Features: Camera capture, MJPEG streaming, Motion detection,
 *           Face detection, Intruder alert, Patrol mode,
 *           Night vision, Jarvis AI integration, MQTT, HTTP
 * =============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <esp_http_server.h>
#include <esp_task_wdt.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <base64.h>
#include "config.h"

// ============================================
// Global Declarations
// ============================================
WiFiClient wifiClient;
WiFiClient wifiClient2;  // Second client for HTTP uploads
PubSubClient mqtt(wifiClient);

httpd_handle_t stream_httpd = NULL;
httpd_handle_t capture_httpd = NULL;

// Camera state
bool streamActive = false;
bool motionDetectEnabled = true;
bool faceDetectEnabled = FACE_DETECT_ENABLED;
bool timelapseActive = false;
int flashIntensity = 0;
bool autoFlash = false;
unsigned long lastMotionTime = 0;
unsigned long lastTimelapse = 0;
int frameCount = 0;
unsigned long fpsTimer = 0;
float currentFPS = 0;

// Motion detection buffer
uint8_t* prevFrame = NULL;
size_t prevFrameSize = 0;
int motionEventCount = 0;

// Face detection
bool facesDetected = false;
int faceCount = 0;

// Jarvis integration state
bool jarvisPatrolMode = false;
bool jarvisIntruderMode = INTRUDER_DETECT_ENABLED;
bool jarvisNightMode = false;
unsigned long lastPersonPublish = 0;
unsigned long lastPatrolCapture = 0;
unsigned long lastHeartbeat = 0;
int personCount = 0;
int consecutiveMotionFrames = 0;
bool intruderAlertActive = false;
unsigned long intruderDetectTime = 0;
String lastAIResult = "";
int totalCaptures = 0;
int totalUploads = 0;
int aiDetectionCount = 0;

// Night vision
bool nightModeActive = false;
int ambientLight = 255; // Estimated from frame brightness

// ============================================
// Camera Initialization (Feature 56)
// ============================================
bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;
    
    // PSRAM available - use higher resolution
    if (psramFound()) {
        config.frame_size = FRAMESIZE_UXGA;    // 1600x1200
        config.jpeg_quality = 10;
        config.fb_count = 2;
        config.fb_location = CAMERA_FB_IN_PSRAM;
        Serial.println("[Camera] PSRAM found, using high resolution");
    } else {
        config.frame_size = FRAMESIZE_VGA;     // 640x480
        config.jpeg_quality = 12;
        config.fb_count = 1;
        config.fb_location = CAMERA_FB_IN_DRAM;
        Serial.println("[Camera] No PSRAM, using standard resolution");
    }
    
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[Camera] Init failed: 0x%x\n", err);
        return false;
    }
    
    // Apply default settings
    sensor_t* s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s, DEFAULT_RESOLUTION);
        s->set_quality(s, DEFAULT_QUALITY);
        s->set_brightness(s, DEFAULT_BRIGHTNESS);
        s->set_contrast(s, DEFAULT_CONTRAST);
        s->set_saturation(s, DEFAULT_SATURATION);
        s->set_sharpness(s, DEFAULT_SHARPNESS);
        s->set_hmirror(s, DEFAULT_HMIRROR);
        s->set_vflip(s, DEFAULT_VFLIP);
        s->set_wb_mode(s, DEFAULT_WB_MODE);
        s->set_special_effect(s, DEFAULT_EFFECT);
        
        // Feature 62-63: Exposure control
        s->set_exposure_ctrl(s, 1);
        s->set_aec2(s, 1);
        s->set_ae_level(s, 0);
        
        // Feature 67-68: Gain control
        s->set_gain_ctrl(s, 1);
        s->set_agc_gain(s, 0);
        s->set_gainceiling(s, (gainceiling_t)6);
        
        // Feature 76-79: Corrections
        s->set_bpc(s, 1);
        s->set_wpc(s, 1);
        s->set_raw_gma(s, 1);
        s->set_lenc(s, 1);
        
        // Feature 73: DCW
        s->set_dcw(s, 1);
    }
    
    Serial.println("[Camera] Initialized successfully");
    return true;
}

// ============================================
// Flash LED Control (Feature 81)
// ============================================
void setupFlash() {
    ledcSetup(FLASH_LED_CHANNEL, 5000, 8);
    ledcAttachPin(FLASH_LED_PIN, FLASH_LED_CHANNEL);
    ledcWrite(FLASH_LED_CHANNEL, 0);
    Serial.println("[Flash] Initialized");
}

void setFlash(int intensity) {
    flashIntensity = constrain(intensity, 0, 255);
    ledcWrite(FLASH_LED_CHANNEL, flashIntensity);
}

void flashOn() { setFlash(255); }
void flashOff() { setFlash(0); }

void autoFlashControl(int lightLevel) {
    if (autoFlash && lightLevel < 100) {
        setFlash(map(100 - lightLevel, 0, 100, 50, 255));
    } else if (autoFlash) {
        flashOff();
    }
}

// ============================================
// Night Vision Auto-Detect
// ============================================
int estimateAmbientLight(camera_fb_t* fb) {
    if (!fb || fb->len < 100) return 128;
    // Sample brightness from JPEG data (rough estimate)
    long total = 0;
    int samples = min((size_t)500, fb->len / 4);
    for (int i = 0; i < samples; i++) {
        total += fb->buf[i * 4];
    }
    return total / samples;
}

void handleNightMode(camera_fb_t* fb) {
    if (!NIGHT_MODE_AUTO) return;
    ambientLight = estimateAmbientLight(fb);
    bool shouldBeNight = (ambientLight < LIGHT_THRESHOLD_LOW);
    
    if (shouldBeNight != nightModeActive) {
        nightModeActive = shouldBeNight;
        sensor_t* s = esp_camera_sensor_get();
        if (s) {
            if (nightModeActive) {
                // Night mode: increase gain, lower quality for speed
                s->set_agc_gain(s, 30);
                s->set_gainceiling(s, (gainceiling_t)6);
                s->set_aec_value(s, 600);
                Serial.println("[Night] Night vision mode ACTIVATED");
            } else {
                s->set_agc_gain(s, 0);
                s->set_gainceiling(s, (gainceiling_t)2);
                s->set_aec_value(s, 300);
                Serial.println("[Night] Day mode restored");
            }
        }
        // Notify Jarvis
        StaticJsonDocument<128> doc;
        doc["event"] = "night_mode";
        doc["active"] = nightModeActive;
        doc["ambient"] = ambientLight;
        char buf[128];
        serializeJson(doc, buf);
        mqtt.publish(TOPIC_JARVIS_CAM_EVENT, buf);
    }
}

// ============================================
// Jarvis Heartbeat
// ============================================
void sendCamHeartbeat() {
    StaticJsonDocument<512> doc;
    doc["device"]     = MQTT_CLIENT_ID;
    doc["type"]       = "camera";
    doc["firmware"]   = FIRMWARE_VERSION;
    doc["uptime"]     = millis() / 1000;
    doc["free_heap"]  = ESP.getFreeHeap();
    doc["free_psram"] = ESP.getFreePsram();
    doc["rssi"]       = WiFi.RSSI();
    doc["ip"]         = WiFi.localIP().toString();
    doc["streaming"]  = streamActive;
    doc["fps"]        = currentFPS;
    doc["motion"]     = motionDetectEnabled;
    doc["night_mode"] = nightModeActive;
    doc["ambient"]    = ambientLight;
    doc["patrol"]     = jarvisPatrolMode;
    doc["intruder_mode"] = jarvisIntruderMode;
    doc["motion_events"] = motionEventCount;
    doc["persons"]    = personCount;
    doc["captures"]   = totalCaptures;
    doc["uploads"]    = totalUploads;
    doc["detections"] = aiDetectionCount;
    doc["flash"]      = flashIntensity;
    doc["stream_url"] = "http://" + WiFi.localIP().toString() + ":81/stream";
    
    char buf[512];
    serializeJson(doc, buf);
    mqtt.publish(TOPIC_JARVIS_CAM_HEARTBEAT, buf);
}

// ============================================
// Intruder Alert System
// ============================================
void triggerIntruderAlert(camera_fb_t* fb, const String& reason) {
    if (intruderAlertActive) return; // Already alerting
    intruderAlertActive = true;
    intruderDetectTime = millis();
    
    Serial.println("[INTRUDER] *** ALERT TRIGGERED: " + reason + " ***");
    
    // Flash strobe as visual deterrent
    for (int i = 0; i < 5; i++) {
        flashOn(); delay(100); flashOff(); delay(100);
    }
    
    // Publish intruder alert
    StaticJsonDocument<256> doc;
    doc["event"]     = "intruder_alert";
    doc["reason"]    = reason;
    doc["camera"]    = MQTT_CLIENT_ID;
    doc["timestamp"] = millis();
    doc["night"]     = nightModeActive;
    
    char buf[256];
    serializeJson(doc, buf);
    mqtt.publish(TOPIC_JARVIS_INTRUDER, buf, true);
    mqtt.publish(TOPIC_JARVIS_CAM_ALERT, buf);
    
    // Capture evidence frames
    for (int i = 0; i < INTRUDER_CAPTURE_COUNT; i++) {
        if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
        delay(200);
        camera_fb_t* evidence = esp_camera_fb_get();
        if (evidence) {
            uploadImageToAI(evidence, "intruder_evidence");
            esp_camera_fb_return(evidence);
        }
        flashOff();
        delay(300);
    }
    
    // Reset after delay
    intruderAlertActive = false;
}

// ============================================
// Patrol Mode
// ============================================
void handlePatrol() {
    if (!jarvisPatrolMode) return;
    
    unsigned long now = millis();
    if (now - lastPatrolCapture < PATROL_INTERVAL_MS) return;
    lastPatrolCapture = now;
    
    Serial.println("[Patrol] Periodic capture");
    
    // Night flash if needed
    if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
    delay(100);
    
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) {
        totalCaptures++;
        if (PATROL_UPLOAD) {
            uploadImageToAI(fb, "patrol");
        }
        
        // Check motion
        bool motion = detectMotion(fb);
        
        StaticJsonDocument<256> doc;
        doc["event"]     = "patrol_capture";
        doc["motion"]    = motion;
        doc["size"]      = fb->len;
        doc["night"]     = nightModeActive;
        doc["ambient"]   = ambientLight;
        doc["timestamp"] = millis();
        
        char buf[256];
        serializeJson(doc, buf);
        mqtt.publish(TOPIC_JARVIS_PATROL, buf);
        
        esp_camera_fb_return(fb);
    }
    
    flashOff();
}

// ============================================
// Camera Settings Control (Features 59-80)
// ============================================
void setCameraSettings(JsonDocument& doc) {
    sensor_t* s = esp_camera_sensor_get();
    if (!s) return;
    
    // Feature 59: Resolution
    if (doc.containsKey("resolution")) {
        String res = doc["resolution"].as<String>();
        framesize_t fs = FRAMESIZE_VGA;
        if (res == "QQVGA") fs = FRAMESIZE_QQVGA;           // 160x120
        else if (res == "QCIF") fs = FRAMESIZE_QCIF;        // 176x144
        else if (res == "HQVGA") fs = FRAMESIZE_HQVGA;      // 240x176
        else if (res == "240X240") fs = FRAMESIZE_240X240;   // 240x240
        else if (res == "QVGA") fs = FRAMESIZE_QVGA;        // 320x240
        else if (res == "CIF") fs = FRAMESIZE_CIF;          // 400x296
        else if (res == "HVGA") fs = FRAMESIZE_HVGA;        // 480x320
        else if (res == "VGA") fs = FRAMESIZE_VGA;           // 640x480
        else if (res == "SVGA") fs = FRAMESIZE_SVGA;         // 800x600
        else if (res == "XGA") fs = FRAMESIZE_XGA;           // 1024x768
        else if (res == "HD") fs = FRAMESIZE_HD;             // 1280x720
        else if (res == "SXGA") fs = FRAMESIZE_SXGA;         // 1280x1024
        else if (res == "UXGA") fs = FRAMESIZE_UXGA;         // 1600x1200
        s->set_framesize(s, fs);
        Serial.printf("[Camera] Resolution: %s\n", res.c_str());
    }
    
    // Feature 61: JPEG quality
    if (doc.containsKey("quality")) s->set_quality(s, doc["quality"].as<int>());
    
    // Feature 63: Brightness
    if (doc.containsKey("brightness")) s->set_brightness(s, doc["brightness"].as<int>());
    
    // Feature 64: Contrast
    if (doc.containsKey("contrast")) s->set_contrast(s, doc["contrast"].as<int>());
    
    // Feature 65: Saturation
    if (doc.containsKey("saturation")) s->set_saturation(s, doc["saturation"].as<int>());
    
    // Feature 66: Sharpness
    if (doc.containsKey("sharpness")) s->set_sharpness(s, doc["sharpness"].as<int>());
    
    // Feature 69: Special effects
    if (doc.containsKey("effect")) {
        int effect = doc["effect"].as<int>();
        // 0=None, 1=Negative, 2=Grayscale, 3=Red, 4=Green, 5=Blue, 6=Sepia
        s->set_special_effect(s, effect);
    }
    
    // Feature 70-71: Mirror & Flip
    if (doc.containsKey("hmirror")) s->set_hmirror(s, doc["hmirror"].as<int>());
    if (doc.containsKey("vflip")) s->set_vflip(s, doc["vflip"].as<int>());
    
    // Feature 62: Auto-exposure
    if (doc.containsKey("aec")) s->set_exposure_ctrl(s, doc["aec"].as<int>());
    if (doc.containsKey("aec2")) s->set_aec2(s, doc["aec2"].as<int>());
    if (doc.containsKey("ae_level")) s->set_ae_level(s, doc["ae_level"].as<int>());
    if (doc.containsKey("aec_value")) s->set_aec_value(s, doc["aec_value"].as<int>());
    
    // Feature 67: Gain
    if (doc.containsKey("agc")) s->set_gain_ctrl(s, doc["agc"].as<int>());
    if (doc.containsKey("agc_gain")) s->set_agc_gain(s, doc["agc_gain"].as<int>());
    if (doc.containsKey("gainceiling")) s->set_gainceiling(s, (gainceiling_t)doc["gainceiling"].as<int>());
    
    // Feature 64: White balance
    if (doc.containsKey("awb")) s->set_whitebal(s, doc["awb"].as<int>());
    if (doc.containsKey("awb_gain")) s->set_awb_gain(s, doc["awb_gain"].as<int>());
    if (doc.containsKey("wb_mode")) s->set_wb_mode(s, doc["wb_mode"].as<int>());
    
    // Corrections
    if (doc.containsKey("bpc")) s->set_bpc(s, doc["bpc"].as<int>());
    if (doc.containsKey("wpc")) s->set_wpc(s, doc["wpc"].as<int>());
    if (doc.containsKey("raw_gma")) s->set_raw_gma(s, doc["raw_gma"].as<int>());
    if (doc.containsKey("lenc")) s->set_lenc(s, doc["lenc"].as<int>());
    if (doc.containsKey("dcw")) s->set_dcw(s, doc["dcw"].as<int>());
    
    // Flash
    if (doc.containsKey("flash")) setFlash(doc["flash"].as<int>());
    if (doc.containsKey("auto_flash")) autoFlash = doc["auto_flash"].as<bool>();
    
    // Motion detect
    if (doc.containsKey("motion_detect")) motionDetectEnabled = doc["motion_detect"].as<bool>();
    if (doc.containsKey("face_detect")) faceDetectEnabled = doc["face_detect"].as<bool>();
}

// Get current camera settings as JSON
String getCameraSettingsJSON() {
    sensor_t* s = esp_camera_sensor_get();
    String json = "{";
    if (s) {
        json += "\"framesize\":" + String(s->status.framesize) + ",";
        json += "\"quality\":" + String(s->status.quality) + ",";
        json += "\"brightness\":" + String(s->status.brightness) + ",";
        json += "\"contrast\":" + String(s->status.contrast) + ",";
        json += "\"saturation\":" + String(s->status.saturation) + ",";
        json += "\"sharpness\":" + String(s->status.sharpness) + ",";
        json += "\"special_effect\":" + String(s->status.special_effect) + ",";
        json += "\"wb_mode\":" + String(s->status.wb_mode) + ",";
        json += "\"awb\":" + String(s->status.awb) + ",";
        json += "\"awb_gain\":" + String(s->status.awb_gain) + ",";
        json += "\"aec\":" + String(s->status.aec) + ",";
        json += "\"aec2\":" + String(s->status.aec2) + ",";
        json += "\"ae_level\":" + String(s->status.ae_level) + ",";
        json += "\"aec_value\":" + String(s->status.aec_value) + ",";
        json += "\"agc\":" + String(s->status.agc) + ",";
        json += "\"agc_gain\":" + String(s->status.agc_gain) + ",";
        json += "\"gainceiling\":" + String(s->status.gainceiling) + ",";
        json += "\"bpc\":" + String(s->status.bpc) + ",";
        json += "\"wpc\":" + String(s->status.wpc) + ",";
        json += "\"raw_gma\":" + String(s->status.raw_gma) + ",";
        json += "\"lenc\":" + String(s->status.lenc) + ",";
        json += "\"hmirror\":" + String(s->status.hmirror) + ",";
        json += "\"vflip\":" + String(s->status.vflip) + ",";
        json += "\"dcw\":" + String(s->status.dcw) + ",";
    }
    json += "\"flash\":" + String(flashIntensity) + ",";
    json += "\"auto_flash\":" + String(autoFlash ? "true" : "false") + ",";
    json += "\"motion_detect\":" + String(motionDetectEnabled ? "true" : "false") + ",";
    json += "\"face_detect\":" + String(faceDetectEnabled ? "true" : "false") + ",";
    json += "\"stream_active\":" + String(streamActive ? "true" : "false") + ",";
    json += "\"fps\":" + String(currentFPS, 1) + ",";
    json += "\"motion_events\":" + String(motionEventCount);
    json += "}";
    return json;
}

// ============================================
// Motion Detection (Feature 86)
// ============================================
bool detectMotion(camera_fb_t* fb) {
    if (!motionDetectEnabled || !fb) return false;
    
    unsigned long now = millis();
    if (now - lastMotionTime < MOTION_COOLDOWN) return false;
    
    if (prevFrame == NULL) {
        prevFrame = (uint8_t*)ps_malloc(fb->len);
        if (prevFrame) {
            memcpy(prevFrame, fb->buf, fb->len);
            prevFrameSize = fb->len;
        }
        return false;
    }
    
    if (fb->len != prevFrameSize) {
        free(prevFrame);
        prevFrame = (uint8_t*)ps_malloc(fb->len);
        if (prevFrame) {
            memcpy(prevFrame, fb->buf, fb->len);
            prevFrameSize = fb->len;
        }
        return false;
    }
    
    // Count changed pixels
    int changedPixels = 0;
    int sampleStep = 10; // Sample every 10th byte for speed
    for (size_t i = 0; i < fb->len; i += sampleStep) {
        int diff = abs((int)fb->buf[i] - (int)prevFrame[i]);
        if (diff > MOTION_THRESHOLD) {
            changedPixels++;
        }
    }
    
    // Update previous frame
    memcpy(prevFrame, fb->buf, fb->len);
    
    // Calculate motion percentage
    int totalSamples = fb->len / sampleStep;
    float motionPercent = (float)changedPixels / totalSamples * 100.0;
    
    bool motionDetected = changedPixels > (MOTION_MIN_AREA / sampleStep);
    
    if (motionDetected) {
        lastMotionTime = now;
        motionEventCount++;
        consecutiveMotionFrames++;
        Serial.printf("[Motion] Detected! Changed: %d (%.1f%%) [consecutive: %d]\n", 
                      changedPixels * sampleStep, motionPercent, consecutiveMotionFrames);
        
        // Publish motion event to standard topic
        StaticJsonDocument<256> doc;
        doc["event"] = "motion";
        doc["changed_pixels"] = changedPixels * sampleStep;
        doc["motion_percent"] = motionPercent;
        doc["timestamp"] = millis();
        doc["camera"] = MQTT_CLIENT_ID;
        doc["night"] = nightModeActive;
        doc["consecutive"] = consecutiveMotionFrames;
        
        char buffer[256];
        serializeJson(doc, buffer);
        mqtt.publish(TOPIC_CAM_MOTION, buffer);
        
        // Also publish to Jarvis motion topic
        mqtt.publish(TOPIC_JARVIS_CAM_EVENT, buffer);
        
        // Intruder mode: sustained motion triggers alert
        if (jarvisIntruderMode && consecutiveMotionFrames >= 3) {
            triggerIntruderAlert(fb, "Sustained motion detected (" + String(consecutiveMotionFrames) + " frames)");
        }
    } else {
        consecutiveMotionFrames = 0;
    }
    
    return motionDetected;
}

// ============================================
// MJPEG Stream Handler (Feature 58)
// ============================================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\nX-Timestamp: %lu\r\n\r\n";

esp_err_t streamHandler(httpd_req_t* req) {
    camera_fb_t* fb = NULL;
    esp_err_t res = ESP_OK;
    char partBuf[128];
    
    streamActive = true;
    Serial.println("[Stream] Client connected");
    
    res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;
    
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-Framerate", String(STREAM_FPS).c_str());
    
    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("[Stream] Capture failed");
            res = ESP_FAIL;
            break;
        }
        
        // Motion detection on stream frames
        detectMotion(fb);
        
        // FPS calculation
        frameCount++;
        if (millis() - fpsTimer >= 1000) {
            currentFPS = frameCount;
            frameCount = 0;
            fpsTimer = millis();
        }
        
        size_t hlen = snprintf(partBuf, sizeof(partBuf), STREAM_PART, fb->len, millis());
        
        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, partBuf, hlen);
        if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
        
        esp_camera_fb_return(fb);
        fb = NULL;
        
        if (res != ESP_OK) break;
        
        // Frame rate control
        int delayMs = 1000 / STREAM_FPS;
        delay(delayMs);
    }
    
    streamActive = false;
    Serial.println("[Stream] Client disconnected");
    return res;
}

// ============================================
// Capture Handler (Feature 57)
// ============================================
esp_err_t captureHandler(httpd_req_t* req) {
    camera_fb_t* fb = NULL;
    
    // Auto flash for capture
    if (autoFlash) flashOn();
    delay(100);
    
    fb = esp_camera_fb_get();
    
    if (autoFlash) flashOff();
    
    if (!fb) {
        Serial.println("[Capture] Failed");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-Timestamp", String(millis()).c_str());
    httpd_resp_set_hdr(req, "X-Resolution", String(String(fb->width) + "x" + String(fb->height)).c_str());
    
    esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    
    Serial.printf("[Capture] Sent %d bytes (%dx%d)\n", fb->len, fb->width, fb->height);
    return res;
}

// ============================================
// Status Handler
// ============================================
esp_err_t statusHandler(httpd_req_t* req) {
    String json = getCameraSettingsJSON();
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, json.c_str(), json.length());
}

// ============================================
// Settings Handler
// ============================================
esp_err_t settingsHandler(httpd_req_t* req) {
    char buf[512];
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret <= 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    buf[ret] = '\0';
    
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, buf);
    if (error) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid JSON");
        return ESP_FAIL;
    }
    
    setCameraSettings(doc);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_sendstr(req, "{\"status\":\"settings_updated\"}");
}

// ============================================
// Start HTTP Servers
// ============================================
void startStreamServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = STREAM_PORT;
    config.ctrl_port = STREAM_PORT + 1;
    config.max_uri_handlers = 4;
    
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_uri_t stream_uri = { .uri = "/stream", .method = HTTP_GET, .handler = streamHandler, .user_ctx = NULL };
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        Serial.printf("[Stream] Server started on port %d\n", STREAM_PORT);
    }
}

void startCaptureServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.max_uri_handlers = 12;
    
    if (httpd_start(&capture_httpd, &config) == ESP_OK) {
        httpd_uri_t capture_uri = { .uri = "/capture", .method = HTTP_GET, .handler = captureHandler, .user_ctx = NULL };
        httpd_uri_t status_uri = { .uri = "/status", .method = HTTP_GET, .handler = statusHandler, .user_ctx = NULL };
        httpd_uri_t settings_uri = { .uri = "/settings", .method = HTTP_POST, .handler = settingsHandler, .user_ctx = NULL };
        httpd_uri_t jarvis_status_uri = { .uri = "/jarvis/status", .method = HTTP_GET, .handler = jarvisStatusHandler, .user_ctx = NULL };
        httpd_uri_t jarvis_detect_uri = { .uri = "/jarvis/detect", .method = HTTP_GET, .handler = jarvisCaptureDetectHandler, .user_ctx = NULL };
        
        httpd_register_uri_handler(capture_httpd, &capture_uri);
        httpd_register_uri_handler(capture_httpd, &status_uri);
        httpd_register_uri_handler(capture_httpd, &settings_uri);
        httpd_register_uri_handler(capture_httpd, &jarvis_status_uri);
        httpd_register_uri_handler(capture_httpd, &jarvis_detect_uri);
        Serial.println("[HTTP] Capture server started on port 80");
    }
}

// ============================================
// Upload Image to AI Server (Jarvis-Enhanced)
// ============================================
bool uploadImageToAI(camera_fb_t* fb, const char* context = "general") {
    if (!fb) return false;
    
    HTTPClient http;
    String url = String(AI_SERVER_URL) + AI_INFERENCE_PATH;
    
    http.begin(url);
    http.setTimeout(AI_TIMEOUT_MS);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", MQTT_CLIENT_ID);
    http.addHeader("X-Timestamp", String(millis()));
    http.addHeader("X-Context", context);
    http.addHeader("X-Night-Mode", String(nightModeActive ? "true" : "false"));
    
    int httpCode = http.POST(fb->buf, fb->len);
    
    if (httpCode == 200) {
        String response = http.getString();
        lastAIResult = response;
        totalUploads++;
        Serial.printf("[AI] Response (%s): %s\n", context, response.c_str());
        
        // Parse AI response for person detection
        StaticJsonDocument<1024> aiDoc;
        if (!deserializeJson(aiDoc, response)) {
            if (aiDoc.containsKey("detections")) {
                JsonArray detections = aiDoc["detections"].as<JsonArray>();
                int persons = 0;
                for (JsonObject det : detections) {
                    String label = det["label"].as<String>();
                    if (label == "person") persons++;
                }
                if (persons != personCount) {
                    personCount = persons;
                    // Publish person count change to Jarvis
                    StaticJsonDocument<256> pDoc;
                    pDoc["event"]   = "person_count";
                    pDoc["count"]   = personCount;
                    pDoc["context"] = context;
                    pDoc["camera"]  = MQTT_CLIENT_ID;
                    pDoc["night"]   = nightModeActive;
                    char pBuf[256];
                    serializeJson(pDoc, pBuf);
                    mqtt.publish(TOPIC_JARVIS_CAM_PERSON, pBuf);
                    
                    // Intruder check
                    if (jarvisIntruderMode && personCount > 0 && strcmp(context, "intruder_evidence") != 0) {
                        triggerIntruderAlert(fb, "AI detected " + String(persons) + " person(s)");
                    }
                }
                aiDetectionCount++;
            }
            
            // Forward face identification results
            if (aiDoc.containsKey("faces")) {
                JsonArray faces = aiDoc["faces"].as<JsonArray>();
                if (faces.size() > 0) {
                    StaticJsonDocument<512> fDoc;
                    fDoc["event"]  = "face_detected";
                    fDoc["count"]  = faces.size();
                    fDoc["camera"] = MQTT_CLIENT_ID;
                    JsonArray fArr = fDoc.createNestedArray("faces");
                    for (JsonObject face : faces) {
                        JsonObject f = fArr.createNestedObject();
                        f["name"]       = face["name"] | "unknown";
                        f["confidence"] = face["confidence"] | 0.0;
                    }
                    char fBuf[512];
                    serializeJson(fDoc, fBuf);
                    mqtt.publish(TOPIC_JARVIS_FACE_ID, fBuf);
                }
            }
        }
        
        // Forward full results via MQTT
        mqtt.publish(TOPIC_AI_INFERENCE, response.c_str());
        
        http.end();
        return true;
    }
    
    Serial.printf("[AI] Upload failed (%s): %d\n", context, httpCode);
    http.end();
    return false;
}

// ============================================
// Burst Capture (Feature 84)
// ============================================
void burstCapture() {
    Serial.printf("[Burst] Capturing %d frames...\n", BURST_COUNT);
    
    for (int i = 0; i < BURST_COUNT; i++) {
        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) {
            String topic = String(TOPIC_CAM_IMAGE) + "/burst/" + String(i);
            
            // Encode first 1KB as base64 preview
            String preview = base64::encode(fb->buf, min((size_t)1024, fb->len));
            
            StaticJsonDocument<2048> doc;
            doc["frame"] = i;
            doc["total"] = BURST_COUNT;
            doc["size"] = fb->len;
            doc["width"] = fb->width;
            doc["height"] = fb->height;
            doc["timestamp"] = millis();
            
            char buffer[256];
            serializeJson(doc, buffer);
            mqtt.publish(topic.c_str(), buffer);
            
            esp_camera_fb_return(fb);
            delay(BURST_DELAY);
        }
    }
    
    Serial.println("[Burst] Complete");
}

// ============================================
// Time-lapse (Feature 85)
// ============================================
void handleTimelapse() {
    if (!timelapseActive) return;
    
    unsigned long now = millis();
    if (now - lastTimelapse >= TIMELAPSE_INTERVAL) {
        lastTimelapse = now;
        
        camera_fb_t* fb = esp_camera_fb_get();
        if (fb) {
            // Upload to AI server for processing
            uploadImageToAI(fb);
            
            StaticJsonDocument<256> doc;
            doc["event"] = "timelapse";
            doc["size"] = fb->len;
            doc["timestamp"] = millis();
            
            char buffer[256];
            serializeJson(doc, buffer);
            mqtt.publish(TOPIC_CAM_IMAGE, buffer);
            
            esp_camera_fb_return(fb);
            Serial.println("[Timelapse] Frame captured");
        }
    }
}

// ============================================
// MQTT Callback (Jarvis-Enhanced)
// ============================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';
    
    Serial.printf("[MQTT] %s: %s\n", topic, message);
    
    String topicStr = String(topic);
    
    // Parse JSON command
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, message);
    if (error) return;
    
    const char* cmd = doc["command"];
    if (!cmd) return;
    
    // ---- Standard camera commands ----
    if (topicStr == TOPIC_CAM_COMMAND || topicStr == TOPIC_JARVIS_CAM_CMD) {
        
        if (strcmp(cmd, "capture") == 0) {
            if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
            delay(100);
            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                totalCaptures++;
                const char* ctx = doc["context"] | "capture";
                uploadImageToAI(fb, ctx);
                esp_camera_fb_return(fb);
            }
            flashOff();
        }
        else if (strcmp(cmd, "burst") == 0) {
            burstCapture();
        }
        else if (strcmp(cmd, "timelapse_start") == 0) {
            timelapseActive = true;
            Serial.println("[Timelapse] Started");
        }
        else if (strcmp(cmd, "timelapse_stop") == 0) {
            timelapseActive = false;
            Serial.println("[Timelapse] Stopped");
        }
        else if (strcmp(cmd, "settings") == 0) {
            setCameraSettings(doc);
        }
        else if (strcmp(cmd, "flash_on") == 0) {
            flashOn();
        }
        else if (strcmp(cmd, "flash_off") == 0) {
            flashOff();
        }
        else if (strcmp(cmd, "flash") == 0) {
            setFlash(doc["intensity"] | 128);
        }
        else if (strcmp(cmd, "status") == 0) {
            mqtt.publish(TOPIC_CAM_STATUS, getCameraSettingsJSON().c_str());
        }
        else if (strcmp(cmd, "restart") == 0) {
            ESP.restart();
        }
        else if (strcmp(cmd, "reset_camera") == 0) {
            esp_camera_deinit();
            delay(500);
            initCamera();
        }
        else if (strcmp(cmd, "detect") == 0) {
            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                totalCaptures++;
                uploadImageToAI(fb, "detect");
                esp_camera_fb_return(fb);
            }
        }
        // ---- Jarvis-specific commands ----
        else if (strcmp(cmd, "patrol_start") == 0) {
            jarvisPatrolMode = true;
            lastPatrolCapture = 0;
            Serial.println("[Jarvis] Patrol mode STARTED");
            StaticJsonDocument<128> ack;
            ack["event"] = "patrol_started";
            ack["camera"] = MQTT_CLIENT_ID;
            char buf[128];
            serializeJson(ack, buf);
            mqtt.publish(TOPIC_JARVIS_CAM_EVENT, buf);
        }
        else if (strcmp(cmd, "patrol_stop") == 0) {
            jarvisPatrolMode = false;
            Serial.println("[Jarvis] Patrol mode STOPPED");
            StaticJsonDocument<128> ack;
            ack["event"] = "patrol_stopped";
            ack["camera"] = MQTT_CLIENT_ID;
            char buf[128];
            serializeJson(ack, buf);
            mqtt.publish(TOPIC_JARVIS_CAM_EVENT, buf);
        }
        else if (strcmp(cmd, "intruder_mode") == 0) {
            jarvisIntruderMode = doc["enabled"] | true;
            Serial.printf("[Jarvis] Intruder mode: %s\n", jarvisIntruderMode ? "ON" : "OFF");
        }
        else if (strcmp(cmd, "night_flash") == 0) {
            int level = doc["level"] | NIGHT_FLASH_LEVEL;
            setFlash(level);
            delay(doc["duration"] | 1000);
            flashOff();
        }
        else if (strcmp(cmd, "identify") == 0) {
            // Capture and send for face identification
            if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
            delay(200);
            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                totalCaptures++;
                uploadImageToAI(fb, "face_identify");
                esp_camera_fb_return(fb);
            }
            flashOff();
        }
        else if (strcmp(cmd, "snapshot_hd") == 0) {
            // Temporarily switch to HD for a single capture
            sensor_t* s = esp_camera_sensor_get();
            framesize_t prevSize = (framesize_t)s->status.framesize;
            s->set_framesize(s, FRAMESIZE_SXGA);
            delay(300);
            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                totalCaptures++;
                uploadImageToAI(fb, "hd_snapshot");
                esp_camera_fb_return(fb);
            }
            s->set_framesize(s, prevSize);
        }
        else if (strcmp(cmd, "resolution") == 0) {
            sensor_t* s = esp_camera_sensor_get();
            int res = doc["value"] | 8; // Default VGA
            s->set_framesize(s, (framesize_t)res);
        }
        else if (strcmp(cmd, "heartbeat") == 0) {
            sendCamHeartbeat();
        }
    }
}

// ============================================
// MQTT Connection
// ============================================
bool connectMQTT() {
    Serial.printf("[MQTT] Connecting to %s...\n", MQTT_BROKER);
    
    String willMsg = "{\"status\":\"offline\",\"camera\":\"" + String(MQTT_CLIENT_ID) + "\"}";
    
    if (mqtt.connect(MQTT_CLIENT_ID, MQTT_USER, MQTT_PASSWORD,
                     TOPIC_CAM_STATUS, 1, true, willMsg.c_str())) {
        Serial.println("[MQTT] Connected!");
        
        mqtt.subscribe(TOPIC_CAM_COMMAND);
        mqtt.subscribe(TOPIC_JARVIS_CAM_CMD);
        
        // Publish online status with Jarvis info
        StaticJsonDocument<512> doc;
        doc["status"]      = "online";
        doc["camera"]      = MQTT_CLIENT_ID;
        doc["firmware"]    = FIRMWARE_VERSION;
        doc["ip"]          = WiFi.localIP().toString();
        doc["stream_url"]  = "http://" + WiFi.localIP().toString() + ":81/stream";
        doc["capture_url"] = "http://" + WiFi.localIP().toString() + "/capture";
        doc["psram"]       = psramFound();
        doc["jarvis"]      = true;
        doc["patrol"]      = jarvisPatrolMode;
        doc["intruder"]    = jarvisIntruderMode;
        doc["night_mode"]  = nightModeActive;
        
        char buffer[512];
        serializeJson(doc, buffer);
        mqtt.publish(TOPIC_CAM_STATUS, buffer, true);
        
        // Initial heartbeat
        sendCamHeartbeat();
        
        return true;
    }
    
    Serial.printf("[MQTT] Failed: %d\n", mqtt.state());
    return false;
}

void handleMQTTReconnect() {
    static unsigned long lastRetry = 0;
    if (!mqtt.connected() && millis() - lastRetry > 5000) {
        lastRetry = millis();
        connectMQTT();
    }
}

// ============================================
// Periodic Status Publish (Jarvis-Enhanced)
// ============================================
void publishStatus() {
    static unsigned long lastPublish = 0;
    if (millis() - lastPublish < 10000) return;
    lastPublish = millis();
    
    StaticJsonDocument<512> doc;
    doc["camera"]        = MQTT_CLIENT_ID;
    doc["status"]        = "online";
    doc["fps"]           = currentFPS;
    doc["streaming"]     = streamActive;
    doc["motion_detect"] = motionDetectEnabled;
    doc["face_detect"]   = faceDetectEnabled;
    doc["timelapse"]     = timelapseActive;
    doc["flash"]         = flashIntensity;
    doc["motion_events"] = motionEventCount;
    doc["free_heap"]     = ESP.getFreeHeap();
    doc["free_psram"]    = ESP.getFreePsram();
    doc["uptime"]        = millis() / 1000;
    doc["rssi"]          = WiFi.RSSI();
    doc["ip"]            = WiFi.localIP().toString();
    doc["patrol"]        = jarvisPatrolMode;
    doc["intruder_mode"] = jarvisIntruderMode;
    doc["night_mode"]    = nightModeActive;
    doc["ambient"]       = ambientLight;
    doc["persons"]       = personCount;
    doc["captures"]      = totalCaptures;
    doc["uploads"]       = totalUploads;
    
    char buffer[512];
    serializeJson(doc, buffer);
    mqtt.publish(TOPIC_CAM_STATUS, buffer);
}

// ============================================
// Jarvis Endpoints for HTTP Server
// ============================================
esp_err_t jarvisStatusHandler(httpd_req_t* req) {
    StaticJsonDocument<512> doc;
    doc["device"]        = MQTT_CLIENT_ID;
    doc["firmware"]      = FIRMWARE_VERSION;
    doc["uptime"]        = millis() / 1000;
    doc["free_heap"]     = ESP.getFreeHeap();
    doc["free_psram"]    = ESP.getFreePsram();
    doc["rssi"]          = WiFi.RSSI();
    doc["ip"]            = WiFi.localIP().toString();
    doc["streaming"]     = streamActive;
    doc["fps"]           = currentFPS;
    doc["motion"]        = motionDetectEnabled;
    doc["night_mode"]    = nightModeActive;
    doc["ambient"]       = ambientLight;
    doc["patrol"]        = jarvisPatrolMode;
    doc["intruder_mode"] = jarvisIntruderMode;
    doc["persons"]       = personCount;
    doc["motion_events"] = motionEventCount;
    doc["captures"]      = totalCaptures;
    doc["detections"]    = aiDetectionCount;
    doc["last_ai"]       = lastAIResult.substring(0, 200);
    
    char buf[512];
    serializeJson(doc, buf);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, buf, strlen(buf));
}

esp_err_t jarvisCaptureDetectHandler(httpd_req_t* req) {
    // Single-shot: capture + upload to AI + return results
    if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
    delay(200);
    
    camera_fb_t* fb = esp_camera_fb_get();
    flashOff();
    
    if (!fb) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    
    totalCaptures++;
    uploadImageToAI(fb, "jarvis_detect");
    
    esp_camera_fb_return(fb);
    
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    
    if (lastAIResult.length() > 0) {
        return httpd_resp_send(req, lastAIResult.c_str(), lastAIResult.length());
    }
    return httpd_resp_sendstr(req, "{\"status\":\"captured\",\"ai\":\"pending\"}");
}

// ============================================
// Setup
// ============================================
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(1000);
    
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════╗");
    Serial.println("║   Vision-AI ESP32-CAM v" FIRMWARE_VERSION "        ║");
    Serial.println("╠══════════════════════════════════════╣");
    Serial.println("║  Jarvis Vision Processing Module     ║");
    Serial.println("╚══════════════════════════════════════╝");
    Serial.println();
    
    // Initialize flash LED first
    setupFlash();
    
    // Blink to show startup
    flashOn(); delay(200); flashOff();
    
    // Initialize camera
    if (!initCamera()) {
        Serial.println("[FATAL] Camera init failed!");
        flashOn(); // Keep flash on to indicate error
        while (1) delay(1000);
    }
    
    // Connect WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
    
    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_CONNECT_TIMEOUT) {
        delay(500);
        Serial.print(".");
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n[WiFi] Connected! IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("[WiFi] Signal: %d dBm\n", WiFi.RSSI());
    } else {
        Serial.println("\n[WiFi] Connection failed!");
    }
    
    // Start HTTP servers
    startCaptureServer();
    startStreamServer();
    
    // Setup MQTT
    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(mqttCallback);
    mqtt.setKeepAlive(MQTT_KEEPALIVE);
    mqtt.setBufferSize(MQTT_BUFFER_SIZE);
    connectMQTT();
    
    // Watchdog
    esp_task_wdt_init(WDT_TIMEOUT, true);
    esp_task_wdt_add(NULL);
    
    Serial.println("\n[Setup] ✓ Jarvis Camera module ready!");
    Serial.printf("[URLs] Stream:  http://%s:%d/stream\n", WiFi.localIP().toString().c_str(), STREAM_PORT);
    Serial.printf("[URLs] Capture: http://%s/capture\n", WiFi.localIP().toString().c_str());
    Serial.printf("[URLs] Status:  http://%s/status\n", WiFi.localIP().toString().c_str());
    Serial.printf("[URLs] Jarvis:  http://%s/jarvis/status\n", WiFi.localIP().toString().c_str());
    Serial.printf("[URLs] Detect:  http://%s/jarvis/detect\n", WiFi.localIP().toString().c_str());
    Serial.println();
    
    // Indicate ready
    flashOn(); delay(100); flashOff(); delay(100);
    flashOn(); delay(100); flashOff();
}

// ============================================
// Main Loop (Jarvis-Enhanced)
// ============================================
void loop() {
    // Reset watchdog
    esp_task_wdt_reset();
    
    // Handle MQTT
    mqtt.loop();
    handleMQTTReconnect();
    
    // Publish periodic status
    publishStatus();
    
    // Handle timelapse
    handleTimelapse();
    
    // Handle patrol mode
    handlePatrol();
    
    // Periodic heartbeat to Jarvis
    if (millis() - lastHeartbeat >= CAM_HEARTBEAT_INTERVAL) {
        lastHeartbeat = millis();
        sendCamHeartbeat();
    }
    
    // WiFi reconnect
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastWifiRetry = 0;
        if (millis() - lastWifiRetry > WIFI_RECONNECT_INTERVAL) {
            lastWifiRetry = millis();
            Serial.println("[WiFi] Reconnecting...");
            WiFi.reconnect();
        }
    }
    
    // Periodic motion check (when not streaming)
    if (!streamActive && motionDetectEnabled) {
        static unsigned long lastCheck = 0;
        if (millis() - lastCheck > 500) {
            lastCheck = millis();
            camera_fb_t* fb = esp_camera_fb_get();
            if (fb) {
                // Night vision auto-detect
                handleNightMode(fb);
                
                bool motion = detectMotion(fb);
                if (motion && MOTION_AUTO_CAPTURE) {
                    // Auto-capture on motion and send to AI
                    totalCaptures++;
                    if (nightModeActive) setFlash(NIGHT_FLASH_LEVEL);
                    uploadImageToAI(fb, "motion_trigger");
                    flashOff();
                }
                esp_camera_fb_return(fb);
            }
        }
    }
    
    // Periodic person count publish
    if (millis() - lastPersonPublish >= PERSON_COUNT_PUBLISH_MS) {
        lastPersonPublish = millis();
        if (personCount > 0) {
            StaticJsonDocument<128> doc;
            doc["persons"] = personCount;
            doc["camera"]  = MQTT_CLIENT_ID;
            doc["night"]   = nightModeActive;
            char buf[128];
            serializeJson(doc, buf);
            mqtt.publish(TOPIC_JARVIS_CAM_PERSON, buf);
        }
    }
    
    delay(1);
}
