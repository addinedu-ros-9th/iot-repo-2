#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include "spo2_algorithm.h"
#include <LiquidCrystal.h>

// 센서 및 LCD 설정
MAX30105 particleSensor;
LiquidCrystal lcd(A0, A1, 4, 5, 6, 7); // RS, E, D4, D5, D6, D7

// BPM 계산용 변수
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
int beatAvg = 80;

// SpO2 계산용 버퍼 및 변수 (uint16_t로 변경)
const int SAMPLES = 50;
uint16_t irBuffer[SAMPLES];
uint16_t redBuffer[SAMPLES];
int32_t spo2;
int8_t validSPO2;
int32_t dummyHR;
int8_t dummyValidHR;
bool spO2Done = false;

// 손가락 감지 시간
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
        while (1) {}
    }

    // 센서 기본 설정
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);

    // 초기 BPM 배열 세팅
    for (byte i = 0; i < RATE_SIZE; i++) rates[i] = 80;
    beatAvg = 80;
    lastBeat = millis();

    lcd.clear();
}

// 100개 샘플 수집 후 SpO2 계산
void measureSpO2()
{
    for (int i = 0; i < SAMPLES; i++)
    {
        while (!particleSensor.available()) particleSensor.check();
        redBuffer[i] = particleSensor.getRed();
        irBuffer[i] = particleSensor.getIR();
        particleSensor.nextSample();
    }
    maxim_heart_rate_and_oxygen_saturation(
        irBuffer, SAMPLES,
        redBuffer,
        &spo2, &validSPO2,
        &dummyHR, &dummyValidHR
    );
}

void loop()
{
    long irValue = particleSensor.getIR();

    // BPM 계산 (PBA 알고리즘)
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
            for (byte i = 0; i < RATE_SIZE; i++) sum += rates[i];
            beatAvg = sum / RATE_SIZE;
        }
    }

    // 손가락 처음 감지 시각 기록
    if (irValue >= 50000)
    {
        if (fingerStartTime == 0)
        {
            fingerStartTime = millis();
            spO2Done = false;
        }
    }
    else
    {
        fingerStartTime = 0;
    }

    // 시리얼 출력: BPM
    Serial.print("Avg BPM: ");
    Serial.println(beatAvg);

    // 10초 경과 시 한 번만 SpO2 계산 및 출력
    if (fingerStartTime > 0 && millis() - fingerStartTime >= 10000 && !spO2Done)
    {
        measureSpO2();
        Serial.print("SpO2: ");
        if (validSPO2) Serial.println(spo2);
        else Serial.println("N/A");
        spO2Done = true;
    }

    // LCD 표시
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
        lcd.print("BPM:"); lcd.print(beatAvg);
        lcd.setCursor(8, 0);
        lcd.print("SpO2:");
        if (validSPO2) lcd.print(spo2);
        else lcd.print("--");
        lcd.setCursor(0, 1);
        lcd.print("                ");
    }
}
