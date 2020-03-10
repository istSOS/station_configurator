#!/usr/bin/python

import configparser
import sys
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
import json
import os

# external lib
import requests
import yaml


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


event_time = f'{begin_position.isoformat()}/{end_position.isoformat()}'

for section in config.sections():
    sec = config[section]
    if 'aggregation_time' in sec.keys():
        url_get_data = (
            f'{istsos_url}/{service}agg?request=GetObservation&'
            f'offering=temporary&procedure={section}&'
            f'eventtime={event_time}&observedProperty=:&'
            'qualityIndex=True&responseFormat=text/plain'
            '&service=SOS&version=1.0.0'
            '&qualityfilter=<10'
        )
        req = requests.get(
            url_get_data,
            auth=(
                config['DEFAULT']['user'],
                config['DEFAULT']['password']
            )
        )
        if req.status_code == 200:
            data = req.text
            csv_read = csv.reader(
                StringIO(data), delimiter=','
            )
            header = None
            for row in csv_read:
                if header:
                    try:
                        assigned_id = sec['assignedagg_id']
                        foi = sec['foi']
                        sec_type = sec['type']
                        data = f'{assigned_id};{row[0]}'
                        update_val = []
                        for i in range(len(header)):
                            if i > 1:
                                if 'quality' in header[i]:
                                    data = data + f':{row[i]}'
                                    if str(row[i]) == '-100':
                                        update_val.append(int(f'-110'))
                                    else:
                                        update_val.append(int(f'1{row[i]}'))
                                else:
                                    data = data + f',{round(float(row[i]), 2)}'
                                    update_val.append(round(float(row[i]), 2))
                        # IMPLEMENT SEND DATA
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
                        # if data sent change quality index
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
                        print(req2.status_code)
                    except Exception as e:
                        pass
                else:
                    header = row
        else:
            raise Exception('ERROR in loading file')
    else:
        print('Cannot send not aggregated data')


# use the QI to know if a data is sent or not

# &qualityfilter=%3E210
# &qualityfilter=>210
