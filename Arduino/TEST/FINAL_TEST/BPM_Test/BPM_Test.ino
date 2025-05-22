/*
  Optical Heart Rate Detection (PBA Algorithm) using the MAX30105 Breakout
  1602 LCD output (avg BPM init 80, display after 10s)
*/

#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <LiquidCrystal.h>

MAX30105 particleSensor;
// LCD pins: RS=A0, E=A1, D4=4, D5=5, D6=6, D7=7
LiquidCrystal lcd(A0, A1, 4, 5, 6, 7);

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
int beatAvg = 80;
unsigned long fingerStartTime = 0;

void setup()
{
    Serial.begin(9600);
    lcd.begin(16, 2);
    lcd.print("Initializing...");

    if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
    {
        lcd.clear();
        lcd.print("Sensor not found");
        while (1);
    }

    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);

    for (byte i = 0; i < RATE_SIZE; i++)
    {
        rates[i] = 80;
    }

    beatAvg = 80;
    lastBeat = millis();

    lcd.clear();
}

void loop()
{
    long irValue = particleSensor.getIR();

    if (checkForBeat(irValue))
    {
        long delta = millis() - lastBeat;
        lastBeat = millis();
        float bpm = 60.0 / (delta / 1000.0);

        if (bpm > 20 && bpm < 255)
        {
            rates[rateSpot++] = (byte)bpm;
            rateSpot %= RATE_SIZE;

            int sum = 0;
            for (byte i = 0; i < RATE_SIZE; i++)
            {
                sum += rates[i];
            }

            beatAvg = sum / RATE_SIZE;
        }
    }

    if (irValue >= 50000)
    {
        if (fingerStartTime == 0)
        {
            fingerStartTime = millis();
        }
    }
    else
    {
        fingerStartTime = 0;
    }

    Serial.print("Avg BPM: ");
    Serial.println(beatAvg);

    lcd.setCursor(0, 0);

    if (fingerStartTime == 0)
    {
        lcd.print("No finger      ");
        lcd.setCursor(0, 1);
        lcd.print("                ");
    }
    else if (millis() - fingerStartTime < 10000)
    {
        lcd.print("Collecting...  ");
        lcd.setCursor(0, 1);
        lcd.print("                ");
    }
    else
    {
        lcd.clear();
        lcd.print("BPM:");
        lcd.print(beatAvg);
        lcd.setCursor(0, 1);
        lcd.print("                ");
    }
}
