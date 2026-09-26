// Optional ESP32 prototype. Bench validation required before attaching a pump.
// Libraries: DHT sensor library (Adafruit), Adafruit Unified Sensor, ArduinoJson 7.
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>
#include "config.h"

constexpr int SOIL_PIN=34, DHT_PIN=4, PUMP_PIN=26, TANK_LOW_PIN=27;
constexpr int DRY_ADC=3200, WET_ADC=1200; // Replace with measured calibration.
constexpr int PUMP_ON=HIGH, PUMP_OFF=LOW; // Verify your driver polarity.
DHT dht(DHT_PIN,DHT22);
uint32_t remainingMs=0, sequenceNo=0;
bool localTankLow(){ return digitalRead(TANK_LOW_PIN)==LOW; }
void off(){digitalWrite(PUMP_PIN,PUMP_OFF);}

void setup(){
  pinMode(PUMP_PIN,OUTPUT); off();
  pinMode(TANK_LOW_PIN,INPUT_PULLUP);
  Serial.begin(115200); dht.begin();
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  configTime(0,0,"pool.ntp.org","time.nist.gov");
}

void loop(){
  // Every network operation runs with the pump OFF. A bounded pulse follows a
  // fresh authenticated response; Wi-Fi failure cannot leave the output ON.
  off(); remainingMs=0;
  if(WiFi.status()!=WL_CONNECTED){delay(500);return;}
  float moisture=constrain(100.0f*(DRY_ADC-analogRead(SOIL_PIN))/(DRY_ADC-WET_ADC),0,100);
  float temperature=dht.readTemperature(), humidity=dht.readHumidity();
  time_t now=time(nullptr);
  if(isnan(temperature)||isnan(humidity)||now<1700000000){delay(500);return;}
  struct tm utc; gmtime_r(&now,&utc);
  char stamp[25]; strftime(stamp,sizeof(stamp),"%Y-%m-%dT%H:%M:%SZ",&utc);
  JsonDocument body;
  body["device_id"]=DEVICE_ID;
  body["sample_id"]=String((uint32_t)now)+"-"+String(sequenceNo++);
  body["timestamp"]=stamp;
  body["soil_moisture"]=moisture;
  body["temperature"]=temperature;
  body["humidity"]=humidity;
  body["light_level"]=0; // Not fitted; replace with calibrated light measurement.
  body["water_tank_level"]=localTankLow()?0:100; // Binary float switch, not percentage measurement.
  String payload; serializeJson(body,payload);
  WiFiClientSecure tls; tls.setCACert(ROOT_CA);
  HTTPClient http;
  http.setConnectTimeout(3000); http.setTimeout(3000);
  if(!http.begin(tls,String(API_URL)+"/api/sensors/data")){delay(500);return;}
  http.addHeader("Content-Type","application/json");
  http.addHeader("X-Device-Key",DEVICE_KEY);
  uint32_t sentAt=millis();
  int code=http.POST(payload);
  JsonDocument reply;
  if(code==200 && !deserializeJson(reply,http.getString())){
    double remaining=(reply["pump_until"].as<double>()-reply["server_time"].as<double>())*1000;
    remaining-=(millis()-sentAt); // Conservatively subtract complete request latency.
    if(reply["pump_on"].as<bool>() && remaining>0 && moisture<reply["target_moisture"].as<float>() && !localTankLow()){
      remainingMs=(uint32_t)min(remaining,1000.0); // At most one second per fresh response.
    }
  }
  http.end();
  uint32_t pulseStart=millis();
  if(remainingMs){
    digitalWrite(PUMP_PIN,PUMP_ON);
    while(millis()-pulseStart<remainingMs && !localTankLow()){delay(10);}
  }
  off(); delay(2100); // DHT22 requires at least two seconds between samples.
}
