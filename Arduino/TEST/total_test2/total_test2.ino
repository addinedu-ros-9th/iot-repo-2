#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>

MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
SoftwareSerial espSerial(2, 3); // ESP-01 RX, TX

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

#define BUFFER_SIZE 20
#define PULSE_LED 11
#define READ_LED 13

unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 30000;

bool wifiConnected = false;
bool tcpConnected = false;

bool sendATCommand(const char* command, const char* expected_response, unsigned long timeout = 2000)
{
    espSerial.println(command);
    unsigned long start = millis();
    String response = "";

    while (millis() - start < timeout)
    {
        if (espSerial.available())
        {
            char c = espSerial.read();
            response += c;
            if (response.indexOf(expected_response) != -1)
            {
                return true;
            }
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
    String cmd = "AT+CIPSTART=\"TCP\",\"" + String(TCP_SERVER) + "\"," + String(TCP_PORT);
    return sendATCommand(cmd.c_str(), "OK", 10000);
}

bool sendTCPData(const char* data, int len)
{
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write((uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}

// 이 함수는 RFID 리더기에서 UID를 읽어 반환하는 함수로 사용자가 구현해야 함
String readUid()
{
    // 예시 구현. 실제로는 RFID 모듈에서 읽은 값 반환
    // return "1234ABCD";
    return ""; // 임시
}

void setup()
{
    Serial.begin(9600);
    espSerial.begin(9600);
    pinMode(PULSE_LED, OUTPUT);
    pinMode(READ_LED, OUTPUT);

    if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
    {
        Serial.println("MAX30105 초기화 실패");
        while (1);
    }

    if (!mlx.begin())
    {
        Serial.println("MLX90614 초기화 실패");
        while (1);
    }

    particleSensor.setup(60, 4, 2, 100, 411, 4096);

    while (!wifiConnected)
    {
        Serial.println("WiFi 연결 시도");
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }

    while (!tcpConnected)
    {
        Serial.println("TCP 연결 시도");
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
}

void loop()
{
    // TCP 재연결
    if (wifiConnected && !tcpConnected)
    {
        while (!tcpConnected)
        {
            tcpConnected = connectTCP();
            if (!tcpConnected) delay(3000);
        }
    }

    // RFID UID 읽기
    String uid = readUid();
    if (tcpConnected && uid.length() > 0)
    {
        char uidPacket[64];
        snprintf(uidPacket, sizeof(uidPacket), "{SU}%s\n", uid.c_str());
        if (sendTCPData(uidPacket, strlen(uidPacket)))
        {
            Serial.println("UID 전송됨: " + uid);
        }
        else
        {
            tcpConnected = false;
        }
        delay(1000);  // 중복 방지
    }

    // 센서 데이터 주기적 전송
    if (tcpConnected && millis() - lastSendTime >= SEND_INTERVAL)
    {
        uint16_t irBuffer[BUFFER_SIZE];
        uint16_t redBuffer[BUFFER_SIZE];
        int32_t spo2, heartRate;
        int8_t validSPO2, validHeartRate;

        for (byte i = 0 ; i < BUFFER_SIZE ; i++)
        {
            while (!particleSensor.available())
            {
                particleSensor.check();
            }

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
        char dataBuffer[100];
        snprintf(dataBuffer, sizeof(dataBuffer), "%.2fC,HR=%ld,SPO2=%ld", tempC, (long)heartRate, (long)spo2);

        if (sendTCPData(dataBuffer, strlen(dataBuffer)))
        {
            Serial.println("센서 데이터 전송됨");
        }
        else
        {
            tcpConnected = false;
        }

        lastSendTime = millis();
    }
}
