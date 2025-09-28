/*
 * ESP32-S3 Golf Club Sensor - Cleaned UDP Client
 */

#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <WiFiUdp.h>

// --- Function Declarations ---
void initializeMPU();
void calibrateGyro();
void connectToWiFi();
void readAccelData(float* x, float* y, float* z);
void readGyroData(float* x, float* y, float* z);
void sendDataToServer(float accelX, float accelY, float accelZ, float gyroX, float gyroY, float gyroZ, float absGyroX, float absGyroY, float absGyroZ);

// --- Configuration ---
const char* ssid = "qwerty";
const char* password = "qwerty12345";
const char* serverIP = "10.62.26.197"; // Your Mac's IP on the hotspot
const uint16_t serverPort = 50000;

WiFiUDP udp;

// --- MPU6050 & Sensor Variables ---
#define MPU_ADDR 0x68
#define ACCEL_XOUT_H 0x3B
#define GYRO_XOUT_H 0x43
#define PWR_MGMT_1 0x6B

float gyroXCal = 0, gyroYCal = 0, gyroZCal = 0;
float absGyroX = 0, absGyroY = 0, absGyroZ = 0;
unsigned long lastTime = 0;

// --- Main Program ---
void setup() {
  Serial.begin(115200);
  Wire.begin(4, 5); // SDA=4, SCL=5

  initializeMPU();
  connectToWiFi();
  calibrateGyro();
  
  lastTime = millis();
  Serial.println("ESP32-S3 Golf Club Sensor Ready!");
}
 
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    connectToWiFi();
    return;
  }

  float accelX, accelY, accelZ;
  readAccelData(&accelX, &accelY, &accelZ);
  
  float gyroX, gyroY, gyroZ;
  readGyroData(&gyroX, &gyroY, &gyroZ);
  
  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTime) / 1000.0;
  lastTime = currentTime;
  
  float calibratedGyroX = gyroX - gyroXCal;
  float calibratedGyroY = gyroY - gyroYCal;
  float calibratedGyroZ = gyroZ - gyroZCal;

  absGyroX += calibratedGyroX * deltaTime;
  absGyroY += calibratedGyroY * deltaTime;
  absGyroZ += calibratedGyroZ * deltaTime;

  sendDataToServer(accelX, accelY, accelZ, calibratedGyroX, calibratedGyroY, calibratedGyroZ, absGyroX, absGyroY, absGyroZ);
  
  // Use a stable delay (e.g., 50ms for 20 packets/sec)
  delay(50); 
}

// --- Functions ---
void connectToWiFi() {
  Serial.print("Connecting to WiFi...");
  WiFi.disconnect(true);
  delay(100);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(100); // Use a 500ms delay to give it time to connect
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
  }
}

void sendDataToServer(float accelX, float accelY, float accelZ, 
                      float gyroX, float gyroY, float gyroZ,
                      float absGyroX, float absGyroY, float absGyroZ) {
  JsonDocument doc;
  doc["accelerometer"]["x"] = isnan(accelX) ? 0 : accelX;
  doc["accelerometer"]["y"] = isnan(accelY) ? 0 : accelY;
  doc["accelerometer"]["z"] = isnan(accelZ) ? 0 : accelZ;
  doc["gyroscope_rate"]["x"] = isnan(gyroX) ? 0 : gyroX;
  doc["gyroscope_rate"]["y"] = isnan(gyroY) ? 0 : gyroY;
  doc["gyroscope_rate"]["z"] = isnan(gyroZ) ? 0 : gyroZ;
  doc["gyroscope_absolute"]["x"] = isnan(absGyroX) ? 0 : absGyroX;
  doc["gyroscope_absolute"]["y"] = isnan(absGyroY) ? 0 : absGyroY;
  doc["gyroscope_absolute"]["z"] = isnan(absGyroZ) ? 0 : absGyroZ;
  
  udp.beginPacket(serverIP, serverPort);
  serializeJson(doc, udp);
  udp.endPacket();
}

void initializeMPU() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(PWR_MGMT_1);
  Wire.write(0);
  Wire.endTransmission(true);
  Serial.println("MPU initialized");
}

 void calibrateGyro() {
   Serial.println("Calibrating gyroscope...");
   Serial.println("Keep the sensor still during calibration...");
   
   float sumX = 0, sumY = 0, sumZ = 0;
   int samples = 1000;
   
   for (int i = 0; i < samples; i++) {
     float gx, gy, gz;
     readGyroData(&gx, &gy, &gz);
     sumX += gx;
     sumY += gy;
     sumZ += gz;
     delay(2);
   }
   
   gyroXCal = sumX / samples;
   gyroYCal = sumY / samples;
   gyroZCal = sumZ / samples;
   
  //calibrated = true;
  //  Serial.println("Gyroscope calibrated");
  //  Serial.print("Calibration values: X=");
  //  Serial.print(gyroXCal, 3);
  //  Serial.print(", Y=");
  //  Serial.print(gyroYCal, 3);
  //  Serial.print(", Z=");
  //  Serial.println(gyroZCal, 3);
 }
 
 void readAccelData(float* x, float* y, float* z) {
   Wire.beginTransmission(MPU_ADDR);
   Wire.write(ACCEL_XOUT_H);
   Wire.endTransmission(false);
   Wire.requestFrom(MPU_ADDR, 6, true);
   
   int16_t accelX = (Wire.read() << 8) | Wire.read();
   int16_t accelY = (Wire.read() << 8) | Wire.read();
   int16_t accelZ = (Wire.read() << 8) | Wire.read();
   
   // Convert to g (assuming ±2g range)
   *x = accelX / 16384.0;
   *y = accelY / 16384.0;
   *z = accelZ / 16384.0;
 }
 
 void readGyroData(float* x, float* y, float* z) {
   Wire.beginTransmission(MPU_ADDR);
   Wire.write(GYRO_XOUT_H);
   Wire.endTransmission(false);
   Wire.requestFrom(MPU_ADDR, 6, true);
   
   int16_t gyroX = (Wire.read() << 8) | Wire.read();
   int16_t gyroY = (Wire.read() << 8) | Wire.read();
   int16_t gyroZ = (Wire.read() << 8) | Wire.read();
   
   // Convert to °/s (assuming ±250°/s range)
   *x = gyroX / 131.0;
   *y = gyroY / 131.0;
   *z = gyroZ / 131.0;
 }
 
 float readTemperature() {
   Wire.beginTransmission(MPU_ADDR);
   Wire.write(0x41); // TEMP_OUT_H register
   Wire.endTransmission(false);
   Wire.requestFrom(MPU_ADDR, 2, true);
   
   int16_t temp = (Wire.read() << 8) | Wire.read();
   return (temp / 340.0) + 36.53;
 }
 
void writeRegister(uint8_t deviceAddress, uint8_t address, uint8_t val) {
  Wire.beginTransmission(deviceAddress);
  Wire.write(address);
  Wire.write(val);
  Wire.endTransmission();
}
