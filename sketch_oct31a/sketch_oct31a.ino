#include <Adafruit_NeoPixel.h>

#define PINO 6
#define LEDS 24

Adafruit_NeoPixel pixels(
  LEDS,
  PINO,
  NEO_GRB + NEO_KHZ800
);

String comando = "";

void azul() {

  for(int i = 0; i < LEDS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }

  pixels.show();
}

void vermelho() {

  for(int i = 0; i < LEDS; i++) {
    pixels.setPixelColor(i, pixels.Color(255, 0, 0));
  }

  pixels.show();
}

void setup() {

  Serial.begin(9600);

  pixels.begin();

  azul();
}

void loop() {

  if (Serial.available()) {

    comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "MOVIMENTO") {
      vermelho();
    }

    if (comando == "NORMAL") {
      azul();
    }

  }
}