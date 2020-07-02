# Keylogger
A simple python keylogger built on top of this one: https://www.thepythoncode.com/code/write-a-keylogger-python

## Usage
keylogger_full.py is the full project with microphone recording and screenshoting. keylogger.py only does keylogging and system info gathering. keylogging.py is more lightweight and will send emails faster.

To use them as exes, use pyinstaller and run this command: pyinstaller --onefile --noconsole \<filename> after hardcoding your credentials in place of fromAdrr and fromPswd (the from config import isn't necessary a that point)
