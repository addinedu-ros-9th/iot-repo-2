#include <Wire.h>
#include <LiquidCrystal.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>

// LiquidCrystal(rs, enable, d4, d5, d6, d7)
LiquidCrystal lcd(A0, A1, 4, 5, 6, 7);

MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

#define BUFFER_SIZE 20

void setup()
{
  Serial.begin(9600);
  lcd.begin(16, 2);
  lcd.print("Initializing...");

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    lcd.clear();
    lcd.print("MAX30105 Error");
    while (1);
  }

  if (!mlx.begin()) {
    lcd.clear();
    lcd.print("MLX90614 Error");
    while (1);
  }

  particleSensor.setup();
  lcd.clear();
}

void loop()
{
  uint16_t irBuffer[BUFFER_SIZE];
  uint16_t redBuffer[BUFFER_SIZE];

  int32_t spo2, heartRate;
  int8_t validSPO2, validHeartRate;

  for (byte i = 0; i < BUFFER_SIZE; i++) {
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

  Serial.print("T:"); Serial.print(tempC);
  Serial.print(" HR:"); Serial.print(heartRate);
  Serial.print(" SPO2:"); Serial.println(spo2);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(tempC, 1);
  lcd.print((char)223);
  lcd.print("C");

  lcd.setCursor(0, 1);
  lcd.print("HR:");
  lcd.print(heartRate);
  lcd.print(" SP:");
  lcd.print(spo2);
  lcd.print("%");

  delay(2000);
}
