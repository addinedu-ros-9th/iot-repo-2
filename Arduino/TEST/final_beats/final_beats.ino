#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include "heartRate.h"              // PBA 알고리즘 헤더
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

SoftwareSerial espSerial(2, 3);     // ESP-01 RX, TX
#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);
MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

const char* WIFI_SSID     = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER    = "34.64.53.123";
const int   TCP_PORT      = 8888;

bool wifiConnected = false;
bool tcpConnected  = false;
bool uidApproved   = false;

unsigned long lastSendTime   = 0;
const unsigned long SEND_INTERVAL = 10000UL;

// PBA 알고리즘용 변수
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeatTime = 0;
float beatsPerMinute = 0;
int   beatAvg = 0;

int32_t spo2Value;
int8_t validSPO2;
int32_t heartRateValue;
int8_t validHeartRate;

bool sendATCommand(const char* command, const char* expected_response, unsigned long timeout = 2000) {
    espSerial.println(command);
    unsigned long start = millis();
    String response = "";
    while (millis() - start < timeout) {
        if (espSerial.available()) {
            response += (char)espSerial.read();
            if (response.indexOf(expected_response) != -1) return true;
        }
    }
    return false;
}
bool connectWiFi() {
    if (!sendATCommand("AT", "OK")) return false;
    if (!sendATCommand("AT+CWMODE=1", "OK")) return false;
    String cmd = "AT+CWJAP=\"" + String(WIFI_SSID) + "\",\"" + WIFI_PASSWORD + "\"";
    return sendATCommand(cmd.c_str(), "OK", 20000);
}
bool connectTCP() {
    String cmd = "AT+CIPSTART=\"TCP\",\"" + String(TCP_SERVER) + "\"," + TCP_PORT;
    return sendATCommand(cmd.c_str(), "OK", 10000);
}
bool sendTCPData(const char* data, int len) {
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write((uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}
bool sendTCPBytes(const uint8_t* data, int len) {
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write(data, len);
    return sendATCommand("", "SEND OK", 5000);
}
void sendUID(const char* uid) {
    char buffer[40];
    sprintf(buffer, "SU%s\n", uid);
    sendTCPData(buffer, strlen(buffer));
}
void sendSensorPacket(uint8_t hr, uint8_t spo2, float temp) {
    char buffer[12];
    buffer[0] = 'S';
    buffer[1] = 'D';
    // HeartRate: 3자리
    buffer[2] = '0' + hr / 100;
    buffer[3] = '0' + (hr / 10) % 10;
    buffer[4] = '0' + hr % 10;
    // SpO2: 3자리
    buffer[5] = '0' + spo2 / 100;
    buffer[6] = '0' + (spo2 / 10) % 10;
    buffer[7] = '0' + spo2 % 10;
    // Temp*10 → 3자리
    int tempInt = (int)(temp * 10);
    buffer[8]  = '0' + tempInt / 100;
    buffer[9]  = '0' + (tempInt / 10) % 10;
    buffer[10] = '0' + tempInt % 10;
    buffer[11] = '\n';
    sendTCPData(buffer, 12);
}
void handleServerResponse(String msg) {
    msg.trim();
}
void receiveTCPMessage() {
    if (espSerial.available()) {
        String raw = espSerial.readStringUntil('\n');
        raw.trim();
        int idx = raw.indexOf(':');
        if (idx != -1 && idx + 1 < raw.length()) {
            String msg = raw.substring(idx + 1);
            handleServerResponse(msg);
        }
    }
}
void setup()
{
    Serial.begin(9600);
    espSerial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();
    Wire.begin();

    // MAX30105 초기화
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
    {
        while (1);
    }
    particleSensor.setup(60, 4, 2, 100, 411, 4096);
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeGreen(0);

    // MLX90614 초기화
    if (!mlx.begin())
    {
        while (1);
    }

    // WiFi 연결
    while (!wifiConnected)
    {
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }

    // TCP 연결
    while (!tcpConnected)
    {
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
}

void loop()
{
    receiveTCPMessage();

    // RFID 인증 처리
    if (!uidApproved) {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
            String uidStr = "";
            for (byte i = 0; i < mfrc522.uid.size; i++) {
                if (mfrc522.uid.uidByte[i] < 0x10) uidStr += "0";
                uidStr += String(mfrc522.uid.uidByte[i], HEX);
            }
            uidStr.toUpperCase();
            while (uidStr.length() < 32) uidStr += ' ';
            char uidBuffer[33];
            uidStr.toCharArray(uidBuffer, sizeof(uidBuffer));
            sendUID(uidBuffer);
            mfrc522.PICC_HaltA();
            uidApproved = true;
            lastSendTime = millis();
        }
        return;
    }

    if (millis() - lastSendTime >= SEND_INTERVAL)
    {
        float tempC = mlx.readObjectTempC();
        uint8_t hr = 0;
        uint8_t sp = 90;

        // 센서 판독
        particleSensor.check();
        uint32_t red = particleSensor.getRed();
        uint32_t ir  = particleSensor.getIR();

        // PBA 알고리즘으로 심박수 계산
        if (checkForBeat((long)ir))
        {
            long delta = millis() - lastBeatTime;
            lastBeatTime = millis();
            beatsPerMinute = 60.0 / (delta / 1000.0);

            if (beatsPerMinute > 20 && beatsPerMinute < 255)
            {
                rates[rateSpot++] = (byte)beatsPerMinute;
                rateSpot %= RATE_SIZE;

                int sum = 0;
                for (byte i = 0; i < RATE_SIZE; i++)
                {
                    sum += rates[i];
                }
                beatAvg = sum / RATE_SIZE;
            }
        }

        if (beatAvg > 0)
        {
            hr = beatAvg;
        }

        // 간단 SpO2 근사
        float ratio = (float)red / (float)ir;
        if (ratio > 0 && ratio < 1)
        {
            sp = constrain(110 - 25 * ratio, 80, 100);
        }

        sendSensorPacket(hr, sp, tempC);
        lastSendTime = millis();
    }
}
