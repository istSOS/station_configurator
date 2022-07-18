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
import os
from datetime import datetime, timezone
import time
import json
import sys
import statistics

# external lib
import requests
import yaml

# supported devices
from module.ponsel import Ponsel
from module.lufft import WS_UMB
from module.unilux import Unilux
from module.ina219 import read_ina219

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
    try:
        sensor = Ponsel(
            "{}".format(section['port']),
            int(section['addr'])
        )
        sensor.set_run_measurement(0x001f)
        time.sleep(0.25)
        values = sensor.get_values()
        status = sensor.get_status()
    except:
        values = [-999.99, -999.99, -999.99 , -999.99]
        status = [-100, -100, -100, -100]
        print("Can\'t find sensor")
elif sensor_driver == 'unilux':
    try:
        s = Unilux("{}".format(section['port']))
        s.start()
        data = s.get_values()
        print(data)
        filtered_data=[]
        for d in data:
            if d >=0:
                filtered_data.append(d)
        #v = round(statistics.mean(data), 2)
        values = [
            round(statistics.mean(filtered_data), 2)
        ]
        status = [100]
        if data:
            s.stop()
    except:
        values = [-999.99]
        status = [-100]
        if data:
            s.stop()
        print("Can\'t find sensor")
elif sensor_driver == 'lufft':
    values = []
    status = []
    value_UMB = [
        200, 305, 500,
        900, 100, 400, 440
    ]
    try:
        with WS_UMB("{}".format(section['port'])) as umb:
            for v in value_UMB:
                value, st = umb.onlineDataQuery(v, int(section['addr']))
                values.append(
                    round(value, 2)
                )
                status.append(st)
    except:
        values = [-999.99, -999.99, -999.99 , -999.99, -999.99, -999.99, -999.99]
        status = [-100, -100, -100, -100, -100, -100, -100]
    if not values:
        raise Exception('Sensor driver is not supported yet.')
elif sensor_driver == 'ina219':
    values = []
    status = []
    try:
        values = read_ina219()
        status = [100, 100]
    except:
        values = [-999.99, -999.99]
        status = [-100, -100]
        print("Can\'t find sensor")
    if not values:
        raise Exception('Sensor driver is not supported yet.')
else:
    raise Exception('Sensor driver is not supported yet.')

data = None
outputs = []
separator = os.sep
with open(
        os.path.join(
            separator.join(config_file_path.split('/')[0:-1]),
            'support',
            section['driver'],
            f'{sensor_type}.yaml'
        )
    ) as f:
        rs = yaml.safe_load(f)
        outputs = rs['outputs'][1:]
go_values = []
for i in range(len(outputs)):
    go_values.append(round(values[i], 2))
    if data:
        data = data + ',' + str(round(values[i], 2))
    else:
        data = str(round(values[i], 2))

bp = datetime.now(timezone.utc).replace(second=0, microsecond=0).isoformat()

data_post = '{};{},{}'.format(
    section['assigned_id'],
    bp,
    data
)
print(data_post)

#### Using InsertObservation #####
go = requests.get(
    (
        "{}/wa/istsos/services/{}/operations/getobservation"
        "/offerings/temporary/procedures/{}/observedproperties/:/eventtime/last"
    ).format(
        config['DEFAULT']['istsos'],
        config['DEFAULT']['service'],
        section_name
    ),
    auth=(
        config['DEFAULT']['user'],
        config['DEFAULT']['password']
    )
)

go = go.json()
go = go['data'][0]

go["samplingTime"] = {
    "beginPosition": bp,
    "endPosition":  bp
}
go['result']['DataArray']['values'] = [
    [bp] + go_values
]

go['result']['DataArray']['elementCount'] = str(len(outputs)+1)
go['result']['DataArray']['field'] = list(
    filter(
        lambda x: 'qualityIndex' not in x['definition'], go['result']['DataArray']['field']
    )
)

res = requests.post(
    "%s/wa/istsos/services/%s/operations/"
    "insertobservation" % (
        config['DEFAULT']['istsos'],
        config['DEFAULT']['service'],
    ),
    auth=(
        config['DEFAULT']['user'], config['DEFAULT']['password']
    ),
    data=json.dumps({
        "ForceInsert": "true",
        "AssignedSensorId": section['assigned_id'],
        "Observation": go
    })
)
res.raise_for_status()
print(" > Insert observation success: %s" % (
    res.json()['success']))

# req = requests.post(
#     '{}/wa/istsos/services/{}/operations/fastinsert'.format(
#         config['DEFAULT']['istsos'],
#         config['DEFAULT']['service'],
#     ),
#     data=data_post,
#     auth=(config['DEFAULT']['user'], config['DEFAULT']['password'])
# )

# if req.status_code == 200:
#     print(req.text)
# else:
#     print(False)

try:
    if usb_log:
        mode = 'w'
        file_name = 'LOG.txt'
        for item in os.listdir('/media/usb0'):
            if item == file_name:
                mode = 'a'
        # try some standard file operations
        with open('/media/usb0/LOG.txt', mode) as f:
            f.write(section_name + "," + data_post + "\n")
            f.close()
except Exception as e:
    print(str(e))


