/** @package notifications
 *  Functor class hierarchy responsible for user notification of significant events
 *
 *  This module defines a class hierarchy of functors used to send emailed
 *  communications to the user when:
 *
 * * conditions in the tank become unsafe
 * * the user-specified informational period has arrived
 * * it's time to redo the ph sensor calibration
 *
 * @author  Ed Willis
 * @copyright Ed Willis, 2015, all rights reserved
 * @license  This software is released into the public domain
 */
#include <stdarg.h>
#include <Wire.h>
#include <Time.h>
#include <DS1307RTC.h>
#include <Timezone.h>
#include <LiquidCrystal.h>
#include <LCDKeypad.h>
#include <ArduinoJson.h>

/** The object representing the LCD display
 */
LCDKeypad lcd;

/** The local timezone
 */
Timezone* localTz = 0;

/** @defgroup TEMP_CONSTANTS constants and variables used in temperature sensor handling
 */

/** @addtogroup TEMP_CONSTANTS 
 *  @{
 */

/** The value of the 'other' resistor
 */
#define SERIESRESISTOR 10000    
 
/** The analog pin the sensor is connected to
 */
int THERMISTORPIN = -1;

/** How many samples to take to produce a temperature reading
 */
#define NUM_TEMP_SAMPLES 25

/** How long to wait between temperature samples in ms
 */
#define WAIT_BETWEEN_TEMP_SAMPLES 25

/** Resistance at 25 degrees C
 */
#define THERMISTORNOMINAL 10000      

/** Temperature for nominal resistance (almost always 25 C)
 */
#define TEMPERATURENOMINAL 25   

/** The beta coefficient of the thermistor (usually 3000-4000)
 */
#define BCOEFFICIENT 3950

/** @}
 */

/** Common size limit
 */
#define MAX_COLLECTION_SIZE 200

/** @defgroup PH_CONSTANTS constants and variables used in PH sensor handling
 */

/** @addtogroup PH_CONSTANTS
 *  @{
 */

/** The analog pin the ph sensor is connected to
 */
int PHPIN = -1;

/** Linear deviation compensate for PH value
 */
#define OFFSET -0.23

/** The number of samples to take to produce a PH reading
 */
#define NUM_PH_SAMPLES 5

/** How long to wait between PH samples in ms
 */
#define WAIT_BETWEEN_PH_SAMPLES 25

/** Convert a a Celcius value into Farenheit but scaled up by 10
 * 
 *  For example, 200 -> 680
 *
 *  @param celcius the value to convert (in 0.1s of degrees Celcius)
 *  @return the equivalent Farenheit value (in 0.1s of degrees Farenheit)
 */
int celciusToFarenheit(int celcius)
{
  return (int) ((int)((9 * celcius)/5) + 320);
}

/** Print a floating point number at the current cursor on the LCD 
 *
 *  Print to the current cursor on lcd a floating point value represented as
 *  an integer for the portion to the left of the decimal and another integer
 *  for the portion to the right.
 *
 *  @param lcd the display to write to
 *  @param left the integer value to right to the left of the decimal
 *  @param right the integer value to write to the right of the decimal
 *  @param units  a string which is appended to the output
 *  @param showZero 0 if only the left will be shown, 1 if the complete output will be
 */
void printPseudoFloat(LCDKeypad lcd, int left, int right, char * units, int showZero)
{
  lcd.print(left);
  if (showZero)
  {
    lcd.print(".");
    lcd.print(right);
  }
  lcd.print(units);
}

/** Get a temperature reading
 *
 *  Measure temperature from the thermistor, taking multiple readings to 
 *  arrive at a more consistent value.
 */
float getTemp()
{
  float reading = 0.0;
  int i = 0;
  for (i = 0; i<NUM_TEMP_SAMPLES; i++)
  {
    float next = analogRead(THERMISTORPIN);
    reading += next;
    delay(WAIT_BETWEEN_TEMP_SAMPLES);
  }
  reading /= (float) NUM_TEMP_SAMPLES;
  // convert the value to resistance
  reading = (float) 1023 / reading - 1;
  reading = SERIESRESISTOR / reading;
 
  float steinhart;
  steinhart = reading / THERMISTORNOMINAL;     // (R/Ro)
  steinhart = log(steinhart);                  // ln(R/Ro)
  steinhart /= BCOEFFICIENT;                   // 1/B * ln(R/Ro)
  steinhart += 1.0 / (TEMPERATURENOMINAL + 273.15); // + (1/To)
  steinhart = 1.0 / steinhart;                 // Invert
  steinhart -= 273.15;                         // convert to C
  return steinhart;
}

/** Get a PH reading
 *
 *  Get a PH reading, taking multiple samples to arrive at a more consistent
 *  value.
 */
float getPh()
{
  float ph=0.0;
  float voltage=0.0;
  float measurement=0.0;
  float next = 0.0;
  int i = 0;
  for (i=0; i<NUM_PH_SAMPLES; i++)
  {
    next = analogRead(PHPIN);
    measurement += next;
    delay(WAIT_BETWEEN_PH_SAMPLES);
  }
  measurement /= (float) NUM_PH_SAMPLES;
  voltage = measurement * 5.0 / 1024.0;
  ph = 3.5 * voltage + OFFSET;
  return ph;
}

/** send sensor measurements to the Raspberry Pi over serial
 *
 *  Send temperature and ph readings back to pi. Both arguments are 
 *  assumed to be 10 times larger than the actual values.  So 0.1s 
 *  of degree C and 0.1s of units of PH.
 *
 *  @param temp the temperature reading
 *  @param ph the PH reading
 */
