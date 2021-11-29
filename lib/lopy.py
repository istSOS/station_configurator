#!/usr/bin/env python
# Copyright (C) 2021 IST-SUPSI (www.supsi.ch/ist)
# 
# Author: Daniele Strigaro
# 
# This file is part of station_configurator.
# 
# station_configurator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# station_configurator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with station_configurator.  If not, see <http://www.gnu.org/licenses/>.

import time
import serial


def send_data(data):
  try:
      import RPi.GPIO as GPIO
  except Exception as e:
      print(str(e))
      return False
  try:
    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
    ser.flush()
    GPIO.setmode(GPIO.BOARD)
    mode = GPIO.getmode()


    GPIO.setup(7, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(1)
    cnt = 0
    received = ''
    while cnt <= 20:
        GPIO.output(7, GPIO.HIGH)
        if (ser.in_waiting > 0):
            received = ser.readline()
            print(received)
            if received == b'OK\n':
                break
        GPIO.output(7, GPIO.LOW)
        time.sleep(1)
        cnt+=1

    sent = 0
    if received==b'OK\n':
        for row in data:
            cnt = 0
            print('sending {}'.format(row))
            ser.write(
              'SEND {}\n'.format(row).encode()
            )
            while cnt <= 40:
                if (ser.in_waiting > 0):
                  received = ser.readline()
                  print(received)
                  if received==b'SENT\n':
                      print('Data sent')
                      sent+=1
                      break
                time.sleep(1)
                cnt+=1

    ser.write(b'STOP')

    time.sleep(0.1)

    GPIO.setup(7, GPIO.OUT, initial=GPIO.LOW)
    GPIO.cleanup()
    if sent == len(data):
      return True
    else:
      return False
  except Exception as e:
    print(str(e))
    GPIO.cleanup()
    return False
