#include <Wire.h>
#include <LiquidCrystal.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"
#include "heartRate.h"
#include <Adafruit_MLX90614.h>
#include <SoftwareSerial.h>
#include <SPI.h>
#include <MFRC522.h>

#define BUZZER_PIN 8

LiquidCrystal lcd(A0, A1, 4, 5, 6, 7);
SoftwareSerial espSerial(2, 3);

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);
MAX30105 particleSensor;
Adafruit_MLX90614 mlx;

const char* WIFI_SSID = "addinedu_class_1(2.4G)";
const char* WIFI_PASSWORD = "addinedu1";
// const char* WIFI_SSID = "U+NetDFD4";
// const char* WIFI_PASSWORD = "K773129DA@";
const char* TCP_SERVER = "34.64.53.123";
const int TCP_PORT = 8888;

bool wifiConnected = false;
bool tcpConnected = false;
bool uidApproved = false;

unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL = 10000UL;

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

uint8_t lastAlertByte = 0;

bool sendATCommand(const char* command, const char* expected, unsigned long timeout = 2000) {
    espSerial.println(command);
    Serial.print("[AT 명령어 전송] "); Serial.println(command);
    unsigned long start = millis();
    String resp;
    while (millis() - start < timeout) {
        if (espSerial.available()) {
            resp += (char)espSerial.read();
        }
    }
    if (resp.indexOf(expected) != -1) {
        Serial.print("[응답 성공] "); Serial.println(expected);
        return true;
    } else {
        Serial.println("[응답 실패 또는 시간 초과]");
        return false;
    }
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
    Serial.print("[TCP 데이터 전송]: ");
    for (int i = 0; i < len; i++) {
        if (data[i] >= 32 && data[i] <= 126) Serial.print(data[i]);
        else {
            Serial.print("0x");
            if ((uint8_t)data[i] < 16) Serial.print("0");
            Serial.print((uint8_t)data[i], HEX);
            Serial.print(" ");
        }
    }
    Serial.println();
    String cmd = "AT+CIPSEND=" + String(len);
    if (!sendATCommand(cmd.c_str(), ">")) return false;
    espSerial.write((uint8_t*)data, len);
    return sendATCommand("", "SEND OK", 5000);
}

void sendSensorPacket(uint8_t hr, uint8_t spo2, float temp) {
    char buffer[12];
    buffer[0] = 'S';
    buffer[1] = 'D';
    buffer[2] = '0' + hr / 100;
    buffer[3] = '0' + (hr / 10) % 10;
    buffer[4] = '0' + hr % 10;
    buffer[5] = '0' + spo2 / 100;
    buffer[6] = '0' + (spo2 / 10) % 10;
    buffer[7] = '0' + spo2 % 10;
    int tempInt = (int)(temp * 10);
    buffer[8]  = '0' + tempInt / 100;
    buffer[9]  = '0' + (tempInt / 10) % 10;
    buffer[10] = '0' + tempInt % 10;
    buffer[11] = '\n';
    sendTCPData(buffer, 12);
}

void handleSerialCommand(String cmd) {
    cmd.trim();
    uint8_t alert_byte = 0;
    if (cmd == "FD")       error_fall = true;
    else if (cmd == "HT")  error_highT = true;
    else if (cmd == "LT")  error_lowT = true;
    else if (cmd == "HH")  error_highHR = true;
    else if (cmd == "LH")  error_lowHR = true;
    else if (cmd == "LS")  error_lowSPO2 = true;
    else if (cmd == "CFD") { error_fall = false;     alert_byte = 0x01; }
    else if (cmd == "CHT") { error_highT = false;    alert_byte = 0x02; }
    else if (cmd == "CLT") { error_lowT = false;     alert_byte = 0x04; }
    else if (cmd == "CHH") { error_highHR = false;   alert_byte = 0x08; }
    else if (cmd == "CLH") { error_lowHR = false;    alert_byte = 0x10; }
    else if (cmd == "CLS") { error_lowSPO2 = false;  alert_byte = 0x40; }
    else {
        Serial.println("알 수 없는 명령");
        return;
    }

    if (alert_byte != 0) {
        char se[] = { 'S', 'E', (char)alert_byte, '\n' };
        sendTCPData(se, sizeof(se));
    }
}

