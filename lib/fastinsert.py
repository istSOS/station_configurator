#!/usr/bin/env python
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

import requests

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

def update_data(
    assigned_id, samplingtime, section,
    header, foi, update_val, istsos_url,
    service, config):
  force_insert['AssignedSensorId'] = assigned_id
  force_insert[
      'Observation'
  ][
      'samplingTime'
  ]['beginPosition'] = samplingtime
  force_insert[
      'Observation'
  ][
      'samplingTime'
  ]['endPosition'] = samplingtime
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
  print(req2.status_code)