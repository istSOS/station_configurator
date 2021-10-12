#!/usr/bin/python

import configparser
import os
from datetime import datetime, timezone
import time
import json
import sys

# external lib
import requests
import yaml

# supported devices
from module.ponsel import Ponsel
from module.lufft import WS_UMB

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
start = time.time()
while True:
    end = time.time()
    try:
        if sensor_driver == 'ponsel':
            i = 0
            while i<5:
                try:
                    sensor = Ponsel(
                        "{}{}".format(section['port'], i),
                        int(section['addr'])
                    )
                    sensor.set_run_measurement(0x001f)
                    time.sleep(1)
                    values = sensor.get_values()
                    status = sensor.get_status()
                    break
                except:
                    time.sleep(1)
                    i+=1
                    if i==5:
                        raise Exception("Can\'t find sensor")
            break
        elif sensor_driver == 'lufft':
            values = []
            status = []
            value_UMB = [
                200, 305, 500,
                900, 100, 400, 440
            ]
            i = 0
            while i<5:
                try:
                    with WS_UMB("{}{}".format(section['port'], i)) as umb:
                        for v in value_UMB:
                            value, st = umb.onlineDataQuery(v, int(section['addr']))
                            values.append(
                                round(value, 2)
                            )
                            status.append(st)
                    if values:
                        break
                except:
                    time.sleep(1)
                    i+=1
                    if i==5:
                        raise Exception("Can\'t find sensor")
            if not values:
                raise Exception('Sensor driver is not supported yet.')
            else:
                break
        else:
            raise Exception('Sensor driver is not supported yet.')
    except Exception as e:
        if (end-start) > 30:
            raise e
        else:
            time.sleep(1.5)
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
        for item in os.listdir('/media/usb'):
            if item == file_name:
                mode = 'a'
        # try some standard file operations
        with open('/media/usb/LOG.txt', mode) as f:
            f.write(section_name + "," + data_post + "\n")
            f.close()
except Exception as e:
    print(str(e))


