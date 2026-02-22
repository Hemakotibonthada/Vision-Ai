#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// Vision-AI + Jarvis  ESP32 Server Configuration
// ============================================
// v3.0 — Enhanced with Jarvis AI integration,
//         door sensor, IR blaster, servo lock,
//         scheduled tasks, and heartbeat system.
// ============================================

// ---------- WiFi Configuration ----------
#define WIFI_SSID           "VisionAI-Network"
#define WIFI_PASSWORD       "vision2024secure"
#define WIFI_AP_SSID        "VisionAI-Server"
#define WIFI_AP_PASSWORD    "setup12345"
#define WIFI_AP_CHANNEL     6
#define WIFI_AP_MAX_CONN    4
#define WIFI_CONNECT_TIMEOUT 15000
#define WIFI_RECONNECT_INTERVAL 5000
#define WIFI_MAX_RETRIES    10

// ---------- MQTT Configuration ----------
#define MQTT_BROKER         "192.168.1.100"
#define MQTT_PORT           1883
#define MQTT_USER           "vision_server"
#define MQTT_PASSWORD       "mqtt_pass_2024"
#define MQTT_CLIENT_ID      "esp32-server-01"
#define MQTT_KEEPALIVE      60
#define MQTT_QOS            1
#define MQTT_RETAIN         false
#define MQTT_RECONNECT_DELAY 3000
#define MQTT_MAX_PACKET     4096

// MQTT Topics — legacy
#define TOPIC_PREFIX        "vision-ai/"
#define TOPIC_STATUS        TOPIC_PREFIX "server/status"
#define TOPIC_SENSOR        TOPIC_PREFIX "server/sensors"
#define TOPIC_COMMAND       TOPIC_PREFIX "server/command"
#define TOPIC_ALERT         TOPIC_PREFIX "server/alert"
#define TOPIC_CONFIG        TOPIC_PREFIX "server/config"
#define TOPIC_CAMERA_CMD    TOPIC_PREFIX "camera/command"
#define TOPIC_CAMERA_STATUS TOPIC_PREFIX "camera/status"
#define TOPIC_AI_RESULT     TOPIC_PREFIX "ai/result"
#define TOPIC_AI_TRAINING   TOPIC_PREFIX "ai/training"
#define TOPIC_SYSTEM        TOPIC_PREFIX "system/health"
#define TOPIC_OTA           TOPIC_PREFIX "system/ota"
#define TOPIC_LOG           TOPIC_PREFIX "system/log"
#define TOPIC_DEVICE_DISC   TOPIC_PREFIX "discovery"

// MQTT Topics — Jarvis integration
#define TOPIC_JARVIS_PREFIX TOPIC_PREFIX "jarvis/"
#define TOPIC_JARVIS_CMD    TOPIC_JARVIS_PREFIX "command"
#define TOPIC_JARVIS_STATE  TOPIC_JARVIS_PREFIX "state"
#define TOPIC_JARVIS_EVENT  TOPIC_JARVIS_PREFIX "event"
#define TOPIC_JARVIS_DOOR   TOPIC_JARVIS_PREFIX "door"
#define TOPIC_JARVIS_MOTION TOPIC_JARVIS_PREFIX "motion"
#define TOPIC_JARVIS_RELAY  TOPIC_JARVIS_PREFIX "relay"
#define TOPIC_JARVIS_SENSOR TOPIC_JARVIS_PREFIX "sensor"
#define TOPIC_JARVIS_ALERT  TOPIC_JARVIS_PREFIX "alert"
#define TOPIC_JARVIS_LOCK   TOPIC_JARVIS_PREFIX "lock"
#define TOPIC_JARVIS_IR     TOPIC_JARVIS_PREFIX "ir"
#define TOPIC_JARVIS_SCHED  TOPIC_JARVIS_PREFIX "schedule"
#define TOPIC_JARVIS_HEARTBEAT TOPIC_JARVIS_PREFIX "heartbeat"
#define TOPIC_JARVIS_OTA    TOPIC_JARVIS_PREFIX "ota"

