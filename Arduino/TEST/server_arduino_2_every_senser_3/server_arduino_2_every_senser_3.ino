#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include <SoftwareSerial.h>

// Wi-Fi / TCP 설정
const char* WIFI_SSID     = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER    = "34.64.53.123";
const int   TCP_PORT      = 8888;

// 센서 및 통신 객체
MAX30105      particleSensor;
SoftwareSerial espSerial(2, 3); // RX, TX

// 버퍼 크기, 전송 간격
const int   SENSOR_BUFFER_SIZE = 20;
const long  SEND_INTERVAL      = 20000L;  // 20초

uint16_t irBuffer[SENSOR_BUFFER_SIZE];
uint16_t redBuffer[SENSOR_BUFFER_SIZE];

int32_t spo2;
int8_t  validSPO2;
int32_t heartRate;
int8_t  validHeartRate;

bool wifiConnected  = false;
bool tcpConnected   = false;
unsigned long lastSendTime = 0;

// AT 명령 전송 함수
bool sendATCommand(const char* cmd, const char* expect, unsigned long timeout = 2000) {
    espSerial.println(cmd);
    unsigned long start = millis();
    String resp;
    while (millis() - start < timeout) {
        if (espSerial.available()) {
            resp += char(espSerial.read());
            if (resp.indexOf(expect) != -1) return true;
        }
    }
    return false;
}

// Wi-Fi 연결
bool connectWiFi() {
    if (!sendATCommand("AT",          "OK")) return false;
    if (!sendATCommand("AT+CWMODE=1", "OK")) return false;
    String join = String("AT+CWJAP=\"") + WIFI_SSID + "\",\"" + WIFI_PASSWORD + "\"";
    return sendATCommand(join.c_str(), "OK", 20000);
}

// TCP 연결
bool connectTCP() {
    String open = String("AT+CIPSTART=\"TCP\",\"") + TCP_SERVER + "\"," + TCP_PORT;
    return sendATCommand(open.c_str(), "OK", 10000);
}

// TCP로 데이터 전송
bool sendTCPData(const char* data, int len) {
    String p = String("AT+CIPSEND=") + len;
    if (!sendATCommand(p.c_str(), ">")) return false;
    espSerial.write((const uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}

// 센서값 패킷 생성·전송
// 형식: SD + HR(3자리) + SpO2(3자리) + TEMP(3자리) + '\n'
// MLX90614 제거했으므로 temp는 0으로 전송
void sendSensorPacket(uint8_t hr, uint8_t sp, float temp) {
    char buf[12];
    buf[0] = 'S'; buf[1] = 'D';
    buf[2] = '0' + hr/100;
    buf[3] = '0' + (hr/10)%10;
    buf[4] = '0' + hr%10;
    buf[5] = '0' + sp/100;
    buf[6] = '0' + (sp/10)%10;
    buf[7] = '0' + sp%10;
    int ti = int(temp*10);
    buf[8]  = '0' + ti/100;
    buf[9]  = '0' + (ti/10)%10;
    buf[10] = '0' + ti%10;
    buf[11] = '\n';
    sendTCPData(buf, sizeof(buf));
    // Serial.println("디버그: 센서 데이터 전송 완료");
}

void setup() {
    Serial.begin(9600);
    while (!Serial) {;}

    // I2C, MAX30105 초기화
    Wire.begin();
    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        Serial.println("오류: MAX30105 초기화 실패");
        while (1);
    }
    Serial.println("정보: MAX30105 초기화 성공");

    particleSensor.setup(
        0x1F, // LED 밝기
        4,    // 샘플 평균
        2,    // SPO2 모드
        100,  // 샘플링 속도
        411,  // 펄스 폭
        4096  // ADC 범위
    );
    // Serial.println("정보: MAX30105 설정 완료");

    // ESP8266 시리얼
    espSerial.begin(9600);

    // Wi-Fi 연결
    while (!wifiConnected) {
        Serial.println("정보: Wi-Fi 연결 중...");
        wifiConnected = connectWiFi();
        if (!wifiConnected) delay(3000);
    }
    // Serial.println("정보: Wi-Fi 연결됨");

    // TCP 연결
    while (!tcpConnected) {
        Serial.println("정보: TCP 연결 중...");
        tcpConnected = connectTCP();
        if (!tcpConnected) delay(3000);
    }
    // Serial.println("정보: TCP 연결됨");

    lastSendTime = millis();
}

void loop() {
    // 주기적으로 센서 읽기·전송
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

        // 전송 또는 경고
        if (validHeartRate && validSPO2) {
            sendSensorPacket((uint8_t)heartRate, (uint8_t)spo2, 0.0f);
        } else {
            // Serial.println("경고: 유효하지 않은 심박수 또는 산소포화도 측정값");
        }

        lastSendTime = millis();
    }

    // 서버 응답이 오면 시리얼에 출력
    if (espSerial.available()) {
        String line = espSerial.readStringUntil('\n');
        line.trim();
        // Serial.println("서버 응답: " + line);
    }
}
