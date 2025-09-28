/*
 * ESP32-S3 Golf Club Sensor - Simple Version
 * Displays raw gyroscope and accelerometer data in Serial Monitor
 * No WiFi - just sensor data output
 */

#include <Wire.h>

// MPU6050 I2C address
#define MPU_ADDR 0x68

// MPU6050 register addresses
#define PWR_MGMT_1 0x6B
#define SMPLRT_DIV 0x19
#define CONFIG 0x1A
#define GYRO_CONFIG 0x1B
#define ACCEL_CONFIG 0x1C
#define ACCEL_XOUT_H 0x3B
#define GYRO_XOUT_H 0x43

// Calibration data
float gyroXCal = 0, gyroYCal = 0, gyroZCal = 0;
bool calibrated = false;

// Absolute gyro values (accumulated rotation)
float absGyroX = 0, absGyroY = 0, absGyroZ = 0;
unsigned long lastTime = 0;

void setup() {
  Serial.begin(115200);
  
  // I2C pin configuration
  Wire.begin(4, 5); // SDA=4, SCL=5 - change these if needed
  
  // Initialize MPU
  initializeMPU();
  
  // Calibrate gyroscope
  calibrateGyro();
  
  Serial.println("ESP32-S3 Golf Club Sensor Ready!");
  Serial.println("Raw sensor data will be displayed below:");
  Serial.println("Format: Accel(X,Y,Z) Gyro Rate(X,Y,Z) Abs Gyro(X,Y,Z) Temp(°C)");
  Serial.println("Abs Gyro shows total rotation since startup (in degrees)");
  Serial.println("----------------------------------------");
}

void loop() {
  // Read sensor data
  float accelX, accelY, accelZ;
  float gyroX, gyroY, gyroZ;
  float temperature;
  
  // Read accelerometer data
  readAccelData(&accelX, &accelY, &accelZ);
  
  // Read gyroscope data
  readGyroData(&gyroX, &gyroY, &gyroZ);
  
  // Apply calibration
  if (calibrated) {
    gyroX -= gyroXCal;
    gyroY -= gyroYCal;
    gyroZ -= gyroZCal;
  }
  
  // Calculate time delta for integration
  unsigned long currentTime = millis();
  float deltaTime = (currentTime - lastTime) / 1000.0; // Convert to seconds
  lastTime = currentTime;
  
  // Integrate gyro values to get absolute rotation
  absGyroX += gyroX * deltaTime;
  absGyroY += gyroY * deltaTime;
  absGyroZ += gyroZ * deltaTime;
  
  // Read temperature
  temperature = readTemperature();
  
  // Display data with absolute gyro values
  Serial.print("Accel: ");
  Serial.print(accelX, 3);
  Serial.print(", ");
  Serial.print(accelY, 3);
  Serial.print(", ");
  Serial.print(accelZ, 3);
  Serial.print(" | Gyro Rate: ");
  Serial.print(gyroX, 3);
  Serial.print(", ");
  Serial.print(gyroY, 3);
  Serial.print(", ");
  Serial.print(gyroZ, 3);
  Serial.print(" | Abs Gyro: ");
  Serial.print(absGyroX, 3);
  Serial.print(", ");
  Serial.print(absGyroY, 3);
  Serial.print(", ");
  Serial.print(absGyroZ, 3);
  Serial.print(" | Temp: ");
  Serial.print(temperature, 2);
  Serial.println("°C");
  
  delay(100); // 10Hz sampling rate
}

void initializeMPU() {
  // Wake up MPU
  writeRegister(MPU_ADDR, PWR_MGMT_1, 0x00);
  delay(100);
  
  // Set sample rate to 1kHz
  writeRegister(MPU_ADDR, SMPLRT_DIV, 0x07);
  
  // Configure accelerometer (±2g)
  writeRegister(MPU_ADDR, ACCEL_CONFIG, 0x00);
  
  // Configure gyroscope (±250°/s)
  writeRegister(MPU_ADDR, GYRO_CONFIG, 0x00);
  
  // Configure DLPF
  writeRegister(MPU_ADDR, CONFIG, 0x06);
  
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
  
  calibrated = true;
  Serial.println("Gyroscope calibrated");
  Serial.print("Calibration values: X=");
  Serial.print(gyroXCal, 3);
  Serial.print(", Y=");
  Serial.print(gyroYCal, 3);
  Serial.print(", Z=");
  Serial.println(gyroZCal, 3);
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