// ---------- Web Server Configuration ----------
#define HTTP_PORT           80
#define WS_PORT             81
#define API_PREFIX          "/api/v1"
#define MAX_WS_CLIENTS      8
#define WS_PING_INTERVAL    30000

// ---------- NTP Configuration ----------
#define NTP_SERVER_1        "pool.ntp.org"
#define NTP_SERVER_2        "time.nist.gov"
#define NTP_GMT_OFFSET      19800   // IST +5:30
#define NTP_DAYLIGHT_OFFSET 0

// ---------- GPIO Pin Assignments ----------
#define PIN_DHT             4       // DHT11 sensor
#define PIN_PIR             13      // PIR motion sensor
#define PIN_TRIGGER         12      // Ultrasonic trigger
#define PIN_ECHO            14      // Ultrasonic echo
#define PIN_LDR             36      // LDR analog (VP)
#define PIN_BUZZER          25      // Buzzer
#define PIN_STATUS_LED      23      // Status LED
#define PIN_BUTTON          5       // Button

// ---------- Door Sensor (magnetic reed switch) ----------
#define PIN_DOOR_SENSOR     27      // GPIO27 — magnetic reed switch
#define DOOR_DEBOUNCE_MS    200     // debounce time

// ---------- Servo Lock ----------
#define PIN_SERVO_LOCK      26      // GPIO26 — SG90 servo for door lock
#define SERVO_LOCK_ANGLE    10      // locked position (degrees)
#define SERVO_UNLOCK_ANGLE  90      // unlocked position (degrees)
#define SERVO_CHANNEL       1
#define SERVO_FREQ          50      // 50 Hz PWM for servo

// ---------- IR Blaster (optional — controls AC/TV) ----------
#define PIN_IR_LED          33      // IR LED transmitter
#define IR_ENABLED          true

// ---------- 8-Relay Pin Assignments ----------
#define RELAY_COUNT         8
const uint8_t RELAY_PINS[RELAY_COUNT] = {2, 15, 16, 17, 18, 19, 21, 22};

// Room names mapped to relays (index 0-7)
const char* const ROOM_NAMES[RELAY_COUNT] = {
    "Living Room", "Bedroom", "Kitchen", "Bathroom",
    "Garage", "Porch", "Study", "Spare"
};

// Relay active-low flag (set true if your relay module is active-LOW)
#define RELAY_ACTIVE_LOW    true

// ---------- Voltage/Current Sensor ----------
#define PIN_VOLTAGE_SENSOR  34      // Voltage divider ADC input
#define PIN_CURRENT_SENSOR  35      // ACS712 current sensor ADC
#define VOLTAGE_DIVIDER_R1  30000.0 // 30kΩ top resistor
#define VOLTAGE_DIVIDER_R2  7500.0  // 7.5kΩ bottom resistor
#define ACS712_SENSITIVITY  0.185   // 185mV/A for ACS712-5A (use 0.1 for 20A, 0.066 for 30A)
#define ACS712_OFFSET       2.5     // Zero-current output voltage (Vcc/2)
#define ADC_VREF            3.3     // ESP32 ADC reference voltage
#define ADC_RESOLUTION      4095.0  // 12-bit ADC

// ---------- EEPROM Configuration ----------
#define EEPROM_SIZE         1024
#define EEPROM_USERNAME_ADDR    0   // 32 bytes for username
#define EEPROM_PASSWORD_ADDR    32  // 32 bytes for password
#define EEPROM_RELAY_ADDR       64  // 8 bytes for relay states (1 byte per relay)
#define EEPROM_BIRTHDAY_ADDR    96  // 32 bytes for birthday
#define EEPROM_SCENE_ADDR       128 // Scene data (5 scenes × 8 bytes = 40 bytes)
#define EEPROM_SCHEDULE_ADDR    256 // Schedule data (16 schedules × 16 bytes = 256 bytes)
#define EEPROM_LOCK_STATE_ADDR  520 // 1 byte — lock state
#define EEPROM_BOOT_COUNT_ADDR  524 // 4 bytes — boot counter

