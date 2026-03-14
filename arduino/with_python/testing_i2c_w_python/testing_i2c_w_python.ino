/**
========================================================
hardware components
========================================================
- start/reset button --> pin 13
- status rgb led --> pins 6 (red), 5 (blue), 3 (green)
- play buttons:
  - hole 1 = pin 8
  - hole 2 = pin 7
  - hole 3 = pin 4
  - hole 4 = pin 2
- play leds:
  - hole 1 = pin 12
  - hole 2 = pin 11
  - hole 3 = pin 10
  - hole 4 = pin 9
- optional: create a 3d printed enclosure to look like an actual arcade game??
========================================================
pseudocode
========================================================
initialization:
--------------------------------------------------------
- start button --> on click, starts running a new game
- initialize all timer variables:
  - decrementTime = the constant interval to decrease the moleTime by after each successful hit, so that the difficulty increases (default to 100ms)
  - moleTime = the constant interval (for comparing successful hits) between the mole popping out of a new hole (default to 2 seconds, then decreases by decrementTime in the event of a successful hit)
    - note: moleTime should be bounded at 0.25s --> this is approx. typical human reaction time
  - elapsedTurnTime = the time since the mole popped out of the hole most recently (to be compared w/ moleTime) (default to 0 seconds)
  - playerScore = the player's current score, which will increment with each successful hit (default value to 0)
  - ledRandSelector = to choose which led to light up (will be a randomly generated number btwn 1-4)
  - playTime = total play time elapsed since the start of the current round (default value to 0)
  - failCount = the number of times the player has failed to hit the mole, to be compared with the threshold to determine whether the game ends (default to 0)
  - failThreshold = number of times the player can fail before game is over (default value to 3)
- blink status led BLUE 3 times, then start recording all timed events
--------------------------------------------------------
during the game:
--------------------------------------------------------
- randomly generate a number btwn 1-4 for corresponding led to light up
- light up the corresponding led (moleActive function)
- now timer is running, check events:
  - check for a successful player hit in moleTime interval since the moleActive function was sent
    - upon hit, turn off the mole led and update the variables and timers:
      - playerScore ++
      - elapsedTurnTime reset to 0
      - flash status led GREEN
      - update the time interval variable (moleTime) --> recall: this variable is the duration to check btwn each new led blink (when the mole pops out of the hole)
      - ledRandSelector updates after moleTime --> recall: this variable will select a number from 1-4 to light up a new led at random
    - if the time limit is exceeded (i.e. elapsedTurnTime > moleTime) then the player has failed:
      - flash status led RED
      - failCount++
      - check if failCount has exceeded failThreshold
        - endGame flag set to true
      - if failCount still in the threshold, continue with the game
        - elapsedTurnTime reset to 0
        - DO NOT update the time interval variable (moleTime)
        - ledRandSelector chooses a new hole for the mole to pop up after moleTime has passed
---------------------------------------------------------
ending the game:
---------------------------------------------------------
- once the user has missed a mole and the game is over, proceed to turn off and reset everything
  - turn off all game leds
  - print the playerScore to serial
    - optional: track the current run's best score?
    - optional: have different difficulty modes (shorter interval btwn moles popping up)
  - reset the playerScore = 0
  - set status led to BLUE
  - wait for user to click the start button (beginning a new game!)
*/

//=======================================================
//VARIABLES
//=======================================================
//hardware component pins
//-------------------------------------------------------
//buttons:
//start button for game
const byte startButtonPin = 13;
//mole hole buttons
const byte hole1ButtonPin = 8;
const byte hole2ButtonPin = 7;
const byte hole3ButtonPin = 4;
const byte hole4ButtonPin = 12;
byte holeButtons [4] = {hole1ButtonPin, hole2ButtonPin, hole3ButtonPin, hole4ButtonPin};
//mole hole interrupt button
const byte buttonIntPin = 2;

//leds:
//for the rgb led
const byte statusLED_R = 6;
const byte statusLED_G = 3;
//mole hole leds
const byte hole1LEDPin = 5;
const byte hole2LEDPin = 11;
const byte hole3LEDPin = 10;
const byte hole4LEDPin = 9;
byte holeLED [4] = {hole1LEDPin, hole2LEDPin, hole3LEDPin, hole4LEDPin};

//--------------------------------------------------------
//timing events
//--------------------------------------------------------
volatile int count_hundred_ms = 0; //counts time in ms
volatile int count_secs = 0; //counts time in s
//int buttonPressed_time = 0;

volatile int count_star_winks = 0; //counts whether star should wink (resets every 500ms)
volatile bool starWink = false; //start the star animation in initial image

//volatile interrupt/timing-related variables
volatile int numPlayerClicks = 0; //number of clicks done by user throughout the game

//boolean flags to control the game status (start/end game)
bool gameOn = false;
bool endGame = false;

//game/player variables
int randLEDSelector = 0;

const int DECREMENT_TIME = 1; //start with 100ms decreasing interval
const int MOLE_TIME = 20; //start with 2s interval (20 * 100ms)
const int LOW_MOLE_THRESHOLD = 2; //limit mole time to 200 ms as the lowest possible interval

int moleTime = 0; //these timing values will change as the game progresses
volatile int elapsedTurnTime = 0;

bool playerTurn = false; //indicates whether it is time for player's turn

const int failThreshold = 3; //start with 3 fails allowed
int failCount = 1; //start with 0 fails in the current game

int playerScore = 0; //player score for the current game
volatile int playTime = 0; //how long the game is lasting
double avgReactionTime = 0; //how long the player takes to react to the mole on average

//program initialization
void setup() {
  Serial.begin(115200);//serial begin at port 115200

  //TIMER SETUP
  cli(); //clear global interrupt enable flag bit (disable all interrupts initially)
  //init timer1 control registers a and b
  TCCR1A = 0;
  TCCR1B = 0;

  //set prescaler to 64
  TCCR1B |= B00000011;//CS11 and CS10 bits set to 1 for prescaler = 64 (see atmega datasheet)
  //this sets the clock frequency to freq/64 = 16MHz/64 = 0.25MHz = 250 kHz

  //this is the timer/counter register, holding the timer's value in counts
  //for timer1, there are 16 bits --> can hold up to 2^16 = 65535
  TCNT1 = 40535;//preload timer to 40535
    //the purpose of doing the timer preload is so that there will be a defined number of counts until overflow for each clock cycle --> 65535 - 40535 = 25000 'ticks'
    //the arduino frequency is 16MHz = 1 tick every 62.5us
    //but because of the prescaler, the new frequency is 0.25MHz = 1 tick every 4000ns = 4 us
    //so with this preload, 25000 * 4us = 100000 us = 100ms --> approx. 100 ms per clock cycle

  //enable timer overflow interrupt
  TIMSK1 |= B00000001; //the timsk register bit 0 is TOIE1
    //write TOIE1 = 1 to enable overflow interrupt
  
  sei(); //set interrupt global flag (reenable interrupts after initializing timer)

  //handle other initializations
  initComponents();
  initGame();
  initTime();
}

//initialize hardware setup
void initComponents(){
  Serial.println("INITCOMP");
  // Serial.println("Setting up hardware...");

  //set button pins to input
  //start button pin
  pinMode(startButtonPin, INPUT_PULLUP);
  //hole button pins
  pinMode(hole1ButtonPin, INPUT_PULLUP);
  pinMode(hole2ButtonPin, INPUT_PULLUP);
  pinMode(hole3ButtonPin, INPUT_PULLUP);
  pinMode(hole4ButtonPin, INPUT_PULLUP);
  //attach interrupt to pin2, which will trigger on any button click
  //buttons are input_pullup, so they start HIGH and go LOW on click
  attachInterrupt(digitalPinToInterrupt(buttonIntPin), clickCounter, FALLING);

  //set led pins to output
  //status led pins
  pinMode(statusLED_R, OUTPUT);
  pinMode(statusLED_G, OUTPUT);
  //hole led pins
  pinMode(hole1LEDPin, OUTPUT);
  pinMode(hole2LEDPin, OUTPUT);
  pinMode(hole3LEDPin, OUTPUT);
  pinMode(hole4LEDPin, OUTPUT);

  //set initial led states
  //status led pins
  digitalWrite(statusLED_R, LOW);
  digitalWrite(statusLED_G, HIGH); //turn on green status indicator at the start of the game
  //hole led pins
  digitalWrite(hole1LEDPin, LOW);
  digitalWrite(hole2LEDPin, LOW);
  digitalWrite(hole3LEDPin, LOW);
  digitalWrite(hole4LEDPin, LOW);
}

