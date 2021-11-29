#!/usr/bin/python
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

# while
# with serial.Serial("/dev/ttyUSB0") as ser:
#     ser.write(b"Run\r")
#     time.sleep(5)
#     print(ser.read_all())
#     time.sleep(1)
#     ser.write(b"Stop\r")
#     time.sleep(1)
#     print(ser.read_all())

values = []
try:
    with serial.Serial("{}".format('/dev/unilux_chl_10_0')) as ser:
        ser.flush()
        ser.flush()
        ser.flush()
        ser.write(b"Run\r")
        o = 0
        while o < 10:
            c = ser.readline()
            print(c)
            v = c.decode().strip("\r\n")
            print(v)
            try:
                v = float(v)
                values.append(v)
            except:
                continue    
            time.sleep(1)
            o += 1
        ser.write(b"Stop\r")
        time.sleep(1)
        ser.flush()
    if values:
        print(values)
except Exception as e:

    time.sleep(1)
    print(f"No sensor")
    print(str(e))
    raise Exception("Can\'t find sensor")
