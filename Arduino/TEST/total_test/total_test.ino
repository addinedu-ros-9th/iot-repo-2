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
const unsigned long SEND_INTERVAL = 30000; // 30초

bool wifiConnected = false;
bool tcpConnected = false;
bool uidApproved = false;

const char* uid = "ABCD1234"; // 테스트용 UID

bool sendATCommand(const char* command, const char* expected_response, unsigned long timeout = 2000) {
  espSerial.println(command);
  unsigned long start = millis();
  String response = "";
  while (millis() - start < timeout) {
    if (espSerial.available()) {
      char c = espSerial.read();
      response += c;
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
  String cmd = "AT+CIPSTART=\"TCP\",\"" + String(TCP_SERVER) + "\"," + String(TCP_PORT);
  return sendATCommand(cmd.c_str(), "OK", 10000);
}

bool sendTCPData(const char* data, int len) {
  String cmd = "AT+CIPSEND=" + String(len);
  if (!sendATCommand(cmd.c_str(), ">")) return false;
  espSerial.write((uint8_t*)data, len);
  return sendATCommand("", "SEND OK", 5000);
}

void setup()
{
  Serial.begin(9600);
  espSerial.begin(9600);
  Serial.println("begin");

  pinMode(PULSE_LED, OUTPUT);
  pinMode(READ_LED, OUTPUT);
  Serial.println("pinMode");

  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    while (1);
  }
  if (!mlx.begin()) {
    while (1);
  }

  particleSensor.setup(60, 4, 2, 100, 411, 4096);

  while (!wifiConnected) {
    Serial.println("wifiConnected");
    wifiConnected = connectWiFi();
    if (wifiConnected) {
    } else {
      delay(3000);
    }
  }

  while (!tcpConnected) {
    Serial.println("tcpConnected");
    tcpConnected = connectTCP();
    if (tcpConnected) {
    } else {
      delay(3000);
    }
  }
}

void loop()
{
  Serial.println("loop");
  // TCP 재연결 시도
  if (wifiConnected && !tcpConnected) {
    while (!tcpConnected) {
      tcpConnected = connectTCP();
      if (tcpConnected) {
      } else {
        delay(3000);
      }
    }
  }

  // 1회만 UID 승인 요청
  if (tcpConnected && !uidApproved) {
    char uidPacket[50];
    snprintf(uidPacket, sizeof(uidPacket), "{SU}%s\n", uid);
    if (sendTCPData(uidPacket, strlen(uidPacket))) {
    } else {
      tcpConnected = false;
    }
    delay(1000);
  }

  // 서버 응답 수신 처리
  if (tcpConnected && espSerial.available()) {
    String raw = espSerial.readStringUntil('\n');
    raw.trim();
    int idx = raw.indexOf(':');
    if (idx != -1 && idx + 1 < raw.length()) {
      String message = raw.substring(idx + 1);
      message.trim();

      if (message == "APPROVED") {
        uidApproved = true;
      }
    }
  }

  // 30초마다 센서 데이터 전송
  if (tcpConnected && uidApproved && millis() - lastSendTime >= SEND_INTERVAL) {
    uint16_t irBuffer[BUFFER_SIZE];
    uint16_t redBuffer[BUFFER_SIZE];
    int32_t spo2, heartRate;
    int8_t validSPO2, validHeartRate;

    for (byte i = 0 ; i < BUFFER_SIZE ; i++) {
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
    char dataBuffer[100];
    snprintf(dataBuffer, sizeof(dataBuffer), "%.2fC,HR=%ld,SPO2=%ld", tempC, (long)heartRate, (long)spo2);

    if (sendTCPData(dataBuffer, strlen(dataBuffer))) {
    } else {
      tcpConnected = false;
    }
    lastSendTime = millis();
  }
}