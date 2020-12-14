#!/usr/bin/python

import configparser
import sys
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
import json
import os
import time
from lib.battery import read_ina219
from lib.lopy import send_data

# external lib
import requests
import yaml
import paho.mqtt.client as mqtt

send_data("ciaociao")
