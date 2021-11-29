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

from ina219 import INA219, DeviceRangeError
from time import sleep


def to_255(v):
  if v <= 10.5:
    return 1
  elif v <= 11.31:
    return 25
  elif v <= 11.58:
    return 51
  elif v <= 11.75:
    return 77
  elif v <= 11.9:
    return 102
  elif v <= 12.06:
    return 128
  elif v <= 12.2:
    return 153
  elif v <= 12.32:
    return 179
  elif v <= 12.42:
    return 204
  elif v <= 12.5:
    return 230
  elif v <= 12.7:
    return 242
  else:
    return 254

def read_ina219():
    try:
        SHUNT_OHMS = 0.1
        MAX_EXPECTED_AMPS = 2.0
        ADDRESS=0x40
        #ina = INA219(
        #  shunt_ohms=SHUNT_OHMS,
        #  address=ADDRESS
        #)
        #ina.configure(ina.RANGE_16V)
        ina = INA219(
            SHUNT_OHMS, 1.6, address=ADDRESS
        )
        ina.configure(ina.RANGE_32V, ina.GAIN_8_320MV)
        # ina.configure()
        print('Bus Voltage: {0:0.2f}V'.format(ina.voltage()))
        print('Bus Current: {0:0.2f}mA'.format(ina.current()))
        print('Power: {0:0.2f}mW'.format(ina.power()))
        print('Shunt Voltage: {0:0.2f}mV\n'.format(ina.shunt_voltage()))
        return to_255(ina.voltage())
    except DeviceRangeError as e:
        # Current out of device range with specified shunt resister
        print("DeviceRangeError")
        return 254
    except:
        print("Errors found or no INA219 detected")
        return 254
