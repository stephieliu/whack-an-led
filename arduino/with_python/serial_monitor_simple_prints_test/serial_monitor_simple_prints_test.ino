void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
}

void loop() {
  // put your main code here, to run repeatedly:
  Serial.println("HelloWorld");
  delay(1000);

  Serial.println("INITGAME");
  delay(1000);

  Serial.println("STARTGAME");
  delay(1000);

  Serial.println("MOLETURNSTART");
  delay(1000);

  Serial.println("HITSUCCESS");
  delay(1000);

  Serial.print("CURRSCORE ");
  Serial.print(2);
  Serial.println();

  Serial.print("PLAYERSCORE ");
  Serial.print(2);
  Serial.println();

  Serial.println("HITFAIL");
  delay(1000);

  Serial.print("AVGREACTTIME ");
  Serial.print("3.0");
  Serial.println();
  delay(1000);

  Serial.print("TOTALCLICKS ");
  Serial.print("3");
  Serial.println();
  delay(1000);

  Serial.println("ENDGAME");
  delay(1000);
}
