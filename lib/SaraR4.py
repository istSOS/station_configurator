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

__PLATFORM__=''
from os import wait
import os
import requests
import logzero
import time
import sys
import serial
from datetime import datetime, timezone
try:
    import Jetson.GPIO as GPIO
    __PLATFORM__='Jetson'
except Exception as e:
    print(str(e))
    try:
        import RPi.GPIO as GPIO
        __PLATFORM__='RPi'
    except Exception as e2:
        print(str(e2))

logging = logzero.logger

# SLEEP vars
TIMEOUT = 1.5
LTE_SHIELD_POWER_PULSE_PERIOD=3.2
LTE_RESET_PULSE_PERIOD=10

# PIN CONFIGURATION
PWR_PIN=7
RST_PIN=13
RTS_PIN=11
CTS_PIN=36

base_path = os.path.abspath(os.getcwd())

datetime_str = datetime.now(timezone.utc).isoformat()

i=0
success = False

def power_off():
    # init GPIO
    GPIO.setmode(GPIO.BOARD)
    mode = GPIO.getmode()
    GPIO.setup(PWR_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(PWR_PIN, GPIO.LOW)

def reset_v1():
    # init GPIO
    power_off()
    time.sleep(LTE_SHIELD_POWER_PULSE_PERIOD)
    power_on()

def reset():
    GPIO.setmode(GPIO.BOARD)
    mode = GPIO.getmode()
    GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(LTE_RESET_PULSE_PERIOD)
    GPIO.output(RST_PIN, GPIO.HIGH)
    GPIO.setup(RST_PIN, GPIO.IN)

def power_on():
    # init GPIO
    GPIO.setmode(GPIO.BOARD)
    mode = GPIO.getmode()
    GPIO.setup(PWR_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(RTS_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.output(PWR_PIN, GPIO.LOW)
    time.sleep(LTE_SHIELD_POWER_PULSE_PERIOD)
    GPIO.output(PWR_PIN, GPIO.HIGH)
    time.sleep(LTE_SHIELD_POWER_PULSE_PERIOD)

class SaraR4Module:

    DEBUG=False
    USB_SERIAL=True

    # SLEEP vars
    TIMEOUT = 1.5
    LTE_SHIELD_POWER_PULSE_PERIOD=3.2
    LTE_RESET_PULSE_PERIOD=30

    # PIN CONFIGURATION
    PWR_PIN=7
    RST_PIN=13
    RTS_PIN=11

    # SERIAL
    BAUDRATE=115200
    RTSCTS=1

    # GENERAL
    TIMEOUT = 1.5

    def __init__(self, serial_path=None, DEBUG=False, USB_SERIAL=False, BAUDRATE=9600):
        self.BAUDRATE = BAUDRATE
        self.DEBUG = DEBUG
        self.USB_SERIAL = USB_SERIAL
        self.ser = None
        self.serial_path = serial_path
        if not serial_path:
            if self.USB_SERIAL:
                serial_success = self.init_usb_serial()
                if serial_success < 0:
                    logging.info("Trying powering the device...")
                    power_on()
                    serial_success = self.init_usb_serial()
                if serial_success < 0:
                    logging.info("Trying resetting the device...")
                    reset()
                    serial_success = self.init_usb_serial()
                if serial_success < 0:
                    raise Exception("Device not found")
                init_success = self.at_command("AT")
                if init_success:
                    logging.info("Init success")
                else:
                    logging.error("No device found")
                    raise Exception("No device found")
            else:
                serial_success = self.init_serial()
                if serial_success < 0:
                    serial_success = self.init_serial(power=True)
                if serial_success < 0:
                    serial_success = self.init_serial(reset=True)
                if serial_success < 0:
                    raise Exception("Device not found")
                init_success = self.at_command("AT")
                if init_success:
                    logging.info("Init success")
                else:
                    logging.error("No device found")
                    raise Exception("No device found")
        else:
            power_on()
            timeout = 0
            start = time.time()
            resetted = False
            while True:
                try:
                    self.ser = serial.Serial(
                        self.serial_path,
                        baudrate=self.BAUDRATE,
                        timeout=5,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS
                    )
                    if self.at_command("AT", timeout=1):
                        break
                    self.ser.close()
                    time.sleep(1)
                    end = time.time()
                    timeout = end-start
                    if timeout>15:
                        power_off()
                        raise Exception('Sara R4 module not found')
                except:
                    if not resetted:
                        
                        logging.info("reset")
                        start = time.time()
                        resetted = True
                        reset()
                        power_on()
                        time.sleep(3)
                    else:
                        time.sleep(1)
                        end = time.time()
                        timeout = end-start
                        if timeout>15:
                            power_off()
                            raise Exception('Sara R4 module not found')

    def check_serial(self):
        timeout = 0
        start = time.time()
        while True:
            try:
                self.ser = serial.Serial(
                    self.serial_path,
                    baudrate=self.BAUDRATE,
                    timeout=5,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                if self.at_command("AT", timeout=1):
                    break
            except:
                time.sleep(1)
                end = time.time()
                timeout = end-start
                if timeout>15:
                    raise Exception('Sara R4 module not found')

    def get_datetime(self):
        # GET DATETIME
        self.at_command("AT+CTZU=1")
        t = self.at_command('AT+CCLK?', capture_output=True)
        return t

    def flush(self):
        time.sleep(self.TIMEOUT)
        self.ser.flushInput()
        time.sleep(self.TIMEOUT)
        self.ser.flushOutput()
        time.sleep(self.TIMEOUT)
    def enable_cellular_verbosity(self):
        return self.at_command("AT+CMEE=2")
    
    def set_provider_name(self, provider_name):
        return self.at_command('AT+CGDCONT=1,"IP","{}"'.format(provider_name))

    def init_serial(self, power=False, reset= False):
        if power:
            power_on()
            time.sleep(self.LTE_SHIELD_POWER_PULSE_PERIOD)

        if reset:
            reset()
            time.sleep(self.LTE_SHIELD_POWER_PULSE_PERIOD)

        i = 0
        success = -1
        if __PLATFORM__=='RPi':
            serial_code = 'serial'
        elif __PLATFORM__=='Jetson':
            serial_code = 'ttyTHS'
        else:
            serial_code = 'ttyUSB'
        while i<5:
            try:
                ser =serial.Serial(
                    f"/dev/tty{serial_code}{i}",
                    baudrate=self.BAUDRATE,
                    timeout=5,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                self.ser = ser
                if self.at_command("AT", timeout=3):
                    logging.info(f"Device found at /dev/ttyTHS{i}")
                    success = i
                    self.serial_path = f"/dev/ttyTHS{i}",
                    break
                else:
                    self.ser = None
                    raise Exception("No AT response")
            except Exception as e:
                logging.error(str(e))
                logging.error(f"No device found at /dev/ttyTHS{i}")
                i+=1
                continue
        return success
    
    def init_usb_serial(self, power=False, reset= False):
        if power:
            power_on()
            time.sleep(self.LTE_SHIELD_POWER_PULSE_PERIOD)

        if reset:
            reset()
            time.sleep(self.LTE_SHIELD_POWER_PULSE_PERIOD)

        i = 0
        success = -1
        while i<5:
            try:
                self.ser = serial.Serial(
                    f"/dev/ttyUSB{i}",
                    baudrate=self.BAUDRATE,
                    timeout=5,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS
                )
                if self.at_command("AT", timeout=5):
                    logging.info(f"Device found at /dev/ttyUSB{i}")
                    self.serial_path = f"/dev/ttyUSB{i}",
                    success = i
                    break
                try:
                    self.ser.close()
                    self.ser = None
                except:
                    self.ser = None

                logging.error(f"No device found at /dev/ttyUSB{i}")
                i+=1
                time.sleep(2)
            except Exception as e:
                self.ser = None
                logging.error(str(e))
                logging.error(f"No device found at /dev/ttyUSB{i}")
                i+=1
                continue
        return success

    def init(self):
        self.at_command("ATE0")
        self.at_command("AT+CFUN=1")
        self.at_command("AT+CMEE=2")
        # get module manufacturer
        self.at_command("AT+CGMI")
        # get module module
        self.at_command("AT+CGMM")
        # get last fimware update
        self.at_command("AT+CGMR")
        # get fimrware version
        self.at_command("ATI9")
        # boh
        self.at_command('AT+CLCK="SC",2')
        # check SIM card
        self.at_command("AT+CPIN?")
        # get date time
        self.at_command("AT+CCLK?")
        # get imei
        self.at_command("AT+CGSN")
        #
        self.at_command("AT+COPS?")
        #
        if self.registered():
            self.at_command("AT+CEREG=2")
            #
            self.at_command("AT+CEREG=0")
            #
            self.at_command("AT+CSQ")
            #
            self.at_command("AT+UPSV?")
            return True
        else:
            return False
    
    def registered(self):
        #
        output = self.at_command(
            "AT+CEREG?",
            capture_output=True,
            timeout=180
        )
        if not output:
            return False
        else:
            for i in output:
                i_splitted = i.decode().split(',')
                if len(i_splitted) >= 2:
                    if i_splitted[1][0] == '1':
                        return True
            return False        

    def auto_connect(self):
        r = self.register_module()
        if r:
            ops = self.get_operators(capture_output=True)
            if ops:
                self.at_command("AT+CEREG=2")
                self.at_command("AT+CEREG?")
                self.at_command("AT+CEREG=0")
                return True
            else:
                return False
        else:
            return False

    def set_bands(self):
        success = self.at_command(
            "AT+UBANDMASK=0,524420"
        )
        if success:
            return self.at_command(
                "AT+UBANDMASK=1,524420"
            )
        return success
        


    def get_operators(self, capture_output=False):
        output = self.at_command(
            "AT+COPS=?",
            capture_output=capture_output,
            timeout=180
        )
        if not output:
            return []
        else:
            operators = []
            for elem in output:
                elem = elem.decode()
                elem_splitted = elem.strip(
                    '\r\n'
                    ).strip(
                        '+COPS: '
                    ).strip(
                        'OK'
                    ).split(
                        '('
                    )
                logging.warning(elem_splitted)
                for n in elem_splitted:
                    op = n.strip('),').split(',')
                    op_tmp = []
                    for o in op:
                        if o:
                            op_tmp.append(o)
                    if op_tmp:
                        operators.append(op_tmp)
            return operators

    def network_attached(self):
         return self.at_command("AT+CGATT?")

    def network_registered(self):
        return self.at_command("AT+CEREG?")

    def register_module(self, timeout=180):
        return self.at_command("AT+COPS=0", timeout=timeout)
            
    def at_command(self, cmd, wait_until=b"OK", capture_output=False, timeout=30):
        if self.DEBUG:
            logging.info(f"Command --> {cmd}")
        c = '{}\r\n'.format(cmd)
        # self.flush()
        self.ser.write(c.encode())
        time.sleep(0.02)
        tmp_str = ''
        lines = []
        TIMEOUT = timeout
        start = time.time()
        while True:
            try:
                time.sleep(0.01)
                lines.append(self.ser.readline())
                tmp_str = lines[-1]
                time.sleep(0.02)
                if self.DEBUG:
                    logging.info(tmp_str)
                if wait_until in tmp_str:
                    if capture_output:
                        return lines
                    else:
                        return True
                if b'ERROR' in tmp_str:
                    break
                end = time.time()
                if end - start >= TIMEOUT:
                    if self.DEBUG:
                        logging.error('Error')
                    break
            except:
                end = time.time()
                if end - start >= TIMEOUT:
                    if self.DEBUG:
                        logging.error('Error')
                    break
        return False

    def set_umnoprof(self, code):
        success = self.at_command(f"AT+UMNOPROF={code}")
        if success:
            self.soft_reset()
            self.check_serial()
        return success
    
    def set_radio_mode(self, radio_mode):
        success = self.at_command(f"AT+URAT?", capture_output=True)
        if len(success)>0:
            for out in success:
                check_string = '+URAT: {}'.format(radio_mode)
                if check_string.encode() in out:
                    return True
        success = self.at_command(f"AT+URAT={radio_mode}")
        if success:
            self.soft_reset()
            self.check_serial()
        # success = self.at_command("AT+URAT?")
        return success

    def set_operator(self, operator_id, TIMEOUT=30):
        time.sleep(0.2)
        return self.at_command(
            'AT+COPS=1,2,"{}"'.format(
                operator_id
            ),
            timeout=TIMEOUT
        )

    def set_mqtt_user_password(self, user, pwd):
        self.flush()
        time.sleep(0.2)
        return self.at_command('AT+UMQTT=4,"{}","{}"'.format(
            user,
            pwd
        ))
    
    def set_mqtt_server_port(self, server, port):
        self.flush()
        time.sleep(0.2)
        return self.at_command('AT+UMQTT=2,"{}",{}'.format(
            server,
            port
        ))
    
    def set_mqtt_clean_session(self, mode):
        self.flush()
        time.sleep(0.2)
        return self.at_command(f"AT+UMQTT=12,{mode}")

    def set_mqtt(self, server, port, user=None, password=None):
        if user and password:
            if not self.set_mqtt_user_password(
                user,
                password
            ):
                logging.error="Can't set user and password"
                raise Exception("Can't set user and password")
        return self.set_mqtt_server_port(server, port)
    
    def mqtt_login(self, TIMEOUT=30):
        # MQTT logout
        self.flush()
        #self.at_command(
        #    'AT+UMQTTC=0',
        #    wait_until=b'+UMQTTC: 0,1'
        #)
        # MQTT Login
        self.flush()
        return self.at_command(
            'AT+UMQTTC=1',
            wait_until=b'+UMQTTC: 1,1',
            timeout=TIMEOUT
        )
    def mqtt_logout(self, TIMEOUT=30):
        self.flush()
        # MQTT logout
        return self.at_command(
            'AT+UMQTTC=0',
            wait_until=b'+UMQTTC: 0,1',
            timeout=TIMEOUT
        )

    def mqtt_publish(self, topic, data):
        self.flush()
        return self.at_command(
            'AT+UMQTTC=2,2,1,0,"{}","{}"'.format(
            topic,
            data
        ), wait_until=b"+UMQTTC: 2,1")

    def soft_reset(self):
        self.flush()
        a = self.at_command("AT+CFUN=15")
        time.sleep(30)
        # self.__init__(
        #     '' if "USB" in self.serial_path else self.serial_path,
        #     self.DEBUG,
        #     self.USB_SERIAL
        # )
        return a

    def connect(self, operator, radio_mode=7, umnoprof=100):
        if self.set_radio_mode(radio_mode):
            logging.info('RADIO SET')
        else:
            E01 = "Error setting radio mode"
            if not self.set_umnoprof(umnoprof):
                logging.error(E01)
                raise Exception(E01)

        # operators = sara_module.get_operators(capture_output=True)
        # logging.info(operators)
        if self.set_operator(operator):
            logging.info('OPERATOR CORRECTLY SET')
        else:
            E03 = "Error setting the operator"
            logging.error(E03)
            raise Exception(E03)

    def set_mqtt_ssl(self, ssl):
        self.flush()
        time.sleep(0.2)
        return self.at_command(f"AT+UMQTT=11,{ssl}")

    def set_mqtt_params(self, mqtt_server, mqtt_port, mqtt_user, mqtt_password, mqtt_ssl=0):
        if self.set_mqtt_clean_session(1):
            logging.info('MQTT clean session SET correctly')
        else:
            if self.mqtt_logout():
                if self.set_mqtt_clean_session(1):
                    logging.info('MQTT clean session SET correctly')
                else:    
                    E04 = "Error setting MQTT clean session"
                    logging.error(E04)
                    raise Exception(E04)
            else:
                if reset():
                    if self.set_mqtt_clean_session(1):
                        logging.info('MQTT clean session SET correctly')
                    else:
                        E04 = "Error setting MQTT clean session"
                        logging.error(E04)
                        raise Exception(E04)

                else:
                    E04 = "Error setting MQTT clean session"
                    logging.error(E04)
                    raise Exception(E04)
        if self.set_mqtt(
            mqtt_server, mqtt_port,
            mqtt_user, mqtt_password):
            logging.info('MQTT params set')
        else:
            E05 = "Error setting MQTT params"
            logging.error(E05)
            raise Exception(E05)
        
    def set_login(self):
        retry = 0
        while True:
            if self.login():
                logging.info('Logged')
                break
            else:
                E06 = "Error during login retry #{}".format(
                    retry+1
                )
                logging.error(E06)
            if retry==2:
                E06 = "Error during login retry #{}".format(
                    retry+1
                )
                logging.error(E06)
                raise Exception(E06)
            retry+=1
