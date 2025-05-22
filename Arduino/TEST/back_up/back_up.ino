#include <SoftwareSerial.h>
SoftwareSerial espSerial(2, 3); // ESP-01 RX, TX

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

bool wifiConnected = false;
bool tcpConnected = false;

// RFID 테스트용 UID
const char* TEST_UID = "1234567890ABCDEF1234567890ABCDEF";  // 32자리

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

  String cmd = "AT+CWJAP=\"";
  cmd += WIFI_SSID;
  cmd += "\",\"";
  cmd += WIFI_PASSWORD;
  cmd += "\"";
  return sendATCommand(cmd.c_str(), "OK", 20000);
}

bool connectTCP() {
  String cmd = "AT+CIPSTART=\"TCP\",\"";
  cmd += TCP_SERVER;
  cmd += "\",";
  cmd += TCP_PORT;
  return sendATCommand(cmd.c_str(), "OK", 10000);
}

bool sendTCPData(const char* data, int len) {
  String cmd = "AT+CIPSEND=" + String(len);
  if (!sendATCommand(cmd.c_str(), ">")) return false;
  espSerial.write((uint8_t*)data, len);
  return sendATCommand("", "SEND OK", 5000);
}

// SU 명령 - UID 전송 (IF-01)
void sendUID(const char* uid) {
  char buffer[40];
  sprintf(buffer, "SU%s\n", uid); // {SU(2)}{TAG UID(32)}{\n(1)}
  if (sendTCPData(buffer, strlen(buffer))) {
    Serial.println("[UID 전송] " + String(buffer));
  } else {
    Serial.println("[UID 전송 실패]");
  }
}

// GN / GE 응답 처리 (IF-02 / IF-03)
void handleServerResponse(String msg) {
  msg.trim();

  if (msg.startsWith("GN")) {
    char status = msg.charAt(2);
    if (status == '1') {
      String name = msg.substring(3, 12);  // 9바이트 이름
      name.trim();
      Serial.println("[사용자 인식 성공] 이름: " + name);
    } else {
      Serial.println("[사용자 인식 실패] 상태: GN0");
    }
  }
  else if (msg.startsWith("GE")) {
    char status = msg.charAt(2);
    String errorCode = msg.substring(3, 6);
    if (status == '0') {
      Serial.println("[오류 응답] 코드: " + errorCode);
      if (errorCode == "404") Serial.println("→ 사용자 없음");
      else if (errorCode == "500") Serial.println("→ 서버 오류");
    }
  }
}

// +IPD 수신 처리
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

  Serial.println("[시작] WiFi 및 TCP 연결 시도...");
  wifiConnected = connectWiFi();
  if (wifiConnected) {
    tcpConnected = connectTCP();
  }

  if (tcpConnected) {
    Serial.println("[성공] 서버 연결 완료");

    // 사용자 UID 전송 테스트
    sendUID(TEST_UID);
  } else {
    Serial.println("[실패] 서버 연결 실패");
  }
}

void loop() {
  // 서버 응답 수신 확인
  receiveTCPMessage();
}
