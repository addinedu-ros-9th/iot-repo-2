#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>

MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

#define BUFFER_SIZE 20   // 줄임 (기존 25 → 20)
#define PULSE_LED 11
#define READ_LED 13

void setup()
{
  Serial.begin(9600);

  pinMode(PULSE_LED, OUTPUT);
  pinMode(READ_LED, OUTPUT);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println(F("MAX30105 was not found. Please check wiring/power."));
    while (1);
  }

  if (!mlx.begin()) {
    Serial.println("Error connecting to MLX sensor. Check wiring.");
    while (1);
  }

  // 센서 설정
  byte ledBrightness = 60;
  byte sampleAverage = 4;
  byte ledMode = 2;        // Red + IR
  byte sampleRate = 100;
  int pulseWidth = 411;
  int adcRange = 4096;

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);
}

void loop()
{
  uint16_t irBuffer[BUFFER_SIZE];
  uint16_t redBuffer[BUFFER_SIZE];

  int32_t spo2, heartRate;
  int8_t validSPO2, validHeartRate;

  for (byte i = 0 ; i < BUFFER_SIZE ; i++)
  {
    while (!particleSensor.available())
      particleSensor.check();

    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();
  }

  maxim_heart_rate_and_oxygen_saturation(
    irBuffer, BUFFER_SIZE, redBuffer,
    &spo2, &validSPO2,
    &heartRate, &validHeartRate
  );

  float tempC = mlx.readObjectTempC();

  Serial.print(tempC); Serial.print("*C");
  Serial.print(F(", HR=")); Serial.print(heartRate);
  Serial.print(F(", SPO2=")); Serial.println(spo2);
}