// ---------- Schedule System ----------
#define MAX_SCHEDULES       16
// Schedule entry packed as:  relay(1B) | hour(1B) | minute(1B) | days_bitmask(1B) |
//                            action(1B) | enabled(1B) | repeat(1B) | pad(1B)  = 8 bytes
// + scene schedules at offset +128

// ---------- Sensor Configuration ----------
#define DHT_TYPE            DHT11
#define SENSOR_READ_INTERVAL 5000   // 5 seconds
#define MOTION_DEBOUNCE     3000    // 3 seconds
#define ULTRASONIC_TIMEOUT  30000   // 30ms timeout
#define LDR_THRESHOLD       500     // Light threshold

// Sensor Alert Thresholds
#define TEMP_ALERT_HIGH     40.0    // °C
#define TEMP_ALERT_LOW      5.0     // °C
#define HUMIDITY_ALERT_HIGH 85.0    // %
#define VOLTAGE_ALERT_HIGH  260.0   // V
#define VOLTAGE_ALERT_LOW   180.0   // V
#define CURRENT_ALERT_HIGH  15.0    // A

// ---------- OTA Firmware Limits ----------
#define MAX_FIRMWARE_SIZE   1572864 // 1.5MB max firmware size for OTA

// ---------- System Configuration ----------
#define DEVICE_NAME         "VisionAI-Server"
#define FIRMWARE_VERSION    "3.0.0"
#define HARDWARE_VERSION    "2.0"
#define SERIAL_BAUD         115200
#define JSON_BUFFER_SIZE    2048
#define LOG_LEVEL           3       // 0=None, 1=Error, 2=Warn, 3=Info, 4=Debug
#define WATCHDOG_TIMEOUT    30      // seconds
#define HEALTH_CHECK_INTERVAL 10000 // 10 seconds
#define MAX_LOG_ENTRIES     100
#define HEARTBEAT_INTERVAL  15000   // 15 s — send heartbeat to Jarvis

// ---------- Power Management ----------
#define DEEP_SLEEP_TIME     300     // 5 minutes (seconds)
#define LIGHT_SLEEP_TIME    60      // 1 minute (seconds)
#define LOW_BATTERY_VOLT    3.3     // Low battery threshold

// ---------- OTA Configuration ----------
#define OTA_HOSTNAME        "vision-server"
#define OTA_PASSWORD        "ota_update_2024"
#define OTA_PORT            3232

// ---------- SD Card Configuration ----------
// NOTE: SD card disabled - SPI pins reassigned to relays
#define SD_ENABLED          false

// ---------- BLE Configuration ----------
#define BLE_DEVICE_NAME     "VisionAI-BLE"
#define BLE_SERVICE_UUID    "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define BLE_CHAR_UUID       "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// ---------- Rate Limiting ----------
#define API_RATE_LIMIT      60      // requests per minute
#define API_RATE_WINDOW     60000   // 1 minute window

// ---------- Security ----------
#define AUTH_ENABLED        true
#define AUTH_USERNAME       "admin"
#define AUTH_PASSWORD       "vision2024"
#define API_KEY             "vai_sk_2024_abcdef1234567890"
#define CORS_ORIGIN         "*"

// ---------- Jarvis AI Integration ----------
#define JARVIS_API_URL      "http://192.168.1.100:8100"
#define JARVIS_ENABLED      true
// When door opens ➜ publish TOPIC_JARVIS_DOOR ➜ Jarvis wakes camera
// When PIR fires  ➜ publish TOPIC_JARVIS_MOTION ➜ Jarvis starts face recog

#endif // CONFIG_H
