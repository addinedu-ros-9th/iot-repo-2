#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"         // SpO₂·심박수 알고리즘
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

SoftwareSerial espSerial(2, 3);     // ESP-01 RX, TX
#define RST_PIN 9
#define SS_PIN 10

MFRC522       mfrc522(SS_PIN, RST_PIN);
MAX30105      particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

const char* WIFI_SSID     = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER    = "34.64.53.123";
const int   TCP_PORT      = 8888;

bool     wifiConnected = false;
bool     tcpConnected  = false;
bool     uidApproved   = false;

unsigned long lastSendTime     = 0;
const unsigned long SEND_INTERVAL = 10000UL;

#define BUFFER_SIZE 10
uint16_t redBuffer[BUFFER_SIZE];
uint16_t irBuffer[BUFFER_SIZE];

// 알고리즘 결과 저장 변수
int32_t spo2Value;
int8_t  spo2Valid;
int32_t heartRateValue;
int8_t  heartRateValid;

bool sendATCommand(const char* command, const char* expected_response, unsigned long timeout = 2000)
{
    espSerial.println(command);
    unsigned long start = millis();
    String response = "";
    while (millis() - start < timeout)
    {
        if (espSerial.available())
        {
            response += (char)espSerial.read();
            if (response.indexOf(expected_response) != -1)
                return true;
        }
    }
    return false;
}

bool connectWiFi()
{
    if (!sendATCommand("AT", "OK")) return false;
    if (!sendATCommand("AT+CWMODE=1", "OK")) return false;
    String cmd = "AT+CWJAP=\"" + String(WIFI_SSID) + "\",\"" + WIFI_PASSWORD + "\"";
    return sendATCommand(cmd.c_str(), "OK", 20000);
}

bool connectTCP()
{
    String cmd = "AT+CIPSTART=\"TCP\",\"" + String(TCP_SERVER) + "\"," + TCP_PORT;
    return sendATCommand(cmd.c_str(), "OK", 10000);
}

void sendSensorPacket(uint8_t hr, uint8_t spo2, float temp)
{
    char buffer[12];
    buffer[0] = 'S';
    buffer[1] = 'D';
    buffer[2] = '0' + hr / 100;
    buffer[3] = '0' + (hr / 10) % 10;
    buffer[4] = '0' + hr % 10;
    buffer[5] = '0' + spo2 / 100;
    buffer[6] = '0' + (spo2 / 10) % 10;
    buffer[7] = '0' + spo2 % 10;
    int tempInt = (int)(temp * 10);
    buffer[8]  = '0' + tempInt / 100;
    buffer[9]  = '0' + (tempInt / 10) % 10;
    buffer[10] = '0' + tempInt % 10;
    buffer[11] = '\n';

    String cmd = "AT+CIPSEND=" + String(sizeof(buffer));
    if (!sendATCommand(cmd.c_str(), ">")) return;
    espSerial.write((uint8_t*)buffer, sizeof(buffer));
    sendATCommand("", "SEND OK", 5000);
}

void receiveTCPMessage()
{
    if (espSerial.available())
    {
        String raw = espSerial.readStringUntil('\n');
        // 필요 시 응답 파싱
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
    if (!uidApproved)
    {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
        {
            // UID 전송 구현...
            mfrc522.PICC_HaltA();
            uidApproved = true;
            lastSendTime = millis();
        }
        return;
    }

    if (millis() - lastSendTime >= SEND_INTERVAL)
    {
        // 1) 10개 샘플 수집
        for (int i = 0; i < BUFFER_SIZE; i++)
        {
            while (!particleSensor.available())
            {
                particleSensor.check();
            }
            redBuffer[i] = (uint16_t)particleSensor.getRed();
            irBuffer[i]  = (uint16_t)particleSensor.getIR();
            delay(10);  // 샘플링 간 약간 대기
        }

        // 2) 알고리즘 실행
        maxim_heart_rate_and_oxygen_saturation(
            irBuffer,
            BUFFER_SIZE,
            redBuffer,
            &spo2Value,
            &spo2Valid,
            &heartRateValue,
            &heartRateValid
        );

        // 3) 유효성 검사 후 전송값 설정
        uint8_t hr  = heartRateValid ? (uint8_t)heartRateValue : 0;
        uint8_t sp  = spo2Valid       ? (uint8_t)spo2Value       : 0;
        float   tempC = mlx.readObjectTempC();

        // 4) 서버로 전송
        sendSensorPacket(hr, sp, tempC);
        lastSendTime = millis();
    }
}
