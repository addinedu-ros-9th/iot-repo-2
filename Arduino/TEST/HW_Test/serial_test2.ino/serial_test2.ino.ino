#include <SoftwareSerial.h>

// ESP-01 통신을 위한 소프트웨어 시리얼 설정
SoftwareSerial espSerial(2, 3); // RX, TX

// WiFi 설정
const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

// 센서 핀 설정
const int SENSOR_PIN = A0;  // 아날로그 센서 핀

// 데이터 전송 간격 (밀리초)
const unsigned long SEND_INTERVAL = 5000;  // 5초마다 데이터 전송

// 마지막 데이터 전송 시간
unsigned long lastSendTime = 0;

// ESP8266 상태
bool wifiConnected = false;
bool tcpConnected = false;

// AT 명령어 전송 및 응답 확인
bool sendATCommand(const char* command, const char* expected_response, unsigned long timeout = 2000) {
  espSerial.println(command);
  unsigned long start = millis();
  String response = "";
  
  while (millis() - start < timeout) {
    if (espSerial.available()) {
      char c = espSerial.read();
      response += c;
      if (response.indexOf(expected_response) != -1) {
        return true;
      }
    }
  }
  return false;
}

// WiFi 연결
bool connectWiFi() {
  // ESP8266 초기화
  if (!sendATCommand("AT", "OK")) return false;
  if (!sendATCommand("AT+CWMODE=1", "OK")) return false;
  
  // WiFi 연결
  String cmd = "AT+CWJAP=\"";
  cmd += WIFI_SSID;
  cmd += "\",\"";
  cmd += WIFI_PASSWORD;
  cmd += "\"";
  
  if (!sendATCommand(cmd.c_str(), "OK", 20000)) return false;
  return true;
}

// TCP 서버 연결
bool connectTCP() {
  String cmd = "AT+CIPSTART=\"TCP\",\"";
  cmd += TCP_SERVER;
  cmd += "\",";
  cmd += TCP_PORT;
  
  if (!sendATCommand(cmd.c_str(), "OK", 10000)) return false;
  return true;
}

// TCP로 데이터 전송
bool sendTCPData(const char* data, int len) {
  String cmd = "AT+CIPSEND=";
  cmd += len;
  
  if (!sendATCommand(cmd.c_str(), ">")) return false;
  
  espSerial.write((uint8_t*)data, len);
  return sendATCommand("", "SEND OK", 5000);
}

// 센서 데이터 읽기
int readSensorData() {
  // 아날로그 센서에서 값 읽기
  int sensorValue = analogRead(SENSOR_PIN);
  return sensorValue;
}

void setup()
{
  Serial.begin(9600);
  espSerial.begin(9600); // ESP-01 통신 초기화
  
  // 센서 핀 설정
  pinMode(SENSOR_PIN, INPUT);
  
  // WiFi 연결
  wifiConnected = connectWiFi();
  if (wifiConnected) {
    Serial.println("WiFi Connected!");
    // TCP 서버 연결
    tcpConnected = connectTCP();
    if (tcpConnected) {
      Serial.println("TCP Connected!");
    } else {
      Serial.println("TCP Connection Failed!");
    }
  } else {
    Serial.println("WiFi Connection Failed!");
  }
}

void loop() 
{
  // 1. TCP 연결이 끊겼다면 재시도
  if (wifiConnected && !tcpConnected) {
    tcpConnected = connectTCP();
  }

  // 2. 사용자 명령 입력 처리
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // 앞뒤 공백 제거

    if (tcpConnected && cmd.startsWith("send ")) {
      String message = cmd.substring(5);
      char dataBuffer[100];
      message.toCharArray(dataBuffer, sizeof(dataBuffer));
      if (sendTCPData(dataBuffer, strlen(dataBuffer))) {
        Serial.println("Sent: " + message);
      } else {
        Serial.println("Send failed");
        tcpConnected = false;
      }
    } else {
      Serial.println("Unknown command or not connected.");
    }
  }

  // TCP 수신 메시지 출력
  if (tcpConnected && espSerial.available()) {
    // 전체 수신 줄 읽기
    String raw = espSerial.readStringUntil('\n');
    raw.trim(); // 앞뒤 공백 제거

    // +IPD 헤더 처리
    int idx = raw.indexOf(':');
    if (idx != -1 && idx + 1 < raw.length()) {
      // ':' 뒤부터가 실제 메시지
      String message = raw.substring(idx + 1);
      message.trim();
      Serial.println("Received from Server: " + message);
    }
  }
}

