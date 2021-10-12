#!/usr/bin/python

import configparser
import os
from datetime import datetime, timezone, timedelta
import time
import sys
from io import StringIO
import csv
import pandas as pd
from statistics import stdev
import json
import yaml

# external lib
import requests

#
def time_consistency_check(x):
    if len(x) >= 3:
        sum_abs_val = abs(x[1] - x[0]) + abs(x[1] - x[2])
        four_std = 4*stdev(x)
        if sum_abs_val <= four_std:
            return 103
        else:
            return False
    else:
        return False

def minimum_variability_check(x):
    if sum(x)/len(x) == x[0]:
        return False
    else:
        return 104

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
istsos_url = config['DEFAULT']['istsos']
service = config['DEFAULT']['service']
assigned_id = section['assignedagg_id']

### READING SENSOR METADATA
sensor_type = section['type']
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

now = datetime.now(timezone.utc)
end_position = datetime(
    now.year, now.month, now.day,
    now.hour, now.minute, tzinfo=timezone.utc
)
begin_position = end_position - timedelta(
    minutes=int(section['aggregation_time'])
)

event_time = f'{begin_position.isoformat()}/{end_position.isoformat()}'

url_get_data = (
    f'{istsos_url}/{service}?request=GetObservation&'
    f'offering=temporary&procedure={section_name}&'
    f'eventTime={event_time}&observedProperty=:&'
    'qualityIndex=True&responseFormat=text/plain'
    '&service=SOS&version=1.0.0'
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
else:
    raise Exception('ERROR in loading file')

expected_num_values = (
    int(config[section_name]['aggregation_time']) /
    int(config[section_name]['sampling_time'])
)

df = pd.read_csv(
    StringIO(data),
    index_col=0,
    parse_dates=True
)

df_data = df.drop(
  ['urn:ogc:def:procedure'], axis=1
)

columns = df_data.columns
col_idx = 0
for col in columns:
    if 'quality' not in col and 'procedure' not in col:
        #############
        # STEP TEST #
        #############
        freq_sec = (int(config[section_name]['sampling_time'])*3)*60
        ts_tmp2 = df_data.loc[
            df_data[columns[col_idx+1]] == 101
        ]
        ts_tmp2 = ts_tmp2[col].rolling(
            '{}s'.format(freq_sec)
        ).apply(
            lambda x: time_consistency_check(x),
            raw=True
        )
        # updating main dataframe
        df_data[columns[col_idx+1]].update(
            ts_tmp2.where(lambda x : x>0)
        )
        ################################################
        # TIME CONSISTENCY - MINIMUM VARIABILITY CHECK #
        ################################################
        ts_tmp3 = df_data.loc[
            df_data[columns[col_idx+1]] == 202
        ]
        freq_sec = int(config[section_name]['aggregation_time'])*60
        ts_tmp3 = ts_tmp3[col].rolling(
            '{}s'.format(freq_sec)
        ).apply(
            lambda x: minimum_variability_check(x),
            raw=True
        )
        # updating main dataframe
        df_data[columns[col_idx+1]].update(
            ts_tmp2.where(lambda x : x>0)
        )
    col_idx+=1

df_data.insert(0, 'T', df_data.index.strftime('%Y-%m-%dT%H:%M:%S%z'))
data_with_qi = df_data.values.tolist()


####    UPDATE DATA istSOS   ###
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
    "beginPosition": begin_position.isoformat(),
    "endPosition":  end_position.isoformat()
}
go['result']['DataArray']['values'] = data_with_qi

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

aggregators = ['AVG', 'SUM', 'MIN', 'MAX']

if not df_data.empty:
    columns = df_data.columns[1:]
    data_post = None
    idx = 0
    for col in columns:
        if 'aggregator' in outputs[idx+1]:
            aggregator = outputs[idx+1]['aggregator']
        else:
            aggregator = 'AVG'
        if aggregator not in aggregators:
            aggregator = 'AVG'
        if col.find('quality') < 0:
            df_filtered = df_data.loc[
                df_data[columns[idx+1]] >= 104
            ]
            if df_filtered.empty:
                if aggregator == 'AVG':
                    mean_val = df_data[col].mean()
                elif aggregator == 'SUM':
                    mean_val = df_data[col].sum()
                elif aggregator == 'MIN':
                    mean_val = df_data[col].min()
                elif aggregator == 'MAX':
                    mean_val = df_data[col].max()
                mean_val = round(mean_val, 2)
                min_qi = 200
            else:
                if aggregator == 'AVG':
                    mean_val = df_filtered[col].mean()
                elif aggregator == 'SUM':
                    mean_val = df_filtered[col].sum()
                elif aggregator == 'MIN':
                    mean_val = df_filtered[col].min()
                elif aggregator == 'MAX':
                    mean_val = df_filtered[col].max()
                min_qi = df_filtered[columns[idx+1]].min()
                cnt_val = df_filtered[col].count()
                perc = cnt_val/expected_num_values
                if perc == 0:
                    if cnt_val > 0:
                        min_qi = 0
                    else:
                        min_qi = -100
                elif perc < 0.6:
                    mean_val = round(mean_val, 2)
                    min_qi = 200
                else:
                    mean_val = round(mean_val, 2)
                    min_qi = 201
            if data_post:
                data_post = f'{data_post},{mean_val}:{min_qi}'
            else:
                data_post = (
                    f'{assigned_id};{end_position.isoformat()},{mean_val}:{min_qi}'
                )

    req = requests.post(
        '{}/wa/istsos/services/{}agg/operations/fastinsert'.format(
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

else:
    print("No data to aggregate")