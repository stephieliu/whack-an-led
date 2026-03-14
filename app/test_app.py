"""
NOTES & PSEUDOCODE

STORED VARS
- best score
- current score
- longest playtime
- lowest avg reaction time
- shortest mole time interval reached
- number of clicks on average
- current number of fails (out of fail threshold number)

PYTHON APP
- default structure of the app (on launch):
	- title
	- show message to prompt the game starting
		- i.e. "hit the blue button to start the game!"
	- play intro music?
    - start running the threaded reader right on launch for the serial monitor
		- once STARTGAME message is read from serial, game has started --> update app display

- during the game:
	- keep title
    - show current game stats:
        - current score
        - current playtime
        - current mole time interval
        - indicate when the mole pops up
        - current number of fails / fail threshold
        - on hits, i.e. HITSUCCESS or HITFAIL
            - report the status
            - play sounds for successful hit and failed hit
    - exit the game when ENDGAME is read

- on game ending:
    - keep title
    - show the round's stats:
        - score
        - best score
        - playtime
        - longest playtime
        - shortest mole interval reached
        - avg reaction time
        - best reaction time
        - number of clicks on avg

LEARNING NOTES (TKINTER)
- parent root frame is automatically created
- can check all the configs for some widget by passing widgetname.configure() in terminal
- specify widget callbacks to update variables, eg. ttk.Button(mainframe, text='calculate', command=calculate)
    - calls the calculate method on click
- basic widgets:
    - frame = displays as a simple rectangle, for organizing ui
        - similar to div in html
    - label = display text/images for viewing, not interacting
        - use to show results
        - can set contents to textvariable = somestringvar where somestringvar = StringVar() object
            - can get and set the StringVar: somestringvar.get() or somestringvar.set('new val')
        - image display with img=PhotoImage('imagepath.png')
            - use label image = img
"""

#initial imports
import serial
import threading
import queue
import time
import logging

import tkinter as tk
from tkinter import *
from tkinter import ttk, font

from playsound3 import playsound
from PIL import Image, ImageTk

#setup the debug logger
#create logger
logger = logging.getLogger('default_logger')
logger.setLevel(logging.DEBUG)

#make filehandler
fh = logging.FileHandler(filename='wal_app.log', mode='w')
fh.setLevel(logging.DEBUG)

#make console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

#formatter for log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#add formatter to handlers
ch.setFormatter(formatter)
fh.setFormatter(formatter)

#add handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)

#initialize global overall game tracker variables
FAIL_THRESHOLD = 3
BEST_SCORE = 0
LONGEST_PLAYTIME = 0
SHORTEST_MOLE_INT = None
BEST_REACT_TIME = None
TOTAL_CLICKS = 0
NEW_MOLE = False #tracks whether the mole is here to be hit
HIT_SUCCESS = False #whether the hit was successful
HIT_FAIL = False # whether the hit failed

#dynamic variable updates
GAME_ON = False
CURR_SCORE = 0
CURR_CLICKS = 0
CURR_PLAYTIME = 0
CURR_REACT_TIME = 0
CURR_MOLE_INT = 0
CURR_FAIL_CNT = 0

STARWINK = False #will update every 1000ms to "wink" the star icon
#if false, displays star1
#if true, displays star2

#initialize sound file directories
background_music_path = 'sounds/djartmusic-best-game-console-301284.mp3'
startgame_music_path = 'sounds/freesound_community-game-start-6104.mp3'
success_music_path = 'sounds/freesound_community-retro-video-game-coin-pickup-38299.mp3'
fail_music_path = 'sounds/universfield-retro-game-shot-2-152053.mp3'

#initialize images and resize for the ui display
star1_path = 'graphics/star_1.png'
star2_path = 'graphics/star_2.png'
#read image and resize to fit 50x50
STAR1 = Image.open(star1_path) #initial icon
STAR1 = STAR1.resize((50, 50))

#set up the serial port to be read
ser = serial.Serial('COM4', 115200, timeout=2)
time.sleep(0.2) #wait for port to be opened

#playerRoundStats class will hold variables for the current round
#handle reading of threaded serial monitor and update variables
# class playerRoundStats:
#     def __init__(self):
#         self.round_score = 0
#         self.avg_react_time = 0
#         self.play_time = 0
#         self.mole_time_int = 0
#         self.fail_cnt = 0
#         self.total_clicks = 0

#threaded serial reader class for continuous polling of the serial monitor
#adapted from the official pyserial documentation: https://www.pyserial.org/docs/reading-data
class ThreadedSerialReader:
    def __init__(self, ser, queue_size=1000):
        self.ser = ser
        # self.player = playerRoundStats() #make a new player obj for the current round
        self.commandList = [
            'INITCOMP', #initializing hardware setup
            'INITGAME',
            'INITTIME',
            'RESETGAME',
            'PLAYERSCORE',
            'TOTALCLICKS',
            'TOTALPLAYTIME',
            'AVGREACTTIME',
            'ENDGAME',
            'STARTGAME',
            'MOLETURNSTART',
            'PLAYERTURNSTART',
            'HITSUCCESS',
            'CURRSCORE',
            'CURRTIMEINT',
            'HITFAIL',
            'CURRFAILCNT',
            'EXCEEDFAIL',
            'PLAYERTURNEND',
            'STARWINK',
        ]

        self.data_queue = queue.Queue(maxsize=queue_size)
        self.running = True
        self.thread = None
    
    def start(self):
        """Start background reading thread"""
        self.thread = threading.Thread(target=self._read_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def _read_loop(self):
        """Background reading loop"""
        while self.running:
            try:
                if self.ser.in_waiting:
                    data = self.ser.readline() #modified to read by lines instead of raw data
                    if data:
                        try:
                            self.data_queue.put(data, timeout=0.1)
                            self.handleData(data.decode('utf-8').rstrip())
                        except queue.Full:
                            print("Queue full, dropping data")
                else:
                    time.sleep(0.001)  # Small delay when no data
            except Exception as e:
                if self.running:
                    print(f"Read thread error: {e}")
    
    def get_data(self, timeout=0.1):
        """Get data from queue"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_all_data(self):
        """Get all queued data"""
        data = []
        while not self.data_queue.empty():
            try:
                data.append(self.data_queue.get_nowait())
            except queue.Empty:
                break
        return b''.join(data)
    
    def clear_data(self):
        with self.data_queue.mutex: #lock the thread (for thread safety)
            return self.data_queue.queue.clear() #clear the queue contents
    
    def stop(self):
        """Stop reading thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    #the methods below help with catching the game stats throughout
    def handleData(self, data):
        # print(data.split(' '))
        commandName = data.split(' ')[0] #this separates the actual command from the data value if it exists (eg. PLAYERSCORE [playerscore])

        #set global vars
        global HIT_FAIL, NEW_MOLE, BEST_REACT_TIME, BEST_SCORE, SHORTEST_MOLE_INT, FAIL_THRESHOLD, HIT_SUCCESS, TOTAL_CLICKS, LONGEST_PLAYTIME, GAME_ON, STARWINK

        #also global vars for current stats
        global CURR_SCORE, CURR_CLICKS, CURR_PLAYTIME, CURR_REACT_TIME, CURR_MOLE_INT, CURR_FAIL_CNT

        if not commandName in self.commandList:
            logger.debug('Command not in list.')
        else:
            if 'INIT' in commandName:
                #game is initializing
                logger.debug('Initializing game.')
            elif 'RESET' in commandName:
                #game is resetting (round has ended)
                #play sound effect
                logger.debug('Game is resetting.')
            elif 'PLAYERSCORE' in commandName:
                val = int(data.split(' ')[1]) #get the numerical value after (this is the string)
                #update the player score variable
                CURR_SCORE = val

                #also update best score if needed
                if BEST_SCORE < val:
                    BEST_SCORE = val
                    logger.debug(f'New best score set: {BEST_SCORE}')
            elif 'TOTALCLICKS' in commandName:
                val = int(data.split(' ')[1]) #get the numerical value after (this is the string)
                #update the total clicks variable
                CURR_CLICKS = val

                #also update total clicks
                TOTAL_CLICKS += val
                logger.debug(f'Updated clicks count: {TOTAL_CLICKS}')
            elif 'TOTALPLAYTIME' in commandName:
                val = int(data.split(' ')[1]) #get the numerical value after (this is the string)
                #update the player score variable
                CURR_PLAYTIME = val

                #also update best score if needed
                if LONGEST_PLAYTIME < val:
                    LONGEST_PLAYTIME = val
                    logger.debug(f'New longest playtime set: {LONGEST_PLAYTIME}')
            elif 'AVGREACTTIME' in commandName:
                val = float(data.split(' ')[1]) #get the numerical value after (this is the string)
                #update the player score variable
                CURR_REACT_TIME = val

                #also update best avg reaction time if needed
                if BEST_REACT_TIME is None or BEST_REACT_TIME > val:
                    BEST_REACT_TIME = val
                    logger.debug(f'New best average reaction time set: {BEST_REACT_TIME}')
            elif 'STARTGAME' in commandName:
                #this means the player has hit the blue start button
                GAME_ON = True

                logger.debug('Started game, blue button clicked.')

                startsound = playsound(startgame_music_path, block=False) #play the starting sound alert
            elif 'ENDGAME' in commandName:
                logger.debug('Endgame triggered. Will reset game.')
                GAME_ON = False #show that game round has ended
            elif 'MOLETURNSTART' in commandName:
                #mole is popping up
                logger.debug('Mole turn started. Mole is here.')

                #update the boolean trackers for turns
                NEW_MOLE = True
            elif 'PLAYERTURNSTART' in commandName:
                #player's turn
                logger.debug('Player should be ready to hit.')
            elif 'HITSUCCESS' in commandName:
                #reports that the player successfully hit the mole
                logger.debug('Player successful hit!')

                HIT_SUCCESS = True #update the success variable
                NEW_MOLE = False #reset the new mole until it new mole is available to be hit

                success_sound = playsound(success_music_path, block = False) #play the successful hit sound effect
            elif 'HITFAIL' in commandName:
                logger.debug('Player failed to hit.')

                HIT_FAIL = True
                NEW_MOLE = False #reset the new mole on hit until new mole is available
                fail_sound = playsound(fail_music_path, block=False)
            elif 'CURRSCORE' in commandName:
                val = int(data.split(' ')[1])
                logger.debug(f'Player current score: {val}')

                CURR_SCORE = val #update the round score
            elif 'CURRTIMEINT' in commandName:
                val = int(data.split(' ')[1])
                logger.debug(f'Player current time int: {val}')

                CURR_MOLE_INT = val #update the time int variables

                #check if update for overall shortest interval is needed
                if SHORTEST_MOLE_INT is None or val < SHORTEST_MOLE_INT:
                    logger.debug(f'Shortest mole interval updated: {val}')
                    SHORTEST_MOLE_INT = val
            elif 'CURRFAILCNT' in commandName:
                val = int(data.split(' ')[1])
                logger.debug(f'Player current fail count: {val}')

                CURR_FAIL_CNT = val #update the fail counter
            elif 'EXCEEDFAIL' in commandName:
                logger.debug('Fail counter hit.')
            elif 'PLAYERTURNEND' in commandName:
                logger.debug('Player turn over.')
            elif 'STARWINK' in commandName:
                logger.debug('wink the star icon.')
                STARWINK = not STARWINK #toggles the icon back and forth

#class for the main app frame
class userDisplay(tk.Tk): #inherit Tk --> full gui window
    def __init__(self):
        super().__init__()
        self.title('Whack an LED!')
        self.geometry('850x600') #set initial size of the display window
        self._cells = {} #dictionary for mapping cells to row/col on grid

        self.dynamicLabelsList = [
            tk.StringVar(value='-'),
            tk.StringVar(value='-'),
            tk.StringVar(value='-'),
            tk.StringVar(value='-'),
            tk.StringVar(value='-'),
        ]

        #vars for current round
        self.current_vars = [
            tk.StringVar(value='-'),    # score
            tk.StringVar(value='-'),    # playtime
            tk.StringVar(value='-'),    # interval
            tk.StringVar(value='- / 3'),  # fails/threshold
            tk.StringVar(value='-'),    # total clicks
            tk.StringVar(value='-'),    # avg react time
        ]

        #create the displayed elements
        self.createUserDisplay()
        self.createUserStats()

        #begin the reader thread
        #thread will run in the background so the serial monitor can be read at any point
        self.reader = ThreadedSerialReader(ser)
        self.reader.start()

        #start playing the background music
        self.backgroundMusic = playsound(background_music_path, block=False)

        self.after(50, self._poll_ui) #polls updates every 50 ms

    def createUserDisplay(self):
        display_frame = tk.Frame(master=self)
        display_frame.pack(fill=tk.X) #place frame object on main window's top border --> ensure frame will fill entire width on resize
        # display_frame['style'] = self.style

        self.titleLabel = tk.Label(
            master=display_frame,
            text = 'Whack an LED!',
            font = font.Font(size=28, weight='bold', family='Courier'),
        ) #title label
        self.titleLabel.pack(pady=(30, 20)) #add to main window

        self.startLabel = tk.Label(
            master=display_frame,
            text = 'Press the blue button to start the game!',
            font = font.Font(size=20, weight='normal', family='Courier'),
        ) #intro label
        self.startLabel.pack() #add to main window

        self.statsStartLabel = tk.Label(
            master=display_frame,
            text = 'Stats Report',
            font = font.Font(size=16, weight='bold', family='Courier'),
        ) #stats title label
        self.statsStartLabel.pack(pady=(50, 20)) #add to main window
    
    def createUserStats(self):
        #global variables
        global FAIL_THRESHOLD, GAME_ON, STAR1

        #create labels for displaying the user's statistics
        title_frame = tk.Frame(master=self)
        title_frame.pack()

        #labels for current round
        self.current_title = tk.Label(
            master=title_frame,
            text='Current Round Stats',
            font=font.Font(size=12, weight='bold', family='Courier'),
            width=30,
        )
        self.current_title.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 5), padx=(0, 10))

        #added a star icon
        self.star_1 = ImageTk.PhotoImage(STAR1)
        self.starIcon = tk.Canvas(
            master=title_frame,
            width=50,
            height=50,
        )
        # Add the background image to the canvas
        self.starIcon.create_image(0, 0, anchor='nw', image=self.star_1)
        self.starIcon.grid(row=0, column=2, columnspan=1, sticky='nw', pady=(0, 5), padx=(20, 0))

        #labels for best scores
        self.current_title1 = tk.Label(
            master=title_frame,
            text='Best Round Stats',
            font=font.Font(size=12, weight='bold', family='Courier'),
            width=30,
        )
        self.current_title1.grid(row=0, column=3, columnspan=2, sticky='e', pady=(0, 5), padx=(20, 0))

        #create labels for displaying the user's statistics
        grid_frame = tk.Frame(master=self)
        grid_frame.pack()

        current_labels = [
            'CURRENT SCORE:',
            'CURRENT PLAYTIME (s):',
            'CURRENT TIME INTERVAL (ms):',
            'CURRENT FAILS:',
            'CURRENT ROUND CLICKS:',
            'AVERAGE REACTION TIME (ms):',
        ]

        for row in range(len(current_labels)):
            self.rowconfigure(row, weight=1, minsize=400)
            self.columnconfigure(row, weight=1, minsize=100)
            statLabelSpace = tk.Label(
                master=grid_frame,
                text=current_labels[row],
                font=font.Font(size=10, family='Courier'),
                fg='black',
                width = 30,
                # height = 2,
                highlightbackground='lightblue',
            )
            self._cells[statLabelSpace] = (row+1, 0)
            statLabelSpace.grid(
                row=row+1,
                column=0,
                padx=5,
                pady=10,
                sticky='nsew',
            )

            #dynamic variables to be updated w/ the actual score counters
            self.current_vars[0].set(CURR_SCORE)
            self.current_vars[1].set(CURR_PLAYTIME)
            self.current_vars[2].set(CURR_MOLE_INT)
            self.current_vars[3].set(f'{CURR_FAIL_CNT} / 3')
            self.current_vars[4].set(CURR_CLICKS)
            self.current_vars[5].set(CURR_REACT_TIME)

            statLabelSpace = tk.Label(
                master=grid_frame,
                textvariable=self.current_vars[row],
                fg='black',
                font=font.Font(size=10, family='Courier'),
                width = 10,
                # height = 2,
                highlightbackground='lightblue',
            )
            self._cells[statLabelSpace] = (row+1, 0)
            statLabelSpace.grid(
                row=row+1,
                column=1,
                padx=5,
                pady=10,
                sticky='nsw',
            )
            logger.debug(f'currlabel row {row}')

        #best scores
        labelslist = [
            'BEST SCORE:',
            'LONGEST PLAYTIME (s):',
            'SHORTEST LED TIME INTERVAL REACHED (ms):',
            'BEST REACTION TIME (ms):',
            'TOTAL CLICKS RECORDED:',
        ]

        for row in range(len(labelslist)):
            logger.debug(f'best scores row {row}')
            self.rowconfigure(row, weight=1, minsize=400)
            self.columnconfigure(row, weight=1, minsize=100)
            statLabelSpace = tk.Label(
                master=grid_frame,
                text=labelslist[row],
                fg='black',
                font=font.Font(size=10, family='Courier'),
                width = 45,
                # height = 2,
                highlightbackground='lightblue',
            )
            self._cells[statLabelSpace] = (row+1, 0)
            statLabelSpace.grid(
                row=row+1,
                column=3,
                padx=5,
                pady=10,
                sticky='nsew',
            )

            #dynamic variables to be updated w/ the actual score counters
                #in order: [best score, longest playtime, shortest led time int, best reaction time, total clicks recorded]
            self.dynamicLabelsList[0].set(BEST_SCORE)
            self.dynamicLabelsList[1].set(LONGEST_PLAYTIME)
            self.dynamicLabelsList[2].set(SHORTEST_MOLE_INT)
            self.dynamicLabelsList[3].set(BEST_REACT_TIME)
            self.dynamicLabelsList[4].set(TOTAL_CLICKS)

            statLabelSpace = tk.Label(
                master=grid_frame,
                textvariable=self.dynamicLabelsList[row],
                fg='black',
                font=font.Font(size=10, family='Courier'),
                width = 3,
                # height = 2,
                highlightbackground='lightblue',
            )
            self._cells[statLabelSpace] = (row+1, 0)
            statLabelSpace.grid(
                row=row+1,
                column=4,
                padx=5,
                pady=10,
                sticky='nsw',
            )

    #executes every 50ms
    #purpose is to poll any changes in the game variables (from the continuously threading background serial monitor updates) and update the ui accordingly
    def _poll_ui(self):
        global CURR_SCORE, CURR_CLICKS, CURR_PLAYTIME, CURR_REACT_TIME, CURR_MOLE_INT, CURR_FAIL_CNT, STAR1, STARWINK

        #check that background music is still playing
        if not self.backgroundMusic.is_alive():
            self.backgroundMusic = playsound(background_music_path, block=False)
            #restart the music
            logger.debug('Restarted the background music.')
        
        #check the star counter status (should wink it every second)
        if STARWINK:
            STAR1 = Image.open(star1_path) #initial icon
            STAR1 = STAR1.resize((50, 50))
            self.star_1 = ImageTk.PhotoImage(STAR1)
            # Add the background image to the canvas
            self.starIcon.create_image(0, 0, anchor='nw', image=self.star_1)
            self.starIcon.grid(row=0, column=2, columnspan=1, sticky='nw', pady=(0, 5), padx=(20, 0))
        else:
            STAR1 = Image.open(star2_path) #winking icon
            STAR1 = STAR1.resize((50, 50))
            self.star_1 = ImageTk.PhotoImage(STAR1)
            # Add the background image to the canvas
            self.starIcon.create_image(0, 0, anchor='nw', image=self.star_1)
            self.starIcon.grid(row=0, column=2, columnspan=1, sticky='nw', pady=(0, 5), padx=(20, 0))

        #read global vals and update ui
        try:
            if GAME_ON:
                logger.debug('Update current game variables.')

                #update current running game vars
                self.current_vars[0].set(str(CURR_SCORE))
                self.current_vars[1].set(str(CURR_PLAYTIME))
                self.current_vars[2].set('-' if CURR_MOLE_INT is None else str(CURR_MOLE_INT))
                self.current_vars[3].set(str(CURR_FAIL_CNT)+' / 3')
                self.current_vars[4].set(str(CURR_CLICKS))
                if CURR_REACT_TIME is None:
                    self.current_vars[5].set('-')
                else:
                    self.current_vars[5].set(f'{CURR_REACT_TIME:.2f}')

                #update the text subtitle label with game status
                self.startLabel.config(text='Wait for it...')
                if NEW_MOLE:
                    self.startLabel.config(text='Quick, hit the LED!')
            else:
                logger.debug('Update best stats variables.')
                #update ending game vars
                self.dynamicLabelsList[0].set(str(BEST_SCORE))
                self.dynamicLabelsList[1].set(str(LONGEST_PLAYTIME))
                self.dynamicLabelsList[2].set('-' if SHORTEST_MOLE_INT is None else str(SHORTEST_MOLE_INT))
                if BEST_REACT_TIME is None:
                    self.dynamicLabelsList[3].set('-')
                else:
                    self.dynamicLabelsList[3].set(f'{BEST_REACT_TIME:.2f}')
                self.dynamicLabelsList[4].set(str(TOTAL_CLICKS))

                #also reset the curr round vars for the next round
                reset_curr_vars = [
                    '-', #score
                    '-', #playtime
                    '-', #interval
                    '- / 3', #fails/threshold
                    '-', #total clicks
                    '-', #avg react time
                ]

                CURR_SCORE = 0
                CURR_CLICKS = 0
                CURR_PLAYTIME = 0
                CURR_REACT_TIME = 0
                CURR_MOLE_INT = 0
                CURR_FAIL_CNT = 0

                for i in range(len(reset_curr_vars)):
                    self.current_vars[i].set(reset_curr_vars[i])
                
                self.startLabel.config(text='Press the blue button to start the game!')

        finally:
            #schedule next poll
            self.after(50, self._poll_ui)
    
def main():
    #create the display and run mainloop
    ui_display = userDisplay()
    ui_display.mainloop()

#setup the main app window
if __name__ == '__main__':
    main()