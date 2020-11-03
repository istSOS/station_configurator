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