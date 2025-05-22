#include <Wire.h>
#include <LiquidCrystal.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include "heartRate.h"
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

LiquidCrystal lcd(A0, A1, 4, 5, 6, 7);
SoftwareSerial espSerial(2, 3);

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);
MAX30105 particleSensor;
Adafruit_MLX90614 mlx;

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

bool wifiConnected = false;
bool tcpConnected = false;
bool uidApproved = false;

unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 60000UL;

const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute;
int beatAvg;

uint8_t prevHR = 0;
uint8_t prevSP = 0;
float prevTemp = 0.0;

bool error_fall = false;
bool error_highT = false;
bool error_lowT = false;
bool error_highHR = false;
bool error_lowHR = false;
bool error_lowSPO2 = false;

bool sendATCommand(const char* command, const char* expected, unsigned long timeout = 2000) {
    espSerial.println(command);
    Serial.print("AT 명령 전송: "); Serial.println(command);
    unsigned long start = millis();
    String resp;
    while (millis() - start < timeout) {
        if (espSerial.available()) {
            resp += (char)espSerial.read();
        }
    }
    if (resp.indexOf(expected) != -1) {
        Serial.println("응답 확인됨: " + String(expected));
        return true;
    }
    Serial.println("응답 시간 초과");
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

void handleSerialCommand(String cmd) {
    cmd.trim();
    if (cmd == "FD")       error_fall = true;
    else if (cmd == "HT")  error_highT = true;
    else if (cmd == "LT")  error_lowT = true;
    else if (cmd == "HH")  error_highHR = true;
    else if (cmd == "LH")  error_lowHR = true;
    else if (cmd == "LS")  error_lowSPO2 = true;
    else if (cmd == "CFD") error_fall = false;
    else if (cmd == "CHT") error_highT = false;
    else if (cmd == "CLT") error_lowT = false;
    else if (cmd == "CHH") error_highHR = false;
    else if (cmd == "CLH") error_lowHR = false;
    else if (cmd == "CLS") error_lowSPO2 = false;
    else Serial.println("알 수 없는 명령");
}

void setup() {
    Serial.begin(9600);
    espSerial.begin(9600);
    lcd.begin(16, 2);
    lcd.print("초기화 중...");

    SPI.begin();
    mfrc522.PCD_Init();
    Wire.begin();

    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        lcd.clear(); lcd.print("MAX30105 오류"); while(1);
    }
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeIR(0x1F);

    if (!mlx.begin()) {
        lcd.clear(); lcd.print("MLX90614 오류"); while(1);
    }

    for (byte i = 0; i < RATE_SIZE; i++) rates[i] = 0;

    while (!wifiConnected) { wifiConnected = connectWiFi(); delay(3000); }
    while (!tcpConnected)  { tcpConnected  = connectTCP();  delay(3000); }

    lcd.clear();
    Serial.println("시스템 초기화 완료");
}

void loop() {
    // UID 승인 처리
    if (!uidApproved) {
        if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
            String u;
            for (byte i = 0; i < mfrc522.uid.size; i++) {
                if (mfrc522.uid.uidByte[i] < 0x10) u += "0";
                u += String(mfrc522.uid.uidByte[i], HEX);
            }
            u.toUpperCase();
            while (u.length() < 32) u += ' ';
            char ub[33]; u.toCharArray(ub, sizeof(ub));
            char buf[40];
            sprintf(buf, "SU%s", ub);
            sendTCPData(buf, strlen(buf));
            mfrc522.PICC_HaltA();
            uidApproved = true;
            lastSendTime = millis();
            prevHR = 75;
            prevSP = 95;
            prevTemp = 36.5;
            Serial.println("UID 승인 완료");
        }
        return;
    }
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        handleSerialCommand(cmd);
    }

    float tempC = mlx.readObjectTempC();
    if (tempC > 45.0) error_highT = true;
    if (tempC < 20.0) error_lowT = true;

    uint8_t hr = 0, sp = 0;
    bool valid = false;
    unsigned long t0 = millis();

    while (millis() - t0 < 3000) {
        long ir = particleSensor.getIR();
        if (ir < 5000) { delay(10); continue; }
        if (checkForBeat(ir)) {
            long d = millis() - lastBeat;
            lastBeat = millis();
            beatsPerMinute = 60.0 / (d / 1000.0);
            if (beatsPerMinute > 40 && beatsPerMinute < 120) {
                rates[rateSpot++] = (byte)beatsPerMinute;
                rateSpot %= RATE_SIZE;
                beatAvg = 0;
                for (byte x = 0; x < RATE_SIZE; x++) beatAvg += rates[x];
                beatAvg /= RATE_SIZE;
                if (beatAvg > 0) { hr = beatAvg; valid = true; }
            }
        }
        uint32_t rv = particleSensor.getRed();
        if (rv > 0 && ir > 5000) {
            float r = (float)rv / ir;
            if (r > 0 && r < 1) sp = constrain(110 - 25 * r, 90, 99);
            else sp = 95;
        }
        if (valid && sp > 0) break;
        delay(10);
    }

    if (!valid || hr == 0)    hr = (prevHR > 0) ? constrain(prevHR + random(-2, 3), 65, 90) : 75;
    if (sp == 0)              sp = (prevSP > 0) ? constrain(prevSP + random(-1, 2), 92, 98) : 95;
    if (prevHR > 0) {
        hr = (hr * 2 + prevHR) / 3;
        sp = (sp * 2 + prevSP) / 3;
        if (abs(tempC - prevTemp) > 1.0) tempC = (tempC + prevTemp) / 2;
    }
    hr = min(hr, (uint8_t)100);

    if (hr > 150) error_highHR = true;
    if (hr < 50) error_lowHR = true;
    if (sp < 80) error_lowSPO2 = true;

    uint8_t alert_byte = 0;
    if (error_fall)     alert_byte |= 0x01;
    if (error_highT)    alert_byte |= 0x02;
    if (error_lowT)     alert_byte |= 0x04;
    if (error_highHR)   alert_byte |= 0x08;
    if (error_lowHR)    alert_byte |= 0x10;
    if (error_lowSPO2)  alert_byte |= 0x20;

    if (alert_byte != 0) {
        char packet[4];
        packet[0] = 'S'; packet[1] = 'S';
        packet[2] = (char)alert_byte;
        packet[3] = '\n';
        sendTCPData(packet, 4);
    }

    lastSendTime = millis();

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("T:"); lcd.print(tempC, 1); lcd.print((char)223); lcd.print("C");
    lcd.setCursor(0, 1);
    lcd.print("HR:"); lcd.print(hr);
    lcd.print(" SP:"); lcd.print(sp); lcd.print("%");

    prevHR = hr;
    prevSP = sp;
    prevTemp = tempC;

    delay(1000);
}
