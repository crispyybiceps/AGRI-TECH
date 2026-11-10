# ESP32 IoT Soil Telemetry Node: Wiring and Firmware

This document describes the Tier 4 IoT hardware integration for AGRI-TECH. An ESP32 microcontroller collects soil moisture, temperature, and pH values in the field and posts them over HTTPS to the backend.

---

## 1. Hardware Bill of Materials (BOM)

| Component | Purpose | Pins / Interface |
|---|---|---|
| **ESP32 NodeMCU / DevKit v1** | Microcontroller with WiFi and SSL support | 3.3V, GND, GPIO |
| **Capacitive Soil Moisture Sensor v1.2** | Corrosion-resistant analog moisture sensing | VCC (3.3V), GND, AOUT -> GPIO 34 |
| **DS18B20 Waterproof Temperature Sensor** | Soil temperature probe | VCC (3.3V), GND, DATA -> GPIO 4 (4.7kΩ pullup) |
| **Analog pH Sensor Probe (pH-4502C)** | Soil pH measurement | VCC (5.0V), GND, PO -> GPIO 35 |
| **3.7V 18650 Li-Ion Battery + Solar Panel (5V 2W)** | Off-grid power supply | TP4056 charging module |

---

## 2. Wiring Diagram

```
+-------------------------------------------------------------+
|                        ESP32 DevKit                         |
|                                                             |
|   3V3  -----------------+------------+                      |
|                         |            |                      |
|   GND  ----+------------+------------+                      |
|            |            |            |                      |
|   GPIO 34 -+-- [Moisture Sensor AOUT]|                      |
|            |                         |                      |
|   GPIO 4  -+-- [DS18B20 Data] -------+                      |
|            |       |                                        |
|            |   (4.7k Pullup to 3V3)                         |
|            |                                                |
|   GPIO 35 -+-- [pH Sensor Analog PO]                        |
|                                                             |
|   VIN (5V) --- [pH Sensor VCC]                              |
+-------------------------------------------------------------+
```

---

## 3. Registering the Device in AGRI-TECH

Before uploading code to the ESP32:
1. Log into AGRI-TECH and go to **My Soil**.
2. Click **Register IoT Device**.
3. Provide a device identifier, e.g., `ESP32_PUNE_NODE_01`.
4. Copy the generated **X-Device-Key** (e.g. `agri_node_9a4f...`).
5. Paste this key into the sketch below.

---

## 4. Arduino ESP32 Firmware Sketch

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// WiFi Configuration
const char* WIFI_SSID     = "Your_Farm_WiFi_or_Hotspot";
const char* WIFI_PASSWORD = "Your_WiFi_Password";

// AGRI-TECH API Configuration
const char* SERVER_URL    = "https://your-agritech-server.com/sensors/readings";
const char* SENSOR_ID     = "ESP32_PUNE_NODE_01";
const char* DEVICE_API_KEY= "agri_node_YOUR_GENERATED_SECRET_KEY";

// Pin Assignments
#define MOISTURE_PIN 34
#define PH_PIN       35
#define ONE_WIRE_BUS 4

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);

// Calibration Constants
const int AIR_VALUE   = 3200; // Dry air analog reading
const int WATER_VALUE = 1400; // Submerged analog reading

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("[AGRI-TECH] Booting ESP32 Soil Node...");

  tempSensor.begin();

  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected! IP: " + WiFi.localIP().toString());
}

float readMoisturePercentage() {
  int raw = analogRead(MOISTURE_PIN);
  float pct = map(raw, AIR_VALUE, WATER_VALUE, 0, 100);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

float readSoilTemperature() {
  tempSensor.requestTemperatures();
  float tempC = tempSensor.getTempCByIndex(0);
  if (tempC == DEVICE_DISCONNECTED_C) return 25.0; // Fallback
  return tempC;
}

float readSoilPH() {
  int raw = analogRead(PH_PIN);
  float voltage = raw * (3.3 / 4095.0);
  // Standard two-point calibration formula: pH = 7.0 + ((2.5 - voltage) / 0.18)
  float ph = 7.0 + ((2.5 - voltage) / 0.18);
  if (ph < 3.0) ph = 3.0;
  if (ph > 10.0) ph = 10.0;
  return ph;
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    float moisture    = readMoisturePercentage();
    float temperature = readSoilTemperature();
    float ph          = readSoilPH();
    float conductivity= 0.45; // dS/m standard Vertisol benchmark

    Serial.printf("Telemetry: Moisture=%.1f%%, Temp=%.1f C, pH=%.2f\n", moisture, temperature, ph);

    WiFiClientSecure client;
    client.setInsecure(); // For dev self-signed certs; use root CA in production

    HTTPClient http;
    http.begin(client, SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Key", DEVICE_API_KEY);

    // Build JSON payload
    String payload = "{";
    payload += "\"sensor_id\":\"" + String(SENSOR_ID) + "\",";
    payload += "\"moisture\":" + String(moisture, 1) + ",";
    payload += "\"temperature\":" + String(temperature, 1) + ",";
    payload += "\"ph\":" + String(ph, 2) + ",";
    payload += "\"conductivity\":" + String(conductivity, 2);
    payload += "}";

    int httpCode = http.POST(payload);
    if (httpCode > 0) {
      String response = http.getString();
      Serial.printf("HTTP %d: %s\n", httpCode, response.c_str());
    } else {
      Serial.printf("HTTP Error: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected! Reconnecting...");
    WiFi.reconnect();
  }

  // Sleep 15 minutes before next telemetry transmission
  Serial.println("Entering 15-minute telemetry sleep...");
  delay(15 * 60 * 1000);
}
```

---

## 5. Security & Anomaly Detection

- **Hashed Key Storage**: Raw API keys are never stored in the database. Only SHA-256 digests are verified.
- **Out-of-Range Anomaly Alerting**: The AGRI-TECH backend flags telemetry readings with `is_anomaly=True` if:
  - Moisture < 5% or > 95%
  - pH < 4.0 or > 9.5
  - Temperature < 0°C or > 55°C

