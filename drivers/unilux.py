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


import serial
import time


class Unilux():

    def __init__(self, device, baudrate=9600):
        self.device = device
        self.baudrate = baudrate
        self.serial = serial.Serial(
            self.device,
            baudrate=self.baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            #interCharTimeout=1,
            timeout=2.0,
            write_timeout=2.0
        )
    
    def read(self, timeout=1):
        timeout_count = 0
        data = b''
        while True:
            if self.serial.inWaiting() > 0:
                new_data = self.serial.read(1)
                data = data + new_data
                timeout_count = 0
            else:
                timeout_count += 1
                if timeout is not None and timeout_count >= 10 * timeout:
                    break
                time.sleep(0.2)
        return data
    
    def write(self, cmd, timeout=1):
        self.serial.flush()
        cmd = "{}\r".format(cmd)
        self.serial.write(
            cmd.encode()
        )
    
    def get_values(self):
        values = []
        o = 0
        while len(values)<5:
            if o > 10:
                break
            c = self.serial.readline()
            v = c.decode().strip("\r\n")
            try:
                v = float(v)
                values.append(v)
            except:
                values.append(-999.99)
                continue
            time.sleep(0.2)
            o += 1
        return values
    
    def start(self):
        self.write("Run")

    def stop(self):
        self.write("Stop")

# values = []
# try:
#     with serial.Serial("{}".format('/dev/unilux_chl_10_0')) as ser:
#         ser.flush()
#         ser.flush()
#         ser.flush()
#         ser.write(b"Run\r")
#         o = 0
#         while o < 10:
#             c = ser.readline()
#             print(c)
#             v = c.decode().strip("\r\n")
#             print(v)
#             try:
#                 v = float(v)
#                 values.append(v)
#             except:
#                 continue    
#             time.sleep(1)
#             o += 1
#         ser.write(b"Stop\r")
#         time.sleep(1)
#         ser.flush()
#     if values:
#         print(values)
# except Exception as e:

#     time.sleep(1)
#     print(f"No sensor")
#     print(str(e))
#     raise Exception("Can\'t find sensor")
