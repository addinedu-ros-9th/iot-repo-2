#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

SoftwareSerial espSerial(2, 3); // ESP-01 RX, TX

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);  // RFID 인스턴스

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

bool wifiConnected = false;
bool tcpConnected = false;

int heartRate = 88;
int spO2 = 96;
float temperature = 36.5;

#define FALL_DETECTION     0b00000001
#define HIGH_TEMPERATURE   0b00000010
#define LOW_TEMPERATURE    0b00000100
#define HIGH_HEART_RATE    0b00001000
#define LOW_HEART_RATE     0b00010000
#define LOW_SPO2           0b00100000

uint8_t currentAlertStatus = 0;

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

void sendUID(const char* uid)
{
    char buffer[40];
    sprintf(buffer, "SU%s\n", uid);
    sendTCPData(buffer, strlen(buffer));
}

void sendSensorData(int hr, int spo2, float temp)
{
    char buffer[32];
    int tempInt = (int)(temp * 10);
    sprintf(buffer, "SD%02d%02d%02d\n", hr, spo2, tempInt);
    sendTCPData(buffer, strlen(buffer));
}

void sendAlertLogByte(bool isStart, uint8_t alertFlags)
{
    char buffer[8];
    sprintf(buffer, "%s%c\n", isStart ? "SS" : "SE", alertFlags);
    sendTCPData(buffer, strlen(buffer));
}

void handleServerResponse(String msg)
{
    msg.trim();

    if (msg.startsWith("GN"))
    {
        if (msg.charAt(2) == '1')
        {
            String name = msg.substring(3, 12);
            name.trim();
            Serial.println("[사용자 인식 성공] 이름: " + name);
        }
        else
        {
            Serial.println("[사용자 인식 실패: GN 응답 상태 0]");
        }
    }
    else if (msg.startsWith("GE"))
    {
        char status = msg.charAt(2);
        String error = msg.substring(3, 6);
        if (status == '0')
        {
            Serial.print("[오류 응답] 코드: " + error + " → ");
            if (error == "404")
            {
                Serial.println("사용자 없음");
            }
            else if (error == "500")
            {
                Serial.println("서버 오류");
            }
            else
            {
                Serial.println("알 수 없는 오류");
            }
        }
        else
        {
            Serial.println("[GE] 예상치 못한 상태 코드");
        }
    }
    else if (msg.startsWith("GM"))
    {
        String med = msg.substring(2);
        med.trim();
        Serial.println("[약 알림 수신] 약 이름: " + med);
    }
    else
    {
        Serial.println("[알 수 없는 응답] " + msg);
    }
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
    espSerial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();

    while (!wifiConnected)
    {
        Serial.println("[INFO] WiFi 연결 시도 중...");
        wifiConnected = connectWiFi();
        if (!wifiConnected)
        {
            Serial.println("[ERROR] WiFi 연결 실패. 3초 후 재시도...");
            delay(3000);
        }
    }
    Serial.println("[SUCCESS] WiFi 연결 완료");

    while (!tcpConnected)
    {
        Serial.println("[INFO] TCP 서버 연결 시도 중...");
        tcpConnected = connectTCP();
        if (!tcpConnected)
        {
            Serial.println("[ERROR] TCP 서버 연결 실패. 3초 후 재시도...");
            delay(3000);
        }
    }
    Serial.println("[SUCCESS] TCP 서버 연결 완료");
}

void loop()
{
    receiveTCPMessage();

    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
    {
        return;
    }

    String uidStr = "";
    for (byte i = 0; i < mfrc522.uid.size; i++)
    {
        if (mfrc522.uid.uidByte[i] < 0x10) uidStr += "0";
        uidStr += String(mfrc522.uid.uidByte[i], HEX);
    }

    uidStr.toUpperCase();
    uidStr.trim();

    while (uidStr.length() < 32)
    {
        uidStr += ' ';
    }

    char uidBuffer[33];
    uidStr.toCharArray(uidBuffer, sizeof(uidBuffer));

    Serial.print("[RFID] UID 읽음: ");
    Serial.println(uidStr);

    sendUID(uidBuffer);
    Serial.println("[SEND] SU 명령 전송됨");

    mfrc522.PICC_HaltA();
    delay(1000);
}
