#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

//=== 핀 및 객체 정의 ===
#define RST_PIN 9
#define SS_PIN 10

SoftwareSerial espSerial(2, 3);    // ESP-01 RX, TX
MFRC522        mfrc522(SS_PIN, RST_PIN);
MAX30105       particleSensor;

//=== Wi-Fi/TCP 설정 ===
const char* WIFI_SSID     = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER    = "34.64.53.123";
const int   TCP_PORT      = 8888;

//=== 센서 버퍼/주기 정의 ===
const int   SENSOR_BUFFER_SIZE = 20;
const long  SEND_INTERVAL      = 20000L;  // 20초

uint16_t irBuffer[SENSOR_BUFFER_SIZE];
uint16_t redBuffer[SENSOR_BUFFER_SIZE];

int32_t spo2;
int8_t  validSPO2;
int32_t heartRate;
int8_t  validHeartRate;
float   temperature = 0.0f;  // 온도값 (필요시 외부 센서 입력)

unsigned long lastSendTime = 0;
bool wifiConnected = false;
bool tcpConnected  = false;

//=== AT 명령 전송 ===
bool sendATCommand(const char* cmd, const char* expect, unsigned long timeout = 2000) {
    espSerial.println(cmd);
    unsigned long start = millis();
    String resp;
    while (millis() - start < timeout) {
        if (espSerial.available()) resp += char(espSerial.read());
    }
    return resp.indexOf(expect) != -1;
}

//=== 네트워크 연결 함수 ===
bool connectWiFi() {
    if (!sendATCommand("AT",          "OK")) return false;
    if (!sendATCommand("AT+CWMODE=1", "OK")) return false;
    String join = String("AT+CWJAP=\"") + WIFI_SSID + "\",\"" + WIFI_PASSWORD + "\"";
    return sendATCommand(join.c_str(), "WIFI GOT IP", 30000);
}

bool connectTCP() {
    String open = String("AT+CIPSTART=\"TCP\",\"") + TCP_SERVER + "\"," + TCP_PORT;
    return sendATCommand(open.c_str(), "OK", 10000);
}

//=== TCP 데이터 전송 ===
bool sendTCPData(const char* data, int len) {
    String p = String("AT+CIPSEND=") + len;
    if (!sendATCommand(p.c_str(), ">")) return false;
    espSerial.write((const uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}

//=== UID 전송 ===
void sendUID(const char* uid) {
    char buf[40];
    sprintf(buf, "SU%s\n", uid);
    sendTCPData(buf, strlen(buf));
    Serial.println("정보: UID 전송 완료");
}

//=== 센서 데이터 전송 ===
// 형식: SD + HR(3자리) + SpO2(3자리) + TEMP(3자리) + '\n'
void sendSensorData(int hr, int sp, int temp_d) {
    char buf[16];
    sprintf(buf, "SD%03d%03d%03d\n", hr, sp, temp_d);
    sendTCPData(buf, strlen(buf));
    // Serial.println("정보: 센서 데이터 전송 완료");
}

//=== 서버 응답 무시 ===
void receiveTCPMessage() {
    if (!espSerial.available()) return;
    while (espSerial.available()) {
        espSerial.read();  // 버리기
    }
}

void setup() {
    Serial.begin(9600);
    while (!Serial) {;}

    // RFID 초기화
    SPI.begin();
    mfrc522.PCD_Init();
    // Serial.println("정보: RFID 리더 준비됨");

    // MAX30105 초기화
    Wire.begin();
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("오류: MAX30105 초기화 실패");
        while (1);
    }
    particleSensor.setup(0x1F, 4, 2, 100, 411, 4096);
    Serial.println("정보: MAX30105 초기화 성공");

    // ESP8266 시리얼 및 네트워크 연결
    espSerial.begin(9600);
    while (!wifiConnected) {
        Serial.println("정보: Wi-Fi 연결 시도...");
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }
    Serial.println("정보: Wi-Fi 연결됨");

    while (!tcpConnected) {
        Serial.println("정보: TCP 연결 시도...");
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
    Serial.println("정보: TCP 연결됨");

    lastSendTime = millis();
}

void loop() {
    // 서버 응답 처리
    receiveTCPMessage();

    // RFID 태그 읽기
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        String uid = "";
        for (byte i = 0; i < mfrc522.uid.size; i++) {
            if (mfrc522.uid.uidByte[i] < 0x10) uid += "0";
            uid += String(mfrc522.uid.uidByte[i], HEX);
        }
        uid.toUpperCase();
        while (uid.length() < 32) uid += ' ';
        char uidBuf[33];
        uid.toCharArray(uidBuf, sizeof(uidBuf));

        sendUID(uidBuf);
        mfrc522.PICC_HaltA();
        delay(1000);
    }

    // 주기적 센서 데이터 전송
    if (millis() - lastSendTime >= SEND_INTERVAL) {
        // 데이터 수집
        for (int i = 0; i < SENSOR_BUFFER_SIZE; i++) {
            while (!particleSensor.available()) particleSensor.check();
            redBuffer[i] = particleSensor.getRed();
            irBuffer[i]  = particleSensor.getIR();
            particleSensor.nextSample();
        }

        // 측정값 계산
        maxim_heart_rate_and_oxygen_saturation(
            irBuffer, SENSOR_BUFFER_SIZE,
            redBuffer,
            &spo2, &validSPO2,
            &heartRate, &validHeartRate
        );

        // 체온 데이터 (예시: 36.5℃ → 365)
        temperature = 36.5;
        int temp_d = int(temperature * 10);

        // 데이터 전송
        if (validHeartRate && validSPO2) {
            sendSensorData(heartRate, spo2, temp_d);
        } else {
            // Serial.println("경고: 유효하지 않은 심박수/산소포화도");
        }

        lastSendTime = millis();
    }
}
