#include <Wire.h>
#include <Time.h>
#include <DS1307RTC.h>
#include <Timezone.h>
#include <LiquidCrystal.h>
#include <LCDKeypad.h>

LCDKeypad lcd;

Timezone* localTz = 0;

// TEMPERATURE CONSTANTS

// the value of the 'other' resistor
#define SERIESRESISTOR 10000    
 
// What pin to connect the sensor to
#define THERMISTORPIN A1

#define NUM_TEMP_SAMPLES 25

#define WAIT_BETWEEN_TEMP_SAMPLES 25

// resistance at 25 degrees C
#define THERMISTORNOMINAL 10000      

// temp. for nominal resistance (almost always 25 C)
#define TEMPERATURENOMINAL 25   

// The beta coefficient of the thermistor (usually 3000-4000)
#define BCOEFFICIENT 3950

// the value of the 'other' resistor
#define SERIESRESISTOR 10000    


// PH CONSTANTS AND VARIABLES
#define PHPIN A2               //pH meter Analog output to Arduino Analog Input 0

#define OFFSET -0.23           //deviation compensate

#define NUM_PH_SAMPLES 5

#define WAIT_BETWEEN_PH_SAMPLES 25

// 10s of degrees
int celciusToFarenheit(int celcius)
{
  return (int) ((int)((9 * celcius)/5) + 320);
}

// Print to the current cursor on lcd a floating point value
// represented as an integer for the portion to the left of the
// decimal and another integer for the portion to the right.
// Units is a string which is appended to the output.
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

// Measure temperature from the thermistor, taking multiple readings to 
// arrive at a more consistent value
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

// Send temperature and ph readings back to pi. Both arguments are 
// assumed to be 10 times larger than the actual values.  So 0.1s 
// of degree C and 0.1s of units of PH
void printTempAndPhToSerial(int temp, int ph)
{
  Serial.print("T: ");
  Serial.print((float)temp/10.0);
  Serial.print("\n");
  Serial.print("P: ");
  Serial.print((float)ph/10.0);
  Serial.print("\n");
}

void setup()
{
  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 1);
  setSyncProvider(RTC.get);
  TimeChangeRule usEDT = {"EDT", Second, Sun, Mar, 2, -240};  //UTC - 4 hours
  TimeChangeRule usEST = {"EST", First, Sun, Nov, 2, -300};   //UTC - 5 hours
  localTz = new Timezone(usEDT, usEST);
  Serial.begin(9600);
  pinMode(13, OUTPUT);
}

// Measure temperature and ph and pdate serial and LCD with
// these values
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

#define SERIAL_PERIOD 60*15

int serial_output_counter = 0;

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
