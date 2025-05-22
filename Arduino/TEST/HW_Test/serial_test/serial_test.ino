#include <SoftwareSerial.h>

// ESP-01 통신을 위한 소프트웨어 시리얼 설정
SoftwareSerial espSerial(2, 3); // RX, TX

// WiFi 설정
const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 9999;

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
  espSerial.begin(115200); // ESP-01 통신 초기화
  
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
  // TCP 연결 확인 및 재연결
  if (wifiConnected && !tcpConnected) {
    tcpConnected = connectTCP();
  }
  
  // 일정 간격으로 센서 데이터 전송
  unsigned long currentTime = millis();
  if (tcpConnected && (currentTime - lastSendTime >= SEND_INTERVAL)) {
    // 센서 데이터 읽기
    int sensorValue = readSensorData();
    
    // 데이터 포맷팅 (JSON 형식)
    char dataBuffer[50];
    sprintf(dataBuffer, "{\"sensor\":%d,\"time\":%lu}", sensorValue, currentTime);
    
    // 데이터 전송
    if (sendTCPData(dataBuffer, strlen(dataBuffer))) {
      Serial.print("Sensor data sent: ");
      Serial.println(dataBuffer);
      lastSendTime = currentTime;
    } else {
      Serial.println("Failed to send sensor data");
      // 연결 문제 발생 시 재연결 플래그 설정
      tcpConnected = false;
    }
  }

  // TCP 데이터 수신 확인
  if (tcpConnected && espSerial.available()) {
    String response = espSerial.readString();
    Serial.println("TCP Response: " + response);
  }
}
