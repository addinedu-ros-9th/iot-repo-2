#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc522(SS_PIN, RST_PIN);  // MFRC522 인스턴스 생성

void setup()
{
    Serial.begin(9600);
    SPI.begin();               // SPI 초기화
    mfrc522.PCD_Init();        // RFID 초기화
    Serial.println("RFID 준비 완료. 카드를 태그하세요.");
}

void loop()
{
    // 카드가 새로 인식되지 않았으면 리턴
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial())
    {
        return;
    }

    // UID 읽어서 출력
    Serial.print("UID: ");
    for (byte i = 0; i < mfrc522.uid.size; i++)
    {
        if (mfrc522.uid.uidByte[i] < 0x10)
        {
            Serial.print("0");  // 앞에 0 붙이기
        }
        Serial.print(mfrc522.uid.uidByte[i], HEX);
    }
    Serial.println();

    mfrc522.PICC_HaltA();  // 통신 종료
}
