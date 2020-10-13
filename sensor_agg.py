#!/usr/bin/python

import configparser
import os
from datetime import datetime, timezone, timedelta
import time
import sys
from io import StringIO
import csv
import pandas as pd

# external lib
import requests

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

if not df.empty:

    columns = df.columns[1:]

    data_post = None

    idx = 0

    for col in columns:
        if col.find('quality') < 0:
            df_filtered = df.loc[df[columns[idx+1]] >= 100]
            mean_val = df_filtered[col].mean()
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

    print(data_post)

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