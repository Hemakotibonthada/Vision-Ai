#ifndef CAM_CONFIG_H
#define CAM_CONFIG_H

// ============================================
// Vision-AI ESP32-CAM Configuration v3.0
// Jarvis Integration + Advanced Vision
// ============================================

// ---------- WiFi ----------
#define WIFI_SSID           "VisionAI-Network"
#define WIFI_PASSWORD       "vision2024secure"
#define WIFI_CONNECT_TIMEOUT 15000
#define WIFI_RECONNECT_INTERVAL 10000

// ---------- MQTT ----------
#define MQTT_BROKER         "192.168.1.100"
#define MQTT_PORT           1883
#define MQTT_USER           "vision_cam"
#define MQTT_PASSWORD       "mqtt_pass_2024"
#define MQTT_CLIENT_ID      "esp32-cam-01"
#define MQTT_KEEPALIVE      60
#define MQTT_BUFFER_SIZE    4096

// ---------- MQTT Topics ----------
#define TOPIC_PREFIX        "vision-ai/"
#define TOPIC_CAM_STATUS    TOPIC_PREFIX "camera/status"
#define TOPIC_CAM_COMMAND   TOPIC_PREFIX "camera/command"
#define TOPIC_CAM_IMAGE     TOPIC_PREFIX "camera/image"
#define TOPIC_CAM_MOTION    TOPIC_PREFIX "camera/motion"
#define TOPIC_CAM_FACE      TOPIC_PREFIX "camera/face"
#define TOPIC_CAM_SETTINGS  TOPIC_PREFIX "camera/settings"
#define TOPIC_AI_INFERENCE  TOPIC_PREFIX "ai/inference"
#define TOPIC_SERVER_STATUS TOPIC_PREFIX "server/status"

// Jarvis-specific topics
#define TOPIC_JARVIS_CAM_CMD    TOPIC_PREFIX "jarvis/camera/cmd"
#define TOPIC_JARVIS_CAM_EVENT  TOPIC_PREFIX "jarvis/camera/event"
#define TOPIC_JARVIS_CAM_PERSON TOPIC_PREFIX "jarvis/camera/person"
#define TOPIC_JARVIS_CAM_ALERT  TOPIC_PREFIX "jarvis/camera/alert"
#define TOPIC_JARVIS_CAM_HEARTBEAT TOPIC_PREFIX "jarvis/camera/heartbeat"
#define TOPIC_JARVIS_INTRUDER   TOPIC_PREFIX "jarvis/intruder"
#define TOPIC_JARVIS_FACE_ID    TOPIC_PREFIX "jarvis/face/identified"
#define TOPIC_JARVIS_DOORBELL   TOPIC_PREFIX "jarvis/doorbell"
#define TOPIC_JARVIS_PATROL     TOPIC_PREFIX "jarvis/patrol"

// ---------- Camera Pin Config (AI-Thinker) ----------
#define PWDN_GPIO_NUM       32
#define RESET_GPIO_NUM      -1
#define XCLK_GPIO_NUM       0
#define SIOD_GPIO_NUM       26
#define SIOC_GPIO_NUM       27
#define Y9_GPIO_NUM         35
#define Y8_GPIO_NUM         34
#define Y7_GPIO_NUM         39
#define Y6_GPIO_NUM         36
#define Y5_GPIO_NUM         21
#define Y4_GPIO_NUM         19
#define Y3_GPIO_NUM         18
#define Y2_GPIO_NUM         5
#define VSYNC_GPIO_NUM      25
#define HREF_GPIO_NUM       23
#define PCLK_GPIO_NUM       22

// ---------- Flash LED ----------
#define FLASH_LED_PIN       4
#define FLASH_LED_CHANNEL   7

// ---------- PIR Sensor (external, optional) ----------
#define PIR_PIN             13   // External PIR wired to GPIO13 (if available)
#define PIR_ENABLED         false

// ---------- Camera Defaults ----------
#define DEFAULT_RESOLUTION  FRAMESIZE_VGA   // 640x480
#define DEFAULT_QUALITY     12              // 10-63 (lower = better)
#define DEFAULT_BRIGHTNESS  0               // -2 to 2
#define DEFAULT_CONTRAST    0               // -2 to 2
#define DEFAULT_SATURATION  0               // -2 to 2
#define DEFAULT_SHARPNESS   0               // -2 to 2
#define DEFAULT_WB_MODE     0               // 0=Auto
#define DEFAULT_EFFECT      0               // 0=None
#define DEFAULT_HMIRROR     0
#define DEFAULT_VFLIP       0

// ---------- Stream ----------
#define STREAM_PORT         81
#define STREAM_FPS          15
#define STREAM_QUALITY      12
#define MAX_STREAM_CLIENTS  3

// ---------- Motion Detection ----------
#define MOTION_THRESHOLD    20      // Pixel difference threshold
#define MOTION_MIN_AREA     500     // Minimum changed pixels
#define MOTION_COOLDOWN     3000    // ms between detections
#define MOTION_NIGHT_THRESHOLD 15   // Lower threshold for night
#define MOTION_AUTO_CAPTURE true    // Auto-capture + upload on motion

// ---------- Face Detection ----------
#define FACE_DETECT_ENABLED true
#define FACE_RECOGNIZE      true
#define MAX_FACES           10
#define FACE_ID_COUNT       7

// ---------- Person Detection / Intruder ----------
#define INTRUDER_DETECT_ENABLED  true
#define INTRUDER_ALERT_DELAY_MS  5000  // Wait before alerting (owner grace period)
#define INTRUDER_CAPTURE_COUNT   3     // Capture N frames as evidence
#define PERSON_COUNT_PUBLISH_MS  5000  // How often to publish person count

// ---------- Capture ----------
#define TIMELAPSE_INTERVAL  30000   // 30 seconds
#define BURST_COUNT         5
#define BURST_DELAY         200     // ms between burst shots

// ---------- Patrol Mode ----------
#define PATROL_ENABLED      false
#define PATROL_INTERVAL_MS  60000   // Capture every 60s in patrol mode
#define PATROL_UPLOAD       true    // Upload patrol frames to AI

// ---------- Night Vision ----------
#define NIGHT_MODE_AUTO     true
#define NIGHT_FLASH_LEVEL   80      // Flash intensity for night captures (0-255)
#define LIGHT_THRESHOLD_LOW 50      // Below this = nighttime

// ---------- AI Server ----------
#define AI_SERVER_URL       "http://192.168.1.100:8000"
#define AI_INFERENCE_PATH   "/api/v1/detect"
#define AI_UPLOAD_PATH      "/api/v1/upload"
#define AI_FACE_IDENTIFY_PATH "/api/v1/face/identify"
#define AI_TIMEOUT_MS       10000

// ---------- Jarvis Server ----------
#define JARVIS_SERVER_URL   "http://192.168.1.100:8100"
#define JARVIS_ALERT_PATH   "/api/v1/jarvis/alert"
#define JARVIS_FACE_PATH    "/api/v1/jarvis/face_event"

// ---------- Heartbeat ----------
#define CAM_HEARTBEAT_INTERVAL 15000  // 15 seconds

// ---------- System ----------
#define FIRMWARE_VERSION    "3.0.0"
#define HARDWARE_VERSION    "1.0"
#define DEVICE_NAME         "VisionAI-Camera"
#define SERIAL_BAUD         115200
#define WDT_TIMEOUT         30      // Watchdog timeout seconds

#endif // CAM_CONFIG_H
