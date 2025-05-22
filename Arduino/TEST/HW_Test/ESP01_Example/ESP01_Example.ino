#include <SoftwareSerial.h>

SoftwareSerial esp(2, 3); // RX, TX

void setup() {
  Serial.begin(9600); // PC 모니터용
  esp.begin(9600);    // ESP-01 통신

  Serial.println("Ready. Type AT commands.");
}

void loop() {
  if (Serial.available()) {
    esp.write(Serial.read());  // PC → ESP
  }
  if (esp.available()) {
    Serial.write(esp.read());  // ESP → PC
  }
}