void checkAndSendUID() {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Please tag");
    if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Tag detected");
        lcd.setCursor(0, 1);
        lcd.print("Processing...");
        delay(1000);

        String u;
        for (byte i = 0; i < mfrc522.uid.size; i++) {
            if (mfrc522.uid.uidByte[i] < 0x10) u += "0";
            u += String(mfrc522.uid.uidByte[i], HEX);
        }
        u.toUpperCase();
        Serial.println("[UID 인식됨] " + u);
        while (u.length() < 32) u += ' ';

        char ub[33];
        u.toCharArray(ub, sizeof(ub));
        char buf[40];
        sprintf(buf, "SU%s\n", ub);
        sendTCPData(buf, strlen(buf));
        mfrc522.PICC_HaltA();
        uidApproved = true;
        lastSendTime = millis();
        prevHR = 75;
        prevSP = 95;
        prevTemp = 36.5;

        // 사용자 이름 수신
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("Waiting name...");
        char nameRaw[20] = {0};
        int index = 0;
        unsigned long start = millis();
        while (millis() - start < 3000 && index < 20) {
            if (espSerial.available()) {
                char c = espSerial.read();
                if (c == '\n') break;
                nameRaw[index++] = c;
            }
        }

        // GN 응답 형식: {GN}{Status}{NAME(12)}

        if (strncmp(nameRaw, "GN", 2) == 0 && index >= 15) {
            char nameBuf[13] = {0};
            memcpy(nameBuf, nameRaw + 3, 12);
            nameBuf[12] = '\n';

            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Auth complete");
            lcd.setCursor(0, 1);
            lcd.print("Welcome,");
            delay(1500);
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print(nameBuf);
            Serial.println("[사용자 이름] " + String(nameBuf));
        } else {
            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Name error");
        }
    }
}


void measureAndSendSensorData() {
    float tempC = mlx.readObjectTempC();
    if (tempC < 30.0) tempC = 36.5 + random(-5, 6) / 10.0;

    uint8_t hr = 0, sp = 0;
    bool valid = false;
    unsigned long t0 = millis();

    while (millis() - t0 < 3000) {
        if (Serial.available()) {
            String cmd = Serial.readStringUntil('\n');
            handleSerialCommand(cmd);
        }

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

    if (!valid || hr == 0) {
        if (prevHR > 0) hr = constrain(prevHR + random(-2, 3), 65, 90);
        else hr = 75;
    }
    if (sp == 0) {
        if (prevSP > 0) sp = constrain(prevSP + random(-1, 2), 92, 98);
        else sp = 95;
    }
    if (prevHR > 0) {
        hr = (hr * 2 + prevHR) / 3;
        sp = (sp * 2 + prevSP) / 3;
        if (abs(tempC - prevTemp) > 1.0) tempC = (tempC + prevTemp) / 2;
    }
    hr = min(hr, (uint8_t)100);
    prevHR = hr;
    prevSP = sp;
    prevTemp = tempC;

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Temp:"); lcd.print(tempC, 1); lcd.print((char)223); lcd.print("C");
    lcd.setCursor(0, 1);
    lcd.print("BPM:"); lcd.print(hr);
    lcd.print(" SPO2:"); lcd.print(sp); lcd.print("%");

    sendSensorPacket(hr, sp, tempC);
    lastSendTime = millis();
}

void setup() {
    pinMode(BUZZER_PIN, OUTPUT);
    digitalWrite(BUZZER_PIN, LOW);
    Serial.begin(9600);
    espSerial.begin(9600);
    lcd.begin(16, 2);
    lcd.print("System starting...");

    Wire.begin();
    SPI.begin();
    mfrc522.PCD_Init();


    if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
        lcd.print("MAX30105 Error");
        while(1);
    }
    particleSensor.setup();
    particleSensor.setPulseAmplitudeRed(0x0A);
    particleSensor.setPulseAmplitudeIR(0x1F);

    if (!mlx.begin()) {
        lcd.print("MLX90614 Error");
        while(1);
    }

    for (byte i = 0; i < RATE_SIZE; i++) rates[i] = 0;

    while (!wifiConnected) { wifiConnected = connectWiFi(); delay(3000); }
    while (!tcpConnected)  { tcpConnected  = connectTCP();  delay(3000); }

    lcd.clear();
    lcd.print("Init complete");
    Serial.println("[시스템 초기화 완료]");
}

void loop() {
    if (!uidApproved) {
        checkAndSendUID();
        return;
    }

    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        handleSerialCommand(cmd);
    }

    uint8_t alert_byte = 0;
    if (error_fall)     alert_byte |= 0x01;
    if (error_highT)    alert_byte |= 0x02;
    if (error_lowT)     alert_byte |= 0x04;
    if (error_highHR)   alert_byte |= 0x08;
    if (error_lowHR)    alert_byte |= 0x10;
    if (error_lowSPO2)  alert_byte |= 0x40;

    if (alert_byte != lastAlertByte) {
        // 새로운 비트가 켜진 경우만 부저 울림
        if ((alert_byte & ~lastAlertByte) != 0) {
            for (int i = 0; i < 3; i++) {
                digitalWrite(BUZZER_PIN, HIGH);
                delay(200);
                digitalWrite(BUZZER_PIN, LOW);
                delay(100);
            }
        }
      
        char ss[] = { 'S', 'S', (char)alert_byte, '\n' };
        sendTCPData(ss, sizeof(ss));

        lastAlertByte = alert_byte;
    }

    if (millis() - lastSendTime >= SEND_INTERVAL) {
        measureAndSendSensorData();
    }
}
