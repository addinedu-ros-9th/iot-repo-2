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
        // 사용자 인식 성공/실패 처리 생략
    }
    else if (msg.startsWith("GE"))
    {
        // 오류 응답 처리 생략
    }
    else if (msg.startsWith("GM"))
    {
        // 약 알림 수신 처리 생략
    }
    else
    {
        // 기타 메시지 생략
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
    Serial.begin(9600);  // 제거 가능 (또는 주석 처리 가능)
    espSerial.begin(9600);
    SPI.begin();
    mfrc522.PCD_Init();

    while (!wifiConnected)
    {
        wifiConnected = connectWiFi();
        if (!wifiConnected)
        {
            delay(3000);
        }
    }

    while (!tcpConnected)
    {
        tcpConnected = connectTCP();
        if (!tcpConnected)
        {
            delay(3000);
        }
    }
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

    sendUID(uidBuffer);

    mfrc522.PICC_HaltA();
    delay(1000);
}
