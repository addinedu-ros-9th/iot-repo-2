#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);
MAX30105 particleSensor;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

#define BUFFER_SIZE 100
bool wifiConnected = false;
bool tcpConnected = false;
bool uidApproved = false;

unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 20000UL;

int32_t spo2;
int8_t validSPO2;
int32_t heartRate;
int8_t validHeartRate;

SoftwareSerial espSerial(2, 3); // 이후에 초기화 예정

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
            if (response.indexOf(expected_response) != -1) return true;
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

bool sendTCPData(const char* data, int len)
{
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write((uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}

bool sendTCPBytes(const uint8_t* data, int len)
{
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write(data, len);
    return sendATCommand("", "SEND OK", 5000);
}

void sendUID(const char* uid)
{
    char buffer[40];
    sprintf(buffer, "SU%s\n", uid);
    sendTCPData(buffer, strlen(buffer));
    Serial.println("[DEBUG] UID 전송 완료");
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
    sendTCPData(buffer, 12);
    Serial.println("[DEBUG] 센서 패킷 전송 완료");
}

void handleServerResponse(String msg)
{
    msg.trim();
    Serial.println("[DEBUG] 서버 응답 수신: " + msg);
}

void receiveTCPMessage()
{
    if (espSerial.available())
    {
        String raw = espSerial.readStringUntil('\n');
        raw.trim();
        int idx = raw.indexOf(':');
        if (idx != -1 && idx + 1 < raw.length())
        {
            String msg = raw.substring(idx + 1);
            handleServerResponse(msg);
        }
    }
}

void setup()
{
    Serial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();
    Wire.begin();

    if (!particleSensor.begin(Wire, I2C_SPEED_FAST))
    {
        // Serial.println("[ERROR] MAX30105 초기화 실패");
        while (1);
    }
    Serial.println("[INFO] MAX30105 초기화 성공");

    if (!mlx.begin())
    {
        Serial.println("[ERROR] MLX90614 초기화 실패");
        while (1);
    }
    Serial.println("[INFO] MLX90614 초기화 성공");

    particleSensor.setup(60, 4, 2, 100, 411, 4096);
    Serial.println("[INFO] 센서 설정 완료");

    // 🔽 SoftwareSerial 초기화는 센서 초기화가 끝난 뒤에 수행
    espSerial.begin(9600);

    while (!wifiConnected)
    {
        Serial.println("[INFO] WiFi 연결 시도 중...");
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }

    while (!tcpConnected)
    {
        Serial.println("[INFO] TCP 연결 시도 중...");
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
}


void loop()
{
    receiveTCPMessage();

    if (!uidApproved)
    {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial())
        {
            String uidStr = "";
            for (byte i = 0; i < mfrc522.uid.size; i++)
            {
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
            // Serial.println("[DEBUG] RFID 태그 인식 완료");
        }
        return;
    }

    if (millis() - lastSendTime >= SEND_INTERVAL)
    {
        uint16_t irBuffer[BUFFER_SIZE];
        uint16_t redBuffer[BUFFER_SIZE];

        for (byte i = 0; i < BUFFER_SIZE; i++)
        {
            while (!particleSensor.available()) particleSensor.check();
            redBuffer[i] = particleSensor.getRed();
            irBuffer[i] = particleSensor.getIR();
            particleSensor.nextSample();
        }

        maxim_heart_rate_and_oxygen_saturation(
            irBuffer, BUFFER_SIZE, redBuffer,
            &spo2, &validSPO2,
            &heartRate, &validHeartRate);

        float tempC = mlx.readObjectTempC();

        if (validHeartRate && validSPO2)
        {
            // Serial.print("[DEBUG] HR: "); Serial.print(heartRate);
            // Serial.print(", SPO2: "); Serial.print(spo2);
            // Serial.print(", Temp: "); Serial.println(tempC);
            sendSensorPacket((uint8_t)heartRate, (uint8_t)spo2, tempC);
        }
        else
        {
            // Serial.println("[WARN] 유효하지 않은 심박수 또는 산소포화도 측정값");
        }

        lastSendTime = millis();
    }
}