#!/usr/bin/python

import configparser
import sys
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
import json
import os
import time

# external lib
import requests
import yaml
import paho.mqtt.client as mqtt


force_insert = {
  "AssignedSensorId": None,
  "ForceInsert": "true",
  "Observation": {
    "name": "sensor1",
    "samplingTime": {
      "beginPosition": None,
      "endPosition": None,
      "duration": "P1DT1H57M"
    },
    "procedure": None,
    "observedProperty": {
      "CompositePhenomenon": {
        "id": "comp_1",
        "dimension": "9",
        "name": "timeSeriesOfObservations"
      },
      "component": None
    },
    "featureOfInterest": {
      "name": None,
      "geom": ""
    },
    "result": {
      "DataArray": {
        "elementCount": "0",
        "field": None,
        "values": [
          None
        ]
      }
    }
  }
}

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
transmission = config['DEFAULT']['transmission']

if transmission == 'fastinsert':
    # WiFi
    remote_istsos_url = config['DEFAULT']['istsos']
    remote_service = config['DEFAULT']['service']
    remote_user = config['DEFAULT']['user']
    password = config['DEFAULT']['password']
elif transmission == 'mqtt':
    # MQTT
    mqtt_broker = config['DEFAULT']['mqtt_address']
    mqtt_port = int(config['DEFAULT']['mqtt_port'])
    mqtt_user = config['DEFAULT']['mqtt_user']
    mqtt_pwd = config['DEFAULT']['mqtt_pwd']
    mqtt_client_id = config['DEFAULT']['mqtt_client_id']
    mqtt_base_topic = config['DEFAULT']['mqtt_base_topic']
else:
    raise "the selected transmission is not supported yet"

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


for section in config.sections():
    print(section)
    run = True
    sec = config[section]
    sec_type = sec['type']
    driver = sec['driver']
    if 'aggregation_time' in sec.keys():
        url_get_data = (
            f'{istsos_url}/{service}agg?request=GetObservation&'
            f'offering=temporary&procedure={section}&'
            f'eventtime={event_time}&observedProperty=:&'
            'qualityIndex=True&responseFormat=text/plain'
            '&service=SOS&version=1.0.0'
            '&qualityFilter=<=209'
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
            if transmission == 'mqtt': 
                data_text = req.text
                data = data_text.replace(f",{section},", ',')
                
                def on_connect(client, userdata, flags, rc):
                    global run
                    if rc==0:
                        # print("Connected with result code "+str(rc))
                        # print("Sending...")
                        ret = client.publish(
                            f"{mqtt_base_topic}/{section}",
                            data,
                            qos=1,
                            retain=True
                        )
                        if ret[0]==0:
                            data_sent = True
                            print(f"0,{mqtt_base_topic}/{section}")
                        else:
                            print(f"1,{section}")
                        if data_sent:
                            csv_read = csv.reader(
                                StringIO(data_text), delimiter=','
                            )
                            header = None
                            # update_val = []
                            for row in csv_read:
                                # print(header)
                                # print(row)
                                assigned_id = sec['assignedagg_id']
                                foi = sec['foi']
                                
                                # data = f'{assigned_id};{row[0]}'
                                update_val = []
                                if 'time' in row[0]:
                                    header = row
                                else:
                                    data_datetime = row[0]
                                    for i in range(len(header)):
                                        if i > 1:
                                            # print(header[i])
                                            if 'qualityIndex' in header[i]:
                                                # data = data + f':{row[i]}'
                                                if str(row[i]) == '-100':
                                                    update_val.append(int(f'-110'))
                                                else:
                                                    qi_sent = row[i][:1] + '1' + row[i][-1:]
                                                    update_val.append(int(qi_sent))
                                            else:
                                                # data = data + f',{round(float(row[i]), 2)}'
                                                update_val.append(round(float(row[i]), 2))
                                    # print(update_val)
                            # update_val = []
                            # # if data sent change quality index
                                fields = []
                                with open(
                                    os.path.join(
                                        f'{base_path}',
                                        'support',
                                        'ponsel',
                                        f'{sec_type}.yaml'
                                    )
                                ) as f:
                                    
                                    rs = yaml.safe_load(f)
                                    fields_tmp = rs['outputs']
                                    for field in fields_tmp:
                                        fields.append(field)
                                        field_name = field['name']
                                        if 'time' not in field_name.lower():
                                            field_definition = field['definition']
                                            field_qi = {
                                                "name": f'{field_name}:qualityIndex',
                                                "definition": f'{field_definition}:qualityIndex',
                                                "uom": "-"
                                            }
                                            fields.append(field_qi)
                                # print(fields)

                                force_insert['AssignedSensorId'] = assigned_id
                                force_insert[
                                    'Observation'
                                ][
                                    'samplingTime'
                                ]['beginPosition'] = row[0]
                                force_insert[
                                    'Observation'
                                ][
                                    'samplingTime'
                                ]['endPosition'] = row[0]
                                force_insert[
                                    'Observation'
                                ][
                                    'procedure'
                                ] = f"urn:ogc:def:procedure:x-istsos:1.0:{section}"
                                force_insert[
                                    'Observation'
                                ][
                                    'observedProperty'
                                ][
                                    'component'] = header[:1] + header[2:]

                                force_insert[
                                    'Observation'
                                ][
                                    'featureOfInterest'
                                ]['name'] = (
                                    f"urn:ogc:def:feature:x-istsos:1.0:Point:{foi}"
                                )
                                force_insert[
                                    'Observation'
                                ][
                                    'result'
                                ][
                                    'DataArray'
                                ][
                                    'field'
                                ] = fields
                                force_insert[
                                    'Observation'
                                ][
                                    'result'
                                ][
                                    'DataArray'
                                ][
                                    'values'
                                ] = [[row[0]]+update_val]
                                print(force_insert)
                                req2 = requests.post(
                                    (
                                        f'{istsos_url}/wa/istsos/services/'
                                        f'{service}agg/operations/insertobservation'
                                    ),
                                    data=json.dumps(force_insert),
                                    auth=(
                                        config['DEFAULT']['user'],
                                        config['DEFAULT']['password']
                                    )
                                )
                                # print(json.dumps(force_insert))
                                print(req2.status_code)
                        run = False
                    else:
                        print(f"Can't connect to broker. Error code: {rc}")
                        run = False

                def on_publish(client, userdata, result):             #create function for callback
                    print("data published")
                    client.disconnect()
                    pass
                if len(data.split('\n'))>1:
                    client = mqtt.Client(
                        client_id=section,
                        transport='websockets'
                    )
                    client.tls_set()
                    client.username_pw_set(
                        username=mqtt_user,
                        password=mqtt_pwd
                    )
                    client.on_connect = on_connect
                    client.on_publish = on_publish
                    client.connect(
                        mqtt_broker,
                        mqtt_port
                    )
                    client.loop_start()
                    while run:
                        time.sleep(0.1)
            elif transmission == 'fastinsert':
                req_send = requests.post(
                    '{}/wa/istsos/services/{}agg/operations/fastinsert'.format(
                        config['DEFAULT']['remote_istsos'],
                        config['DEFAULT']['remote_service'],
                    ),
                    data=data,
                    auth=(
                        config['DEFAULT']['remote_user'],
                        config['DEFAULT']['remote_password']
                    )
                )
                if req_send.status_code != 200:
                    raise Exception('Data not sent')
                data_sent = True
                if data_sent:
                    # if data sent change quality index
                    fields = []
                    with open(
                        os.path.join(
                            f'{base_path}',
                            'support',
                            driver,
                            f'{sec_type}.yaml'
                        )
                    ) as f:
                        rs = yaml.safe_load(f)
                        fields_tmp = rs['outputs']
                        for field in fields_tmp:
                            fields.append(field)
                            field_name = field['name']
                            if 'time' not in field_name.lower():
                                field_definition = field['definition']
                                field_qi = {
                                    "name": f'{field_name}:qualityIndex',
                                    "definition": f'{field_definition}:qualityIndex',
                                    "uom": "-"
                                }
                                fields.append(field_qi)

                    force_insert['AssignedSensorId'] = assigned_id
                    force_insert[
                        'Observation'
                    ][
                        'samplingTime'
                    ]['beginPosition'] = row[0]
                    force_insert[
                        'Observation'
                    ][
                        'samplingTime'
                    ]['endPosition'] = row[0]
                    force_insert[
                        'Observation'
                    ][
                        'procedure'
                    ] = f"urn:ogc:def:procedure:x-istsos:1.0:{section}"
                    force_insert[
                        'Observation'
                    ][
                        'observedProperty'
                    ][
                        'component'] = header[:1] + header[2:]

                    force_insert[
                        'Observation'
                    ][
                        'featureOfInterest'
                    ]['name'] = (
                        f"urn:ogc:def:feature:x-istsos:1.0:Point:{foi}"
                    )
                    force_insert[
                        'Observation'
                    ][
                        'result'
                    ][
                        'DataArray'
                    ][
                        'field'
                    ] = fields
                    force_insert[
                        'Observation'
                    ][
                        'result'
                    ][
                        'DataArray'
                    ][
                        'values'
                    ] = [[row[0]]+update_val]
                    req2 = requests.post(
                        (
                            f'{istsos_url}/wa/istsos/services/'
                            f'{service}agg/operations/insertobservation'
                        ),
                        data=json.dumps(force_insert),
                        auth=(
                            config['DEFAULT']['user'],
                            config['DEFAULT']['password']
                        )
                    )
                    # print(json.dumps(force_insert))
                    # print(req2.status_code)
            else:
                print('Data not sent because transmission still not implemented')

        else:
            raise Exception('ERROR in loading file')
    else:
        print('Cannot send not aggregated data')

# for section in config.sections():
#     sec = config[section]
#     if 'aggregation_time' in sec.keys():
#         url_get_data = (
#             f'{istsos_url}/{service}agg?request=GetObservation&'
#             f'offering=temporary&procedure={section}&'
#             f'eventtime={event_time}&observedProperty=:&'
#             'qualityIndex=True&responseFormat=text/plain'
#             '&service=SOS&version=1.0.0'
#             '&qualityFilter=<=209'
#         )
#         req = requests.get(
#             url_get_data,
#             auth=(
#                 config['DEFAULT']['user'],
#                 config['DEFAULT']['password']
#             )
#         )
#         if req.status_code == 200:
#             data = req.text
#             csv_read = csv.reader(
#                 StringIO(data), delimiter=','
#             )
#             header = None
#             for row in csv_read:
#                 if header:
#                     try:
#                         # assigned_id = sec['assignedagg_id']
#                         foi = sec['foi']
#                         sec_type = sec['type']
#                         # data = f'{assigned_id};{row[0]}'
#                         data = f'{row[0]}'
#                         update_val = []
#                         for i in range(len(header)):
#                             if i > 1:
#                                 if 'quality' in header[i]:
#                                     data = data + f':{row[i]}'
#                                     if str(row[i]) == '-100':
#                                         update_val.append(int(f'-110'))
#                                     else:
#                                         qi_sent = row[i][:+1] + '1' + row[i][-1:]
#                                         update_val.append(int(qi_sent))
#                                 else:
#                                     data = data + f',{round(float(row[i]), 2)}'
#                                     update_val.append(round(float(row[i]), 2))
#                         # IMPLEMENT SEND DATA
#                         if mode==0 and section=="OPTOD_20_0":
#                             try:
#                                 # The callback for when the client receives a CONNACK response from the server.
#                                 def on_connect(client, userdata, flags, rc):
#                                     global run
#                                     if rc==0:
#                                         # print("Connected with result code "+str(rc))
#                                         # print("Sending...")
#                                         ret = client.publish(
#                                             f"{mqtt_base_topic}/{section}",
#                                             data,
#                                             qos=1,
#                                             retain=True
#                                         )
#                                         if ret[0]==0:
#                                             data_sent = True
#                                             print(f"0,{mqtt_base_topic}/{section},{data}")
#                                         else:
#                                             print(f"1,{section},{data}")
#                                         run = False
#                                     else:
#                                         print(f"Can't connect to broker. Error code: {rc}")
#                                         run = False

#                                 def on_publish(client, userdata, result):             #create function for callback
#                                     print("data published")
#                                     # print(client)
#                                     # print(userdata)
#                                     # print(result)
#                                     pass
#                                 client = mqtt.Client(
#                                     client_id=mqtt_client_id
#                                 )
#                                 client.username_pw_set(
#                                     username=mqtt_user,
#                                     password=mqtt_pwd
#                                 )
#                                 client.on_connect = on_connect
#                                 client.on_publish = on_publish

#                                 client.connect(
#                                     mqtt_broker,
#                                     mqtt_port
#                                 )
#                                 client.loop_start()
                                
#                                 while run:
#                                     time.sleep(0.1)
#                             except Exception as e:
#                                 raise e
#                         else:
#                             req_send = requests.post(
#                                 '{}/wa/istsos/services/{}agg/operations/fastinsert'.format(
#                                     config['DEFAULT']['remote_istsos'],
#                                     config['DEFAULT']['remote_service'],
#                                 ),
#                                 data=data,
#                                 auth=(
#                                     config['DEFAULT']['remote_user'],
#                                     config['DEFAULT']['remote_password']
#                                 )
#                             )
#                             if req_send.status_code != 200:
#                                 raise Exception('Data not sent')
#                             data_sent = True
#                         if data_sent:
#                             # if data sent change quality index
#                             fields = []
#                             with open(
#                                 os.path.join(
#                                     f'{base_path}',
#                                     'support',
#                                     'ponsel',
#                                     f'{sec_type}.yaml'
#                                 )
#                             ) as f:
#                                 rs = yaml.safe_load(f)
#                                 fields_tmp = rs['outputs']
#                                 for field in fields_tmp:
#                                     fields.append(field)
#                                     field_name = field['name']
#                                     if 'time' not in field_name.lower():
#                                         field_definition = field['definition']
#                                         field_qi = {
#                                             "name": f'{field_name}:qualityIndex',
#                                             "definition": f'{field_definition}:qualityIndex',
#                                             "uom": "-"
#                                         }
#                                         fields.append(field_qi)

#                             force_insert['AssignedSensorId'] = assigned_id
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'samplingTime'
#                             ]['beginPosition'] = row[0]
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'samplingTime'
#                             ]['endPosition'] = row[0]
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'procedure'
#                             ] = f"urn:ogc:def:procedure:x-istsos:1.0:{section}"
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'observedProperty'
#                             ][
#                                 'component'] = header[:1] + header[2:]

#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'featureOfInterest'
#                             ]['name'] = (
#                                 f"urn:ogc:def:feature:x-istsos:1.0:Point:{foi}"
#                             )
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'result'
#                             ][
#                                 'DataArray'
#                             ][
#                                 'field'
#                             ] = fields
#                             force_insert[
#                                 'Observation'
#                             ][
#                                 'result'
#                             ][
#                                 'DataArray'
#                             ][
#                                 'values'
#                             ] = [[row[0]]+update_val]
#                             req2 = requests.post(
#                                 (
#                                     f'{istsos_url}/wa/istsos/services/'
#                                     f'{service}agg/operations/insertobservation'
#                                 ),
#                                 data=json.dumps(force_insert),
#                                 auth=(
#                                     config['DEFAULT']['user'],
#                                     config['DEFAULT']['password']
#                                 )
#                             )
#                             # print(json.dumps(force_insert))
#                             # print(req2.status_code)
#                     except Exception as e:
#                         pass
#                 else:
#                     header = row
#         else:
#             raise Exception('ERROR in loading file')
#     else:
#         print('Cannot send not aggregated data')


# # use the QI to know if a data is sent or not

# # &qualityfilter=%3E210
# # &qualityfilter=>210
