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


import configparser
import sys
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
import json
import os
import time
from lib.battery import read_ina219
from lib.lopy import send_data

# external lib
import requests
import yaml
import paho.mqtt.client as mqtt

run = True


num = len(sys.argv)
if num > 1:
    for i in range(1, num):
        if sys.argv[i] == "-h" or sys.argv[i] == "?":  # debug mode
            print('-c = config file path')
        if sys.argv[i] == "-c":  # debug mode
            config_file_path = sys.argv[i+1]


config = configparser.ConfigParser()
config.read(config_file_path)
base_path = f'{os.sep}'.join(
    config_file_path.split(os.sep)[:-1]
)

istsos_url = config['DEFAULT']['istsos']
service = config['DEFAULT']['service']
mode = int(config['DEFAULT']['mode'])
usb_log = int(config['DEFAULT']['usb_log'])

# MQTT
mqtt_broker = config['DEFAULT']['mqtt_address']
mqtt_port = int(config['DEFAULT']['mqtt_port'])
mqtt_user = config['DEFAULT']['mqtt_user']
mqtt_pwd = config['DEFAULT']['mqtt_pwd']
mqtt_client_id = config['DEFAULT']['mqtt_client_id']
mqtt_base_topic = config['DEFAULT']['mqtt_base_topic']

# WiFi
remote_istsos_url = config['DEFAULT']['istsos']
remote_service = config['DEFAULT']['service']
remote_user = config['DEFAULT']['user']
remote_passwrod = config['DEFAULT']['password']


now = datetime.now(timezone.utc)
end_position = datetime(
    now.year, now.month, now.day,
    now.hour, now.minute, tzinfo=timezone.utc
)
begin_position = end_position - timedelta(
    days=int(config['DEFAULT']['max_log_days'])
)

data_sent = False
event_time = f'{begin_position.isoformat()}/{end_position.isoformat()}'

v_batt = read_ina219()

data_to_send = []

for section in config.sections():
    run = True
    sec = config[section]
    if 'aggregation_time' in sec.keys():
        url_get_data = (
            f'{istsos_url}/{service}agg?request=GetObservation&'
            f'offering=temporary&procedure={section}&'
            f'observedProperty=:&'
            'qualityIndex=False&responseFormat=text/plain'
            '&service=SOS&version=1.0.0'
            # '&qualityFilter=<=211'
        )
        req = requests.get(
            url_get_data,
            auth=(
                config['DEFAULT']['user'],
                config['DEFAULT']['password']
            ),
            verify=False
        )
        if req.status_code == 200:
            data_text = req.text
            data_text_splitted = data_text.split('\n')
            if len(data_text_splitted) == 2:
                data_splitted = data_text_splitted[1].split(',')
                #t = data_text_splitted[1].split(',')[0][5:16]
                values_str = data_splitted[2:]
                #print(values_str[0])
                dt = datetime.fromisoformat(data_text_splitted[1].split(',')[0])
                t = str(int(dt.timestamp()))
                # values = list(
                #     map(lambda x: str(round(float(x),2)), values_str)
                # )
                values = []
                for x in values_str:
                    try:
                        values.append(str(round(float(x),2)))
                    except:
                        values.append(x)
                
                values.append(str(v_batt))
                # print(section + ',' + t + "," + ','.join(values))
                body = section + ',' + t + "," + ','.join(values)
                data_to_send.append(body)
                try:
                    if usb_log:
                        mode = 'w'
                        file_name = 'LOG.txt'
                        for item in os.listdir('/media/usb'):
                            if item == file_name:
                                mode = 'a'
                        # try some standard file operations
                        with open('/media/usb/LOG.txt', mode) as f:
                            f.write(body + "\n")
                            f.close()
                except:
                    continue

        else:
            raise Exception('ERROR in loading file')
    else:
        print('Cannot send not aggregated data')
print('SENDING DATA')
send_data(data_to_send)