void printTempAndPhToSerial(int temp, int ph)
{
  StaticJsonBuffer<MAX_COLLECTION_SIZE> jsonBuffer;
  JsonObject& root = jsonBuffer.createObject();
  root["temperature"] = temp/10.0;
  root["ph"] = ph/10.0;
  root.printTo(Serial);
  Serial.print("\n");
  Serial.flush();
}

/** Send a log message to serial so the Raspberry Pi can incude it in its logs
 *
 *  @param message the format string for the var_args message followed by
 *  additional parameters
 */
void logToSerial(const char * const message, ...)
{
  StaticJsonBuffer<MAX_COLLECTION_SIZE> jsonBuffer;
  char msg_buffer[MAX_COLLECTION_SIZE];
  va_list args;
  va_start(args, message);
  vsnprintf(msg_buffer, sizeof(msg_buffer), message, args);
  va_end(args);
  JsonObject& root = jsonBuffer.createObject();
  root["log"] = msg_buffer;
  root.printTo(Serial);
  Serial.print("\n");
  Serial.flush();
}

/** Initiaize the system and prepare to start takng measurements
 *
 *  Prepare LCD, serial, read the sensor pin configuration from serial
 *  and initialize the temperature and PH sensors and read the timezone
 *  configuration and initialize the timezone handling.
 */ 
void setup()
{
  char serial_buffer[MAX_COLLECTION_SIZE];
  char conversion[MAX_COLLECTION_SIZE];
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 1);
  setSyncProvider(RTC.get);
  Serial.begin(9600);
  pinMode(13, OUTPUT);
  int daylight = -1;
  int standard = -1;
  while (THERMISTORPIN == -1 || PHPIN == -1 || daylight == -1 || standard == -1)
  {
    int readCount = Serial.readBytes(serial_buffer, 199);
    serial_buffer[readCount] = '\0';
    StaticJsonBuffer<MAX_COLLECTION_SIZE> jsonBuffer;
    JsonObject& root = jsonBuffer.parseObject(serial_buffer);
    if (root.success()) {
      if (root.containsKey("thermistor_pin") && root.containsKey("ph_pin")) {
        const char* temp = root["thermistor_pin"];
        const char* ph = root["ph_pin"];
        THERMISTORPIN = strtol(&temp[1], 0, 10);
        PHPIN = strtol(&ph[1], 0, 10);
      }
      if (root.containsKey("daylight") && root.containsKey("standard")) {
        daylight = root["daylight"];
        standard = root["standard"];
      }
    }
  }
  logToSerial("thermistor pin set to: %d", THERMISTORPIN);
  logToSerial("ph pin set to: %d", PHPIN);
  TimeChangeRule DT = {"DT", Second, Sun, Mar, 2, daylight};
  TimeChangeRule ST = {"ST", First, Sun, Nov, 2, standard};
  logToSerial("daylight timezone offset set to:  %d", daylight);
  logToSerial("standard timezone offset set to:  %d", standard);
  localTz = new Timezone(DT, ST);
}

/** Measure temperature and ph and update serial and LCD with these values
 *
 *  @param showSerial 1, if we want the display updated with the sensor values
 */
void display(int showSerial)
{
  lcd.setCursor(0, 1);
  int tempC = (int) (getTemp() * 10);
  int tempCelLeft = tempC / 10;
  int tempCelRight = tempC % 10;
  if (tempCelRight >= 5)
  {
    tempCelLeft += 1;
  }
  int tempF = (int)(celciusToFarenheit(tempC));
  int tempFarLeft = tempF / 10;
  int tempFarRight = tempF % 10;
  if (tempFarRight >= 5)
  {
    tempFarLeft += 1;
  }
  printPseudoFloat(lcd, tempFarLeft, 0, "F", 0);
  lcd.print("/");
  printPseudoFloat(lcd, tempCelLeft, 0, "C", 0);
  int phTimesTen = getPh() * 10;
  int phLeft = phTimesTen / 10;
  int phRight = phTimesTen % 10;
  lcd.print("    ");
  printPseudoFloat(lcd, phLeft, phRight, "PH", 1);
  lcd.setCursor(0, 0);
  if (showSerial)
  {
    printTempAndPhToSerial(tempC, phTimesTen);
  }
  if (timeStatus() != timeSet)
  {
    lcd.print("No time source");
    logToSerial("no valid time source could be found");
  }
  else
  {
    time_t local = localTz->toLocal(now());
    lcd.print(dayShortStr(weekday(local)));
    lcd.print(" ");
    lcd.print(monthShortStr(month(local)));
    lcd.print(" ");
    lcd.print(day(local));
    if (day() < 10)
    {
      lcd.print(" ");
    }
    lcd.print(" ");
    if (hour(local) < 10)
    {
      lcd.print(" ");
    }
    lcd.print(hour(local));
    lcd.print(":");
    if (minute(local) < 10)
    {
      lcd.print("0");
    }
    lcd.print(minute(local));
  }
}

/** How often to take measurements of the sensors
 */
#define SERIAL_PERIOD 60*15

/** A counter used to determine whether or not to update the LCD with sensor data
 */
int serial_output_counter = 0;

/** The main alamode loop
 */
void loop()
{
  int showSerial;
  if ((SERIAL_PERIOD % serial_output_counter) == 0)
  {
    showSerial = 1;
  }
  else
  {
    showSerial = 0;
  }
  display(showSerial);
  delay(1000 - ((NUM_TEMP_SAMPLES * WAIT_BETWEEN_TEMP_SAMPLES) + (NUM_PH_SAMPLES * WAIT_BETWEEN_PH_SAMPLES))); // one second
  serial_output_counter += 1;
}
