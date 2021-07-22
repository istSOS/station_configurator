#!/usr/bin/python

import configparser
import os
from datetime import datetime, timezone
import time
import sys

# external lib
import requests
import yaml

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

# read config file
config = configparser.ConfigParser()
config.read(config_file_path)

usb_log = config['DEFAULT']['usb_log']
# read variables for sensor/section
section = config[section_name]

# set variables
sensor_type = section['type']
sensor_driver = section['driver']

# initialize and read data from sensor
if sensor_driver == 'ponsel':
    sensor = Ponsel(
        section['port'],
        int(section['addr'])
    )
    sensor.set_run_measurement(0x001f)
    time.sleep(1)
    values = sensor.get_values()
    status = sensor.get_status()
else:
    raise 'Sensor driver is not supported yet.'

data = None
outputs = []
with open(
        os.path.join(
            ___dir___,
            'support',
            section['driver'],
            f'{sensor_type}.yaml'
        )
    ) as f:
        rs = yaml.safe_load(f)
        outputs = rs['outputs'][1:]

for i in range(len(outputs)):
    if data:
        data = data + ',' + str(round(values[i], 100))
    else:
        data = str(round(values[i], 100))

data_post = '{};{},{}'.format(
    section['assigned_id'],
    datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat(),
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

try:
    if usb_log:
        mode = 'w'
        file_name = 'LOG.txt'
        for item in os.listdir('/media/usb'):
            if item == file_name:
                mode = 'a'
        # try some standard file operations
        with open('/media/usb/LOG.txt', mode) as f:
            f.write(section_name + "," + data_post + "\n")
            f.close()
except Exception as e:
    print(str(e))


