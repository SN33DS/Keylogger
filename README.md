# Keylogger
A simple python keylogger built on top of this one: https://www.thepythoncode.com/code/write-a-keylogger-python

## Explanation
keylogger_full.py is the full project with microphone recording and screenshoting. keylogger.py only does keylogging and system info gathering. keylogging.py is more lightweight and will send emails faster.

Both have persistence on windows machines.

Be aware that the microphone access doesn't seem to be supported by pyinstaller so you will nedd to remove that from the code in order to package it.