//initialize variables for the game
void initGame(){
  Serial.println("INITGAME");

  failCount = 0;
  playTime = 0;
  randLEDSelector = 0;
  playerTurn = false;
  playerScore = 0; //player score for the current game
  avgReactionTime = 0;
}

//initialize variables for counters and timers
void initTime(){
  Serial.println("INITTIME");

  //reset time counters
  count_hundred_ms = 0;
  count_secs = 0;
  count_star_wink = 0;
  moleTime = MOLE_TIME;
  elapsedTurnTime = 0;
}

//end the current game
void resetGame(){
  Serial.println("RESETGAME");

  //set status led RED
  int currentTime = count_hundred_ms;
  while(count_hundred_ms < currentTime + 30){ //keep the led on for 3000ms
    digitalWrite(statusLED_R, HIGH);
  }

  //reset game status variables
  gameOn = false;
  endGame = false;

  //report player's score
  Serial.print("PLAYERSCORE ");
  Serial.print(playerScore);
  Serial.println();
  
  //report player's statistics
  Serial.print("TOTALCLICKS ");
  Serial.print(numPlayerClicks);
  // Serial.print(" times!");
  Serial.println();
  
  //report the total play time (player's turn duration) in ms
  Serial.print("TOTALPLAYTIME ");
  Serial.print(playTime*100);
  Serial.println();

  //calculate average reaction time
  if(playerScore > 0){
	  avgReactionTime = (playTime*100)/playerScore;
  }
  
  Serial.print("AVGREACTTIME ");
  Serial.print(avgReactionTime);
  Serial.println();

  //turn off mole hole leds
  //run resets for all variable
  initComponents();
  initGame();
  initTime();
}

//special interrupt function ISR: for tracking timer variables
ISR(TIMER1_OVF_vect) {
  TCNT1 = 40535; //preload timer
  //handle 100ms timer interrupt
  count_hundred_ms++; //this will increment every 100ms

  elapsedTurnTime++; //increments every 100ms

  if (count_hundred_ms % 10 == 0) {
    count_secs++; //this variable counts time in seconds
  }
  
  if(playerTurn){
    playTime ++; //counts the player's turn duration TOTAL in hundred ms
  }

  if(count_hundred_ms % 5 == 0){
    count_star_wink++; //updates star img every 500ms (each count = star wink)
    if(count_star_wink % 2 == 0){
      starWink = false;
    }
    else{
      starWink = true; //swap the blink status every other count
    }
  }
}

//interrupt function
//this will keep a counter of the total clicks done by the user
void clickCounter(){
  if(playerTurn) //only count clicks done during a valid turn
    numPlayerClicks++;
}

