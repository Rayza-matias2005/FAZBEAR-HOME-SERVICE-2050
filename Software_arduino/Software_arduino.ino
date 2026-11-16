#include <Adafruit_NeoPixel.h>

#define PINO_1 6
#define PINO_2 7
#define LEDS   12

Adafruit_NeoPixel anel1(LEDS, PINO_1, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel anel2(LEDS, PINO_2, NEO_GRB + NEO_KHZ800);

String comando = "";

void pintarTodos(uint8_t r, uint8_t g, uint8_t b) {
  // Prepara a cor dos dois anéis primeiro...
  for (int i = 0; i < LEDS; i++) {
    anel1.setPixelColor(i, anel1.Color(r, g, b));
    anel2.setPixelColor(i, anel2.Color(r, g, b));
  }
  // ...e envia os dois um logo após o outro
  anel1.show();
  anel2.show();
}

void azul()     { pintarTodos(0, 0, 255); }
void vermelho() { pintarTodos(255, 0, 0); }

void setup() {
  Serial.begin(9600);
  anel1.begin();
  anel2.begin();
  azul();
}

void loop() {
  if (Serial.available()) {
    comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando == "MOVIMENTO") vermelho();
    if (comando == "NORMAL")    azul();
  }
}