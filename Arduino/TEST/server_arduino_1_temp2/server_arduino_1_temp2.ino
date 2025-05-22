#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

SoftwareSerial espSerial(2, 3); // ESP-01 RX, TX

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
const unsigned long SEND_INTERVAL = 20000UL;  // 20초

int32_t spo2;
int8_t validSPO2;
int32_t heartRate;
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

    // HeartRate: 3자리 -> char 숫자 문자 ('0'+digit)
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
    if (msg.startsWith("GN")) {
        Serial.println("[GN] 사용자 인식 응답 수신");
    } else if (msg.startsWith("GE")) {
        Serial.println("[GE] 에러 응답 수신");
    } else if (msg.startsWith("GM")) {
        Serial.println("[GM] 약 알림 수신");
    }
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

void setup() {
    Serial.begin(9600);
    espSerial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();
    Wire.begin();

    particleSensor.begin(Wire, I2C_SPEED_FAST);
    mlx.begin();
    particleSensor.setup(60, 4, 2, 100, 411, 4096);
    Serial.println("[SETUP] 센서 초기화 완료");

    while (!wifiConnected) {
        Serial.println("[WIFI] 연결 시도 중...");
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }
    Serial.println("[WIFI] 연결 성공");

    while (!tcpConnected) {
        Serial.println("[TCP] 서버 연결 시도 중...");
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
    Serial.println("[TCP] 서버 연결 성공");
}

void loop() {
    receiveTCPMessage();

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

            Serial.print("[RFID] UID 전송: ");
            Serial.println(uidStr);

            uidApproved = true;
            lastSendTime = millis();
        }
        return;
    }

    if (millis() - lastSendTime >= SEND_INTERVAL) {
        // 예시 값 사용 (센서 측정 생략)
        uint8_t heartRate = 102;
        uint8_t spo2 = 98;
        float tempC = mlx.readObjectTempC();

        Serial.print("[MOCK SEND] HR="); Serial.print(heartRate);
        Serial.print(", SPO2="); Serial.print(spo2);
        Serial.print(", Temp*10="); Serial.println((int)(tempC * 10));

        sendSensorPacket(heartRate, spo2, tempC);
        lastSendTime = millis();
    }
}