//main event loop: will call other functions to actually make the game run
void loop() {
  //top priority: check if the game end status is true (need to reset the game in that case)
  if(endGame){
    Serial.println("ENDGAME");
    resetGame(); //run the reset function
  }

  if(starWink){
    //send the blinking command
    Serial.println("STARWINK");
    starWink = false; //reset so it doesn't update twice (i.e. if it also triggers inside the loop)
  }

  //wait until the player presses the start button
  if((digitalRead(startButtonPin) == LOW) && !gameOn){
    //start the new game
    Serial.println("STARTGAME");

    gameOn = true; //game is currently going

    if(starWink){
      //send the blinking command
      Serial.println("STARWINK");
      starWink = false;//reset so it doesn't update twice (i.e. if it also triggers inside the nested loop)
    }

    //blink the status led blue 3 times
    for (int i = 0; i<3; i++){
      //implementing delay(1 second) with the clock instead
      int blinkTimeTmp = count_secs;
      while(count_secs < blinkTimeTmp + 1){
    	  digitalWrite(statusLED_G, LOW);
      }
      blinkTimeTmp = count_secs;
      while(count_secs < blinkTimeTmp + 1){
    	  digitalWrite(statusLED_G, HIGH);
      }

      if(starWink){
        //send the blinking command
        Serial.println("STARWINK");
        starWink = false;//reset so it doesn't update twice (i.e. if it also triggers inside the nested loop)
      }
    }
    digitalWrite(statusLED_G, LOW); //turn off blue status indicator once the game really begins
	
    //set the current elapsed interval time
    elapsedTurnTime = 0;
    
    while(gameOn && !endGame){
      //top priority: check if the game end status is true (need to reset the game in that case)
      if(endGame){
        Serial.println("ENDGAME");
        resetGame(); //run the reset function
      }

      if(starWink){
        //send the blinking command
        Serial.println("STARWINK");
        starWink = false;//reset so it doesn't update twice (i.e. if it also triggers inside the nested loop)
      }
  //    playRound();
      if(elapsedTurnTime >= moleTime && !playerTurn && !endGame){
        Serial.println("MOLETURNSTART");

        //turn off led status indicator
        digitalWrite(statusLED_R, LOW);
        digitalWrite(statusLED_G, LOW);

        //generate a random led to light up
        randLEDSelector = random(4); //random number from 0 - 3

        //turn on the selected led
        digitalWrite(holeLED[randLEDSelector], HIGH);

        //set the elapsed time to track user's turn
        playerTurn = true; //indicate that the player buttons can now be read
      }

      //check if enough time has elapsed to set a new mole
      if(playerTurn){
		    elapsedTurnTime = 0; //start the player's turn time

        bool hitSuccess = false; //to track whether the player successfully hit the mole this time

        while(elapsedTurnTime <= moleTime){
          if(starWink){
            //send the blinking command
            Serial.println("STARWINK");
            starWink = false;//reset so it doesn't update twice (i.e. if it also triggers inside the nested loop)
          }

          Serial.println("PLAYERTURNSTART");
          //check for user input to the correct button
          if(digitalRead(holeButtons[randLEDSelector]) == LOW && !hitSuccess){
            //set status led GREEN
            digitalWrite(statusLED_G, HIGH);
            Serial.println("HITSUCCESS");
            hitSuccess = true;

            //increment player score
            playerScore++;
            
            Serial.print("CURRSCORE ");
            Serial.print(playerScore);
            Serial.println();
            
            //turn off the mole LED
            digitalWrite(holeLED[randLEDSelector], LOW);
            
            //update time interval
            if(moleTime > LOW_MOLE_THRESHOLD){
              moleTime -= DECREMENT_TIME;
            }
           	Serial.print("CURRTIMEINT ");
            Serial.print(moleTime);
            Serial.println();
            break; //go to next turn immediately
          }
        }
        //catch if the player failed to hit the mole this time
        if(!hitSuccess){
          //print the fail statement to the serial monitor
        	Serial.println("HITFAIL");

          //set status led RED
          digitalWrite(statusLED_R, HIGH);

          //update the fail counter
          failCount++;
          Serial.print("CURRFAILCNT ")
          Serial.print(failCount);
          Serial.println();
          
          //check if the endGame condition is met (exceeded failure threshold):
          if(failCount == failThreshold){
            Serial.println("EXCEEDFAIL")
            endGame = true;
            break;
          }
        }
        
        //make sure mole light is off
        digitalWrite(holeLED[randLEDSelector], LOW);

        Serial.println("PLAYERTURNEND");
        playerTurn = false; //indicate that the player turn is over
        
		    elapsedTurnTime = 0; //at the end of the player's turn, reset the turn time going into the new mole popping out
      }
    }
  }
}