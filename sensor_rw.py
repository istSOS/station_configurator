#!/usr/bin/python

import configparser
import os
from datetime import datetime, timezone
import time
import sys

# external lib
import requests

# supported devices
from module.ponsel import Ponsel

___dir___ = os.path.abspath(os.getcwd())

num = len(sys.argv)
if num > 1:
    for i in range(1, num):
        if sys.argv[i] == "-h" or sys.argv[i] == "?":  # debug mode
            print('-s = sensor/section name')
            quit()
        if sys.argv[i] == "-s":  # debug mode
            section_name = sys.argv[i+1]
        if sys.argv[i] == "-c":  # debug mode
            config_file_path = sys.argv[i+1]


config = configparser.ConfigParser()
config.read(config_file_path)
section = config[section_name]
sensor = Ponsel(
    section['port'],
    int(section['addr'])
)
sensor.set_run_measurement(0x001f)
time.sleep(1)
values = sensor.get_values()
status = sensor.get_status()

data = None

for i in range(len(status)):
    if status[i] != 0:
        if data:
            data = data + ',' + str(round(values[i], 1))
        else:
            data = str(round(values[i], 1))

data_post = '{};{},{}'.format(
    section['assigned_id'],
    datetime.now(timezone.utc).isoformat(),
    data
)
print(data_post)

req = requests.post(
    '{}/wa/istsos/services/{}/operations/fastinsert'.format(
        config['DEFAULT']['istsos'],
        config['DEFAULT']['service'],
    ),
    data=data_post,
    auth=(config['DEFAULT']['user'], config['DEFAULT']['password'])
)

if req.status_code == 200:
    print(req.text)
else:
    print(False)
