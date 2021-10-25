#!/usr/bin/python

import configparser
import sys
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
import json
import os
import time
from lib import SaraR4
import logzero
import pandas as pd
from dateutil import parser

# external lib
import requests
import yaml
import paho.mqtt.client as mqtt


logging = logzero.logger

### FUNCTIONS
def connect(serial_path, radio_mode, apn, umnoprof=100, debug=False):
    try:
        # SaraR4.reset()
        sara_module = SaraR4.SaraR4Module(
            serial_path=serial_path,
            DEBUG=debug
        )
        # sara_module.set_umnoprof(umnoprof)
        sara_module.set_radio_mode(radio_mode)
        sara_module.set_provider_name(apn)
        # sara_module.set_operator(22801, TIMEOUT=120)
        if not sara_module.init():
            time.sleep(5)
            if not sara_module.init():
                raise Exception("Can't connect to operator")
        return sara_module
    except Exception as e:
        SaraR4.power_off()
        raise e

def set_mqtt_params(sara_module, mqtt_server, mqtt_port, mqtt_ssl, mqtt_user, mqtt_password):
    sara_module.set_mqtt_params(
        mqtt_server, mqtt_port,
        mqtt_ssl, mqtt_user,
        mqtt_password
    )

def mqtt_login(sara_module):
    if not sara_module.mqtt_login(TIMEOUT=60):
        if sara_module.mqtt_logout(TIMEOUT=60):
            if not sara_module.mqtt_login(TIMEOUT=60):
                logging.error("Can't login to MQTT server")
                raise Exception("Can't login to MQTT server")

def mqtt_logout(sara_module):
    return sara_module.mqtt_logout()

def mqtt_publish(sara_module, topic, data):
    return sara_module.mqtt_publish(topic, data)

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

if transmission == 'nbiot':
    # MQTT
    modem_serial_path = config['DEFAULT']['modem_serial_path']
    modem_debug = config['DEFAULT']['modem_debug']
    modem_operator = config['DEFAULT']['modem_operator']
    modem_radio_mode = config['DEFAULT']['modem_radio_mode']
    modem_apn = config['DEFAULT']['modem_apn']
    modem_umnoprof = config['DEFAULT']['modem_umnoprof']
    mqtt_address = config['DEFAULT']['mqtt_address']
    mqtt_port = config['DEFAULT']['mqtt_port']
    mqtt_base_topic = config['DEFAULT']['mqtt_base_topic']
    mqtt_ssl = config['DEFAULT']['mqtt_ssl']
    mqtt_user = config['DEFAULT']['mqtt_user']
    mqtt_pwd = config['DEFAULT']['mqtt_pwd']
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

mqtt_logged = False
sara_module = False
for section in config.sections():
    logging.info(section)
    run = True
    sec = config[section]
    istsos_service = config['DEFAULT']['remote_istsos_service']
    sec_type = sec['type']
    driver = sec['driver']
    # assigned_id = sec['driver']
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
            df = pd.read_csv(
                StringIO(req.text),
                index_col=0,
                parse_dates=True
            )
            df_data = df.drop(
                ['urn:ogc:def:procedure'], axis=1
            )
            if not df_data.empty:
                df_data.insert(
                    0, 'T',
                    df_data.index.strftime(
                        '%Y-%m-%dT%H:%M:%S%z'
                    )
                )
                columns = df_data.columns
                data_to_send = df_data.values.tolist()
                if len(data_to_send):
                    if transmission == 'nbiot':
                        if not sara_module:
                            try:
                                if not mqtt_logged:
                                    sara_module = connect(
                                        '/dev/serial0', 8,
                                        'shared.m2m.ch', debug=True
                                    )
                                    set_mqtt_params(
                                        sara_module, mqtt_address,
                                        mqtt_port, mqtt_ssl,
                                        mqtt_user, mqtt_pwd
                                    ) 
                                    mqtt_login(sara_module)
                                    mqtt_logged = True
                            except:
                                logging.info('error')
                                SaraR4.power_off()
                                raise Exception('Can\'t connect')
                    else:
                        logging.info('Data not sent because transmission still not implemented')
                for row in data_to_send:
                    i = 0
                    v = ''
                    errors = 0
                    q_idxs = []
                    for col in columns:
                        if "qualityIndex" in col:
                            q_idxs.append(i)
                            v = v + ':{}'.format(row[i])                                    
                        else:
                            if v:
                                v = v + ',{}'.format(row[i])
                            else:
                                v = '{}'.format(row[i])
                        i+=1
                    while errors<=3:
                        published = mqtt_publish(
                            sara_module,
                            'istsos/{}/{}'.format(
                                istsos_service,
                                config[section]['assignedremote_id']
                            ), v
                        )
                        if published:
                            try:
                                begin_position = parser.parse(row[0])
                                begin_position = begin_position - timedelta(seconds=1)
                                url_get_data = (
                                    '{}/{}agg?request=GetObservation&'
                                    'offering=temporary&procedure={}&'
                                    'eventtime={}/{}&observedProperty=:&'
                                    'qualityIndex=True&responseFormat=application/json'
                                    '&service=SOS&version=1.0.0'
                                    '&qualityFilter=<=209'
                                ).format(
                                    istsos_url,
                                    service,
                                    section,
                                    begin_position.isoformat(),
                                    row[0]
                                )
                                req = requests.get(
                                    url_get_data,
                                    auth=(
                                        config['DEFAULT']['user'],
                                        config['DEFAULT']['password']
                                    ),
                                    verify=False
                                )
                                res_json = req.json()
                                for q_idx in q_idxs:
                                    res_member = res_json["ObservationCollection"]['member'][0]                                    
                                    qi = str(res_member['result']['DataArray']['values'][0][q_idx])[:1] + '1' + str(res_member['result']['DataArray']['values'][0][q_idx])[1+1:]
                                    ###check somthing wrong!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                                    res_member['result']['DataArray']['values'][0][q_idx] = int(qi)
                                res_member['samplingTime']['beginPosition'] = row[0]
                                res_member['samplingTime']['endPosition'] = row[0]
                                res = requests.post(
                                    "%s/wa/istsos/services/%s/operations/"
                                    "insertobservation" % (
                                        config['DEFAULT']['istsos'],
                                        '{}agg'.format(config['DEFAULT']['service']),
                                    ),
                                    auth=(
                                        config['DEFAULT']['user'],
                                        config['DEFAULT']['password']
                                    ),
                                    data=json.dumps({
                                        "ForceInsert": "true",
                                        "AssignedSensorId": config[section]['assignedagg_id'],
                                        "Observation": res_member
                                    })
                                )
                                res.raise_for_status()
                                if res.json()['success']:
                                    logging.info(
                                        " > Insert observation success: %s" % (
                                            res.json()['success']
                                        )
                                    )
                                    break
                                else:
                                    errors+=1
                            except Exception as e:
                                logging.error(str(e))
                                errors+=1
                                logging.warning('Something went wrong in changing the QI flag')
                        else:
                            if errors == 3:
                                if not sara_module.soft_reset():
                                    SaraR4.reset()
                                SaraR4.power_off()
                                logging.error("Can't send data due to connection problem.")
                                raise Exception("Can't send data due to connection problem.")
                            errors+=1
            else:
                logging.info('No data to send')        

        else:
            if mqtt_logged:
                mqtt_logout(sara_module)
            SaraR4.power_off()
            raise Exception('ERROR in loading file')
    else:
        if mqtt_logged:
            mqtt_logout(sara_module)
        SaraR4.power_off()
        logging.info('Cannot send not aggregated data')

SaraR4.power_off()
# # use the QI to know if a data is sent or not

# # &qualityfilter=%3E210
# # &qualityfilter=>210
