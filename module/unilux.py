#!/usr/bin/env python
#
#   Copyright 2021 SUPSI-IST
#
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
            interCharTimeout=1
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
                time.sleep(0.01)
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
            c = self.serial.readline()
            v = c.decode().strip("\r\n")
            try:
                v = float(v)
                values.append(v)
            except:
                continue
            time.sleep(0.25)
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