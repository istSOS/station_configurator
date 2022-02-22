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
import time
import logging
import json
import sys
import argparse
import getpass
from lib import SaraR4

# external lib
import yaml
import requests
from crontab import CronTab
import logzero

# sensors libs
from module.ponsel import Ponsel
from module.lufft import WS_UMB
from module.unilux import Unilux
from module.ina219 import read_ina219

__author__ = "Daniele Strigaro"
__email__ = "daniele.strigaro@supsi.ch"
__license__ = "Apache License, Version 2.0"
__revision__ = "$Rev: 100 $"
__date__ = "$Date: 2020-02-19 17:22:30 $"
__abspath__ = os.path.abspath(os.getcwd())
__config__ = os.path.join(
    __abspath__,
    'default.cfg'
)

# create log folder and file
log_path = os.path.join(
    __abspath__, 'log'
)

if not os.path.exists(log_path):
    os.makedirs(log_path)

logzero.logfile(
    os.path.join(
        __abspath__,
        'log',
        "station.log"
    ),
    maxBytes=1e6,
    backupCount=3
)

"""
This function save the configuration into the config file
(e.g. default.cfg).

Attributes:
    real (int): The real part of complex number.
    imag (int): The imaginary part of complex number.
"""


class Station():
    """
    This is a class for configure a monitoring station.
    """

    def __init__(self):
        self.logger = logzero.logger

        # reading configuration file default.cfg
        self.config = configparser.ConfigParser()
        self.config.read(__config__)
        self.sections = self.config.sections()

        # istsos variables
        self.istsos_url = self.config['DEFAULT']['istsos']
        self.istsos_srv = self.config['DEFAULT']['service']
        self.istsos_auth = (
            self.config['DEFAULT']['user'],
            self.config['DEFAULT']['password']
        )

        # remote istsos variables
        self.remote_istsos_url = self.config['DEFAULT']['remote_istsos_url']
        self.remote_istsos_srv = self.config['DEFAULT']['remote_istsos_service']
        self.remote_istsos_auth_type = self.config['DEFAULT']['remote_istsos_auth']
        if self.remote_istsos_auth_type == 'oauth':
            self.remote_oauth_token_url = self.config['DEFAULT']['remote_oauth_token_url']
            self.remote_oauth_client_id = self.config['DEFAULT']['remote_oauth_client_id']
            body_data = {
                "username": self.config['DEFAULT']['remote_istsos_user'],
                "password": self.config['DEFAULT']['remote_istsos_password'],
                "grant_type": "password",
                "client_id": "istsos-istsos"
            }
            req = requests.post(
                self.remote_oauth_token_url,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
                },
                data=body_data
            )
            if req.status_code==200:
                res = req.json()
                self.remote_istsos_auth = "Bearer {}".format(
                    res['access_token']
                )
            else:
                raise "Can't get authorization token from oauth service"
        elif self.remote_istsos_auth == 'basic':
            self.remote_istsos_auth = (
                self.config['DEFAULT']['remote_istsos_user'],
                self.config['DEFAULT']['remote_istsos_password']
            )
        else:
            print(self.remote_istsos_auth)
            raise "remote_istsos_auth: remote authorization type not recognized"

        # checking configuration file
        self.check_default_section()
        self.mqtt_login = False

    def save_config(self):
        """
        This function save the configuration into the config file
        (e.g. default.cfg).
        """
        with open(__config__, 'w') as f:
            self.config.write(f)

    def connect(self, serial_path, radio_mode, apn, umnoprof=100, debug=False):
        try:
            # SaraR4.reset()
            self.sara_module = SaraR4.SaraR4Module(
                serial_path=serial_path,
                DEBUG=debug
            )
            # sara_module.set_umnoprof(umnoprof)
            self.sara_module.set_radio_mode(radio_mode)
            self.sara_module.set_provider_name(apn)
            # sara_module.set_operator(22801, TIMEOUT=120)
            
            if not self.sara_module.init():
                time.sleep(5)
                if not self.sara_module.init():
                    raise Exception("Can't connect to operator")
            return self.sara_module
        except Exception as e:
            SaraR4.power_off()
            raise e

    def set_mqtt_params(self, mqtt_server, mqtt_port, mqtt_ssl, mqtt_user, mqtt_password):
        self.sara_module.set_mqtt_params(
            mqtt_server, mqtt_port,
            mqtt_ssl, mqtt_user,
            mqtt_password
        )

    def mqtt_logout(self):
        return self.sara_module.mqtt_logout()

    def mqtt_publish(self, topic, data):
        self.sara_module.mqtt_publish(topic, data)

    def set_send_data(self):
        """
        This function creates a job in the crontab
        which refers to the python script send_data.py.
        This command is performed according to the sending_time
        value set in the config file
        """
        python_path = sys.executable

        if self.config['DEFAULT']['transmission'] == 'lora':
            path_script = os.path.join(
                __abspath__,
                'send_data_lora.py'
            )
        elif self.config['DEFAULT']['transmission'] == 'fastinsert':
            path_script = os.path.join(
                __abspath__,
                'send_data.py'
            )
        elif self.config['DEFAULT']['transmission'] == 'mqtt':
            raise Exception("transmission: mqtt still to be implemented")
        elif self.config['DEFAULT']['transmission'] == 'nbiot':
            path_script = os.path.join(
                __abspath__,
                'send_data_nbiot.py'
            )
            
        else:
            raise Exception("transmission: transmission type not recognized")

        path_config = os.path.join(
            __abspath__,
            'default.cfg'
        )

        cron = CronTab(
            user=getpass.getuser()
        )
        path_log = os.path.join(
            __abspath__,
            'log',
            f'send_data.log'
        )
        command = (
            f'/usr/bin/flock -w 0 /tmp/send.lock {python_path} {path_script}'
            f' -c {path_config} >> {path_log} 2>&1'
        )
        add_cron = True
        for job in cron:
            if command in job.command:
                add_cron = False
        if add_cron:
            if int(self.config['DEFAULT']['sending_time']) > 30:
                job = cron.new(command=command)
                job.minute.on(
                    str(int(self.config['DEFAULT']['sending_time']) - 30)
                )
                cron.write()
                job = cron.new(command=command)
                job.minute.on(
                    self.config['DEFAULT']['sending_time']
                )
                cron.write()
            else:
                job = cron.new(command=command)
                job.minute.every(
                    self.config['DEFAULT']['sending_time']
                )
                cron.write()


    def create_service(self):
        """
        This function creates the main istSOS service
        to archive the raw data coming from the sensors
        and collected with the python file 'sensor_rw.py'.
        The service name is set according to the service
        parameter set in the config file.
        """
        service_name = self.config['DEFAULT']['service']
        epsg = '4326'
        if 'epsg' in self.config['DEFAULT'].keys():
            epsg = self.config['DEFAULT']['epsg']
        data_post = {
            "service": f"{service_name}",
            "epsg": epsg
        }
        req = requests.post(
            f'{self.istsos_url}/wa/istsos/services',
            data=json.dumps(data_post),
            auth=self.istsos_auth
        )
        if req.status_code == 200:
            check_idx = req.text.find("true")
            if check_idx > 0:
                return {'success': True}
            else:
                check_idx = req.text.find("already exist")
                if check_idx > 0:
                    return {'success': True}
                else:
                    return {
                        'success': False,
                        'msg': req.text
                    }
        else:
            return {
                'success': False,
                'msg': req.text
            }

    def create_service_agg(self, section):
        """
        This function creates the aggregation istSOS service
        to archive the aggregated data coming from
        the raw istSOS service and processed by
        the python file 'sensor_agg.py'.
        The service name is set according to the service
        parameter set in the config file plus adding the text 'agg'.
        """
        service_name = self.config['DEFAULT']['service']
        epsg = '4326'
        if 'epsg' in self.config[section].keys():
            epsg = self.config[section]['epsg']
        data_post = {
            "service": f"{service_name}agg",
            "epsg": epsg
        }
        req = requests.post(
            f'{self.istsos_url}/wa/istsos/services',
            data=json.dumps(data_post),
            auth=self.istsos_auth
        )
        if req.status_code == 200:
            check_idx = req.text.find("true")
            if check_idx > 0:
                return {'success': True}
            else:
                check_idx = req.text.find("already exist")
                if check_idx > 0:
                    return {'success': True}
                else:
                    return {
                        'success': False,
                        'msg': req.text
                    }
        else:
            return {
                'success': False,
                'msg': req.text
            }

    def set_aggregation(self):
        """
        This function creates the aggregation istSOS service
        to archive the aggregated data coming from
        the raw istSOS service and processed by
        the python file 'sensor_agg.py'.
        The service name is set according to the service
        parameter set in the config file plus adding the text 'agg'.
        """
        python_path = sys.executable

        path_script = os.path.join(
            __abspath__,
            'sensor_agg.py'
        )

        path_config = os.path.join(
            __abspath__,
            'default.cfg'
        )

        cron = CronTab(
            user=getpass.getuser()
        )
        for section in self.sections:
            add_cron = True
            if 'aggregation_time' in self.config[section].keys():
                path_log = os.path.join(
                    __abspath__,
                    'log',
                    f'{section}_agg.log'
                )
                command = (
                    f'{python_path} {path_script} -s {section}'
                    f' -c {path_config} >> {path_log} 2>&1'
                )

                add_cron = True
                for job in cron:
                    if command in job.command:
                        add_cron = False
                if add_cron:
                    job = cron.new(command=command)
                    job.minute.every(
                        self.config[section]['aggregation_time']
                    )
                    cron.write()

    def set_sampling(self):
        """
        This function sets the sampling process for each sensor.
        """
        python_path = sys.executable

        path_script = os.path.join(
            __abspath__,
            'sensor_rw.py'
        )

        path_config = os.path.join(
            __abspath__,
            'default.cfg'
        )

        cron = CronTab(
            user=getpass.getuser()
        )
        files_sh = []

        for section in self.sections:
            if self.config[section].get('assigned_id'):
                path_log = os.path.join(
                    __abspath__,
                    'log',
                    f'{section}.log'
                )
                command = (
                    f'{python_path} {path_script} -s {section}'
                    f' -c {path_config} >> {path_log} 2>&1'
                )
                sampling_time = self.config[section]['sampling_time']
                shell_path = os.path.join(
                    __abspath__,
                    f'read_{sampling_time}.sh'
                )
                with open(shell_path, 'a') as f:
                    f.write(f'{command}\n')
                if shell_path not in files_sh:
                    files_sh.append(shell_path)

        for sh in files_sh:
            add_cron = True
            for job in cron:
                if sh in job.command:
                    add_cron = False
            if add_cron:
                job = cron.new(command=f"/usr/bin/flock -w 0 /tmp/sampling.lock sh {sh}")
                every = sh.split('_')[-1].split('.')[0]
                job.minute.every(int(every))
                cron.write()

    def insert_sensor(self, sensor, section, agg=False, remote=False):
        """
        This function registers the sernsors into the istSOS services.

        Attributes:
            sensor (str): The section related to the sensor name
                          which is equal to the section
                          of the default.cfg file.
        """
        section_obj = self.config[section]
        sensor_type = section_obj['type']
        with open(
            os.path.join(
                __abspath__,
                'support',
                section_obj['driver'],
                f'{sensor_type}.yaml'
            )
        ) as f:
            rs = yaml.safe_load(f)
            if section_obj['driver'] == 'ponsel':
                rs['system_id'] = sensor.get_serial_number()
                rs['description'] = sensor.get_pod_desc()
                rs['classification'][1]['value'] = sensor.get_pod_desc()
            elif section_obj['driver'] == 'lufft':
                rs['system_id'] = section
            elif section_obj['driver'] == 'unilux':
                rs['system_id'] = section
            elif section_obj['driver'] == 'ina219':
                rs['system_id'] = section
            rs['system'] = section
            rs['identification'][0][
                'value'] = rs['identification'][0]['value'] + section
            rs['location']['geometry']['coordinates'] = [
                section_obj['lon'],
                section_obj['lat'],
                section_obj['alt']
            ]
            rs['location']['crs']['properties']['name'] = section_obj['epsg']
            rs['location']['properties']['name'] = section_obj['foi']
            if agg:
                req = requests.post(
                    f'{self.istsos_url}/wa/istsos/services/'
                    f'{self.istsos_srv}agg/procedures',
                    data=json.dumps(rs),
                    auth=self.istsos_auth
                )
            elif remote:
                if self.remote_istsos_auth_type == 'oauth':
                    req = requests.post(
                        f'{self.remote_istsos_url}/wa/istsos/services/' +
                        f'{self.remote_istsos_srv}/procedures',
                        headers={
                            "Authorization": self.remote_istsos_auth
                        },
                        data=json.dumps(rs)
                    )
                    # req = requests.post(
                    #     f'{self.remote_istsos_url}/wa/istsos/services/' 
                    #     f'{self.remote_istsos_srv}/procedures',
                    #     headers={'Authorization': 'Bearer '+ token['access_token']},
                    #     data=json.dumps(rs)
                    # )
                else:
                    req = requests.post(
                        f'{self.remote_istsos_url}/wa/istsos/services/'
                        f'{self.remote_istsos_srv}/procedures',
                        data=json.dumps(rs),
                        auth=self.remote_istsos_auth
                    )
            else:
                req = requests.post(
                    f'{self.istsos_url}/wa/istsos/services/'
                    f'{self.istsos_srv}/procedures',
                    data=json.dumps(rs),
                    auth=self.istsos_auth
                )

            if req.status_code == 200:
                check_idx = req.text.find("AssignedSensorId")
                if check_idx > 0:
                    if not remote:
                        assigned_id = req.text.split(':')[-2].split('<')[0]
                        if agg:
                            self.config[section]['assignedagg_id'] = assigned_id
                        else:
                            self.config[section]['assigned_id'] = assigned_id
                        self.save_config()
                    else:
                        assigned_id = req.text.split(':')[-2].split('<')[0]
                        self.config[section]['assignedremote_id'] = assigned_id
                        self.save_config()
                else:
                    check_idx = req.text.find("already exist")
                    if check_idx > 0:
                        if agg:
                            self.logger.info(
                                f'--> {section} already exist in service'
                                f' {self.istsos_srv}agg'
                            )
                        else:
                            self.logger.info(
                                f'--> {section} already exist in service'
                                f' {self.istsos_srv}'
                            )
                    else:
                        self.logger.warning(req.text)
            else:
                self.logger.error(req.text)

    def set_sensors(self):
        """
        This function sets the sensors.
        """
        for section in self.sections:
            self.logger.info(f'--> Installing sensor {section}')
            if self.config[section]['driver'] == 'ponsel':
                try:
                    if 'addr' in self.config[section].keys():
                        sensor = Ponsel(
                            "{}".format(self.config[section]['port']),
                            int(self.config[section]['addr'])
                        )
                    else:
                        sensor = Ponsel(
                            "{}".format(self.config[section]['port']),
                            int(self.config[section]['type'])
                        )
                    sensor.set_run_measurement(0x001f)
                    time.sleep(1)
                    description = sensor.get_pod_desc()
                except:
                    time.sleep(1)
                    raise Exception("Can\'t find sensor")
                
                self.logger.info(description)
                if description:
                    self.insert_sensor(sensor, section)
                    if 'aggregation_time' in self.config[section].keys():
                        crt_srv_agg = self.create_service_agg(section)
                        if crt_srv_agg['success']:
                            self.insert_sensor(
                                sensor, section,
                                agg=True
                            )
                            if self.remote:
                                self.insert_sensor(
                                    sensor, section,
                                    agg=False, remote=True
                                )
                        else:
                            self.logger.error(
                                '\t\t--> Aggregation service NOT created'
                            )
                            return crt_srv_agg
                else:
                    return {
                        'success': False,
                        'msg': '\t\t--> Can\'t get Ponsel sensor description'
                    }
                self.logger.info(
                    f'--> Sensor {section} INSTALLED'
                )
            elif self.config[section]['driver'] == 'unilux':
                try:
                    s = Unilux("{}".format(self.config[section]['port']))
                    s.start()
                    data = s.get_values()
                    if data:
                        s.stop()
                        self.insert_sensor(umb, section)
                        if 'aggregation_time' in self.config[section].keys():
                            crt_srv_agg = self.create_service_agg(section)
                            if crt_srv_agg['success']:
                                self.insert_sensor(
                                    umb, section,
                                    agg=True
                                )
                                if self.remote:
                                    self.insert_sensor(
                                        umb, section,
                                        agg=False, remote=True
                                    )
                            else:
                                self.logger.error(
                                    '\t\t--> Aggregation service NOT created'
                                )
                                return crt_srv_agg
                    else:
                        s.stop()
                        raise Exception("Can\'t get data from Unilux")
                except Exception as e:
                    raise Exception("Can\'t find sensor")
            elif self.config[section]['driver'] == 'lufft':
                value_UMB = [200, 305, 500, 510, 900, 100, 110, 440, 400]
                try:
                    values = []
                    try:
                        with WS_UMB("{}".format(self.config[section]['port'])) as umb:
                            for v in value_UMB:
                                value, st = umb.onlineDataQuery(v, int(self.config[section]['addr']))
                                values.append(
                                    round(value, 2)
                                )
                        self.insert_sensor(umb, section)
                        if 'aggregation_time' in self.config[section].keys():
                            crt_srv_agg = self.create_service_agg(section)
                            if crt_srv_agg['success']:
                                self.insert_sensor(
                                    umb, section,
                                    agg=True
                                )
                                if self.remote:
                                    self.insert_sensor(
                                        umb, section,
                                        agg=False, remote=True
                                    )
                            else:
                                self.logger.error(
                                    '\t\t--> Aggregation service NOT created'
                                )
                                return crt_srv_agg
                    except:
                        raise Exception("Can\'t find sensor")
                    # with WS_UMB(self.config[section]['port']) as umb:
                    #     for v in value_UMB:
                    #         value, st = umb.onlineDataQuery(v, int(self.config[section]['addr']))
                    #         if st!=0:
                    #             raise Exception('Not working')
                except Exception as e:
                    return {
                        'success': False,
                        'msg': '\t\t--> Can\'t find lufft sensor'
                    }
            elif self.config[section]['driver'] == 'ina219':
                try:
                    values = []
                    try:
                        data = read_ina219()
                        self.insert_sensor(data, section)
                        if 'aggregation_time' in self.config[section].keys():
                            crt_srv_agg = self.create_service_agg(section)
                            if crt_srv_agg['success']:
                                self.insert_sensor(
                                    umb, section,
                                    agg=True
                                )
                                if self.remote:
                                    self.insert_sensor(
                                        umb, section,
                                        agg=False, remote=True
                                    )
                            else:
                                self.logger.error(
                                    '\t\t--> Aggregation service NOT created'
                                )
                                return crt_srv_agg
                    except:
                        raise Exception("Can\'t find sensor")
                except Exception as e:
                    return {
                        'success': False,
                        'msg': '\t\t--> Can\'t find lufft sensor'
                    }
            else:
                self.logger.error(
                    'Sensor type not supported.'
                    'Supported sensor list: ponsel'
                )
                return {
                    'success': False,
                    'msg': (
                        'Sensor type not supported.'
                        'Supported sensor list: ponsel'
                    )
                }
        return {'success': True}

    def check_sensor_conf(self, name):
        """
        Check the config file
        TBD
        """
        available_params = [
            'sampling_time', 'aggregation_time',
            'sending_time', 'driver', 'type',
            'addr', 'port', 'baudrate',
            'foi', 'lat', 'lon'
        ]
        params = list(
            self.config[name].keys()
        )
        for par in params:
            if par not in available_params:
                self.logger.error(
                    ('ERROR --> ')
                )

    def check_default_section(self):
        """
        Check the config file
        TBD
        """
        if self.config.defaults():
            params = list(
                self.config.defaults().keys()
            )
            if 'transmission' not in params:
                raise Exception(
                    'ERROR --> transmission is not set.'
                )
            elif self.config.defaults()['transmission'] not in [
                    'lora', 'serial', 'nbiot', 'lte']:
                self.logger.error(
                    'transmission is not set correctly.'
                    ' Accepted values: lora, serial'
                )
                raise Exception(
                    (
                        'ERROR --> transmission is not set correctly.'
                        ' Accepted values: lora, serial'
                    )
                )
            if 'istsos' not in params:
                self.logger.error(
                    'istsos url is not set.'
                )
                raise Exception(
                    'ERROR --> istsos url is not set.'
                )

            # check remote istsos conf
            if (self.remote_istsos_url and
                    self.remote_istsos_srv and
                        self.remote_istsos_auth):
                if self.remote_istsos_auth_type == 'oauth':
                    req = requests.get(
                        f'{self.remote_istsos_url}/{self.remote_istsos_srv}?'
                        f'request=getCapabilities&service=SOS',
                        headers={
                            "Authorization": self.remote_istsos_auth
                        }
                    )
                else:
                    req = requests.get(
                        f'{self.remote_istsos_url}/{self.remote_istsos_srv}?'
                        f'request=getCapabilities&service=SOS',
                        auth=self.remote_istsos_auth
                    )
                if req.status_code == 200:
                    self.remote = True
                else:
                    logging.error(req.text)
                    self.remote = False
                    self.logger.warning(
                        'The remote istSOS is not correctly set'
                        ' or is not working'
                    )
            else:
                self.remote = False
                self.logger.warning(
                    'The remote istSOS is not correctly set'
                    ' or is not working'
                )
        else:
            self.logger.error(
                (
                    'DEFAULT section was'
                    ' not found into the default.cfg file.'
                )
            )

    def delete_service(self, agg=False, remote=False):
        """
        This function delete the services configured
        on the local istSOS.

        Attributes:
            agg (bool): If True the aggregation service is deleted.
                        If False the raw service is deleted.
        """
        if agg:
            self.logger.info(
                '\t--> Aggregator service deleting...'
            )
            service_name = self.config['DEFAULT']['service'] + 'agg'
            data_post = {
                "service": f"{service_name}",
            }
            req = requests.delete(
                f'{self.istsos_url}/wa/istsos/services/{service_name}',
                data=json.dumps(data_post),
                auth=self.istsos_auth
            )
        elif remote:
            self.logger.info(
                '\t--> Aggregator service deleting...'
            )
            service_name = self.config['DEFAULT']['remmote_istsos_service'] + 'agg'
            data_post = {
                "service": f"{service_name}",
            }
            if self.remote_istsos_auth_type == 'oauth':
                req = requests.delete(
                    f'{self.remote_istsos_url}/wa/istsos/services/{service_name}',
                    headers={
                        "Authorization": self.remote_istsos_auth
                    },
                    data=json.dumps(data_post),
                )
            else:
                req = requests.delete(
                    f'{self.remote_istsos_url}/wa/istsos/services/{service_name}',
                    data=json.dumps(data_post),
                    auth=self.remote_istsos_auth
                )
        else:
            self.logger.info(
                '\t--> Service deleting...'
            )
            service_name = self.config['DEFAULT']['service']
            data_post = {
                "service": f"{service_name}",
            }
            req = requests.delete(
                f'{self.istsos_url}/wa/istsos/services/{service_name}',
                data=json.dumps(data_post),
                auth=self.istsos_auth
            )
        
        if req.status_code == 200:
            check_idx = req.text.find("true")
            if check_idx > 0:

                self.logger.info(
                    f'\t\t--> Service {service_name} deleted'
                )
                return {'success': True}
            else:
                check_idx = req.text.find("already exist")
                check_idx2 = req.text.find("does not exist")
                if check_idx > 0:
                    self.logger.info(
                        f'\t\t--> Service {service_name} deleted'
                    )
                    return {'success': True}
                elif check_idx2 > 0:
                    self.logger.info(
                        f'\t\t--> Service {service_name} does not exist'
                    )
                    return {'success': True}
                else:
                    return {
                        'success': False,
                        'msg': req.text
                    }
        else:
            return {
                'success': False,
                'msg': 'Status code {}'.format(
                    req.status_code
                )
            }

    def delete_cron_jobs(self):
        """
        This function deletes all the jobs configured.
        """
        cron = CronTab(
            user=getpass.getuser()
        )
        removed = False
        for job in cron:
            if __abspath__ in job.command:
                removed = True
                cron.remove(job)
                if '.sh' in job.command:
                    file_sh = job.command.split(' ')[1]
                    os.remove(file_sh)
        cron.write()
        return {'success': True}

    def reset_conf(self):
        """
        This function restore the 'default.cfg' file.
        """
        for section in self.sections:
            self.config.remove_option(
                section, 'assigned_id'
            )
            self.config.remove_option(
                section, 'assignedagg_id'
            )
        self.save_config()
        return {'success': True}

    def clean_data(self):
        """
        This function delete all the data older than the variable
        'max_log_day' set in the 'default.cfg' file.
        TBD
        """
        self.logger.info(
            '--> Clean old data'
        )
        log_days = int(
            self.config['DEFAULT']['max_log_days']
        )
        # req = request.get(
        #     '',
        #     auth=self.istsos_auth
        # )

        self.logger.info(
            '{}'.format(
                self.config['DEFAULT']['max_log_days']
            )
        )
        self.logger.info(
            'The function is still not developed'
        )

    def install(self):
        """
        This function configures all the processes
        to run the monitoring station.
        """
        crt = self.create_service()
        if not crt['success']:
            return crt
        self.logger.info(
            '\t--> Service OK'
        )
        set_sens = self.set_sensors()
        if not set_sens['success']:
            return set_sens
        self.logger.info(
            '\t--> Sensors OK'
        )
        self.set_sampling()
        self.logger.info(
            '\t--> Set sampling configuration'
        )
        self.set_aggregation()
        self.logger.info(
            '\t--> Set aggregation process'
        )
        self.set_send_data()
        self.logger.info(
            '\t--> Set sending process'
        )
        return {'success': True}

    def reset(self):
        """
        This function resets completely all
        the configuration performed.
        """
        del_service = self.delete_service()
        if not del_service['success']:
            return del_service
        del_service_agg = self.delete_service(agg=True)
        if not del_service_agg['success']:
            return del_service_agg
        self.logger.info('\t--> Services DELETED')
        del_cron_jobs = self.delete_cron_jobs()
        if not del_cron_jobs['success']:
            return del_service_agg
        self.logger.info('\t--> Cron jobs and scripts DELETED')
        reset_conf = self.reset_conf()
        if not reset_conf['success']:
            return reset_conf
        self.logger.info('\t--> default.cfg RESTORED')
        return {
            'success': True
        }


def execute(args):
    """
    This function executes the software.
    """
    logger = logzero.logger
    logger.info('********************************')
    logger.info('* START CONFIGURATION SOFTWARE *')
    logger.info('********************************')
    try:
        if args['r']:
            confirm = input(
                (
                    "This operation will delete permanently all the data.\n"
                    "Do you want to continue? (y/n)\n"
                )
            )
            logger.info('### START RESET THE CONFIGURATION')
            if confirm == 'y':
                s = Station()
                logger.info('--> Resetting...')
                reset = s.reset()
                if reset['success']:
                    logger.info(
                        '### END RESET SUCCESSFULLY'
                    )
                else:
                    logger.error(
                        '### END RESET WITH ERRORS: {}'.format(
                            reset['msg']
                        )
                    )
            else:
                logger.info('### operation NOT CONFIRMED')
                logger.info('### EXIT')
        elif args['c']:
            s = Station()
            s.clean_data()
        else:
            s = Station()
            install = s.install()
            if install['success']:
                logger.info(
                    '### END INSTALLATION SUCCESSFULLY'
                )
            else:
                logger.error(
                    '### END INSTALLATION WITH ERRORS: {}'.format(
                        install['msg']
                    )
                )
    except Exception as e:
        logger.error(str(e))
        raise e

# def test_connect():
#     python_path = sys.executable
#     s = Station()
#     s.connect('/dev/serial0', 8, "shared.m2m.ch", debug=True)

#     s.set_mqtt_params(
#         'istsos.ddns.net',
#         1883,
#         0,
#         'simile',
#         'simile'
#     )
#     s.mqtt_publish(
#         'istsos/{}/{}'.format(
#             'test',
#             'asd'
#         ),
#         'asd'
#     )
#     s.mqtt_logout()
#     s.mqtt_login = False

    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Set-up your station'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        dest='v',
        help='Activate verbose debug'
    )

    parser.add_argument(
        '-r', '--reset',
        action='store_true',
        dest='r',
        help='Run a completely reset.'
    )

    parser.add_argument(
        '-c', '--clean',
        action='store_true',
        dest='c',
        help='Remove old data.'
    )

    args = parser.parse_args()
    execute(args.__dict__)
    # test_connect()
