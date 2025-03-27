#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include "HT_SSD1306Wire.h"

// Configuração do OLED (compatível com Heltec)
#ifdef WIRELESS_STICK_V3
SSD1306Wire oledDisplay(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_64_32, RST_OLED);
#else
SSD1306Wire oledDisplay(0x3c, 500000, SDA_OLED, SCL_OLED, GEOMETRY_128_64, RST_OLED);
#endif

// Pinos do RFID (ajuste conforme seu hardware)
#define RFID_SDA 25
#define RFID_SCK 17
#define RFID_MOSI 13
#define RFID_MISO 12
#define RFID_RST 22

MFRC522 mfrc522(RFID_SDA, RFID_RST);
unsigned long lastReadTime = 0;

void VextON() {
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, LOW);
}

void showWelcomeMessage() {
  oledDisplay.clear();
  oledDisplay.setFont(ArialMT_Plain_16);
  oledDisplay.setTextAlignment(TEXT_ALIGN_CENTER);
  oledDisplay.drawString(64, 24, "Aproxime o cartão");
  oledDisplay.display();
}

void setup() {
  Serial.begin(9600);
  while (!Serial); // Aguarda a conexão serial

  // Inicializa o OLED
  VextON();
  delay(100);
  oledDisplay.init();
  oledDisplay.clear();
  oledDisplay.display();
  
  oledDisplay.setFont(ArialMT_Plain_16);
  oledDisplay.setTextAlignment(TEXT_ALIGN_CENTER);
  oledDisplay.drawString(64, 24, "RFID Ready");
  oledDisplay.display();
  delay(2000);
  showWelcomeMessage();

  // Inicializa o RFID
  SPI.begin(RFID_SCK, RFID_MISO, RFID_MOSI);
  mfrc522.PCD_Init();
  mfrc522.PCD_DumpVersionToSerial(); // Debug: exibe a versão do RFID
  Serial.println(F("Aproxime o cartão RFID..."));
}

void loop() {
  // Reseta a mensagem de boas-vindas após 3 segundos sem leitura
  if (lastReadTime != 0 && (millis() - lastReadTime >= 3000)) {
    showWelcomeMessage();
    lastReadTime = 0;
  }

  // Verifica se há um novo cartão presente
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  // Monta o UID como string
  String uidStr;
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    uidStr += (mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) uidStr += ":";
  }
  uidStr.toUpperCase();

  // Exibe o UID no OLED
  oledDisplay.clear();
  oledDisplay.setFont(ArialMT_Plain_16);
  oledDisplay.setTextAlignment(TEXT_ALIGN_CENTER);
  oledDisplay.drawString(64, 0, "UID RFID:");
  oledDisplay.drawString(64, 24, uidStr);
  oledDisplay.display();

  // Envia o UID pela serial
  Serial.print("UID: ");
  Serial.println(uidStr);

  lastReadTime = millis();
  mfrc522.PICC_HaltA(); // Para a leitura do cartão atual
}