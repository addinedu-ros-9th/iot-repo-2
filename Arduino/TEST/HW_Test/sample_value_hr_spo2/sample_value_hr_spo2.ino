#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"

MAX30105 particleSensor;

#define MAX_BRIGHTNESS 255
#define BUFFER_SIZE 25  // 샘플 개수 줄임 (25개)

// Flash 메모리에 저장되도록 const 사용
const byte pulseLED = 11;
const byte readLED = 13;

void setup()
{
  Serial.begin(9600);

  pinMode(pulseLED, OUTPUT);
  pinMode(readLED, OUTPUT);

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println(F("MAX30105 was not found. Please check wiring/power."));
    while (1);
  }

  Serial.println(F("Attach sensor to finger with rubber band. Press any key to start conversion"));
  while (Serial.available() == 0);
  Serial.read();

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
  // 지역 변수로 이동하여 SRAM 사용 최소화
  uint16_t irBuffer[BUFFER_SIZE];
  uint16_t redBuffer[BUFFER_SIZE];

  int32_t spo2 = 0;
  int8_t validSPO2 = 0;
  int32_t heartRate = 0;
  int8_t validHeartRate = 0;

  // 25 샘플 수집
  for (byte i = 0 ; i < BUFFER_SIZE ; i++)
  {
    while (!particleSensor.available())
      particleSensor.check();

    redBuffer[i] = particleSensor.getRed();
    irBuffer[i] = particleSensor.getIR();
    particleSensor.nextSample();
  }

  // SPO2 및 심박수 계산
  maxim_heart_rate_and_oxygen_saturation(
    irBuffer, BUFFER_SIZE, redBuffer,
    &spo2, &validSPO2,
    &heartRate, &validHeartRate
  );

  // 결과 출력
  Serial.print(F("HR="));
  Serial.print(heartRate);
  Serial.print(F(", SPO2="));
  Serial.println(spo2);
}
