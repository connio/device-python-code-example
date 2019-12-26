# Copyright (c) 2014-2020 Connio Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
# and associated documentation files (the "Software"), to deal in the Software without restriction, 
# including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, 
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or 
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT 
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# pip install paho-mqtt
# pip install pytz

from mqtthelper import Session
from mqtthelper import CidMap
from mqtthelper import MqttConnInfo
from mqtthelper import DeviceIdentity

import time
import json
import os
from datetime import datetime
import pytz
import sys

config = { 'frequency': 5, 'forever': True  }
deviceId = None

def onConnected(connection):
    connection.subscribe("connio/data/in/devices/{}/#".format(deviceId))
    
def onMsgReceived(property, data):
    print("{} <= {}".format(property, data))
    
def onConfigUpdated(data):
    global config
    config = data

def readAndWrite(connection):    
    # For testing this code, create a device with the following attributes:
    # 
    #  - temperature property numeric type, protected, publish never
    #  - humidity property numeric type, protected, publish never
    #  - config property object type, public, publish always
    #  - setTemperature method, protected, with body for old script engine:
    #
    #     Device.api.setProperty('temperature', {
    #        value: value,
    #        time: new Date().toISOString()
    #     }).then((property) => {
    #        done(null, property.value)
    #     }).catch((error) => {
    #        done(error, null);
    #     });
    #
    # or with body for new script engine
    #
    #     return this.setProperty("temperature", { 
    #       value: value, time: new Date().toISOString()
    #     }).then(prop => prop.value);
    #
    while config.get('forever', True):
      if (sys.version_info > (3, 0)):
        now = datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
      else:
        now = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        
        # See https://docs.connio.com/docs/data-point for different data formats
        # See https://docs.connio.com/reference#using-mqtt-endpoint for writing data over MQTT API
        # See https://docs.connio.com/reference#section-calling-method-using-mqtt-api for calling methods over MQTT API

        # Example 1
        # Write single data point into single device property as value
        # connection.publish("connio/data/out/devices/{}/properties/temperature".format(deviceId), 21.56)

        # Example 2
        # Write multiple data points into single device property as data points
        # Note that only one of the data points with the exact same time will be stored - so making artificial delta
        #
        # if (sys.version_info > (3, 0)):
        #   t2 = (datetime.utcnow() - datetime.timedelta(seconds=2)).replace(tzinfo=datetime.timezone.utc).isoformat()
        # else:
        #   t2 = (datetime.utcnow() - datetime.timedelta(seconds=2)).isoformat() + 'Z'
        #
        # feed = {
        #   'prop': 'temperature',        
        #   'dps': [
        #     { 't': now, 'v': 15.45},
        #     { 't': t2, 'v': 15.48},
        #   ]
        # }
        # data = json.dumps(feed)
        # connection.publish("connio/data/out/devices/{}/json".format(deviceId), data)

        # Example 3        
        # Write multiple data points into multiple device properties as data points
        feed = {
          'dps': [
            { 't': now, 'v': 15.45, 'prop': 'temperature' },
            { 't': now, 'v': 45.2, 'prop': 'humidity'},
          ]
        }
        data = json.dumps(feed)
        connection.publish("connio/data/out/devices/{}/json".format(deviceId), data)

        # Example 4
        # Call a device method over MQTT (you can call multiple methods as well)
        # feed = {'dps': [             
        #     { 'method': 'setTemperature', 'value': 12.4 }
        # ]}
        # data = json.dumps(feed)
        # connection.publish("connio/data/out/devices/{}/methods/json".format(deviceId), data)

        print("@TIME: " + now)
        time.sleep(config.get('frequency', 5))

    print("----Message loop is terminated gracefully - disconnecting from the broker-----")

def connectThruProvisioning(session, host, port, provisioningKeyId, provisioningKeySecret, cidValue, cidType):

    cidMap = CidMap(cidType, cidValue)

    # Provision the device
    # Returns the content of object property called `config` if exists - Expected object schema is { frequency: <int>, forever: <bool>  }
    deviceIdentity = session.provision(MqttConnInfo(
            host = host,
            port = port, 
            username = provisioningKeyId, 
            password = provisioningKeySecret), cidMap, 'config')
    
    # Reconnect with device credentials acquired during provisioning
    mqttConnInfo = MqttConnInfo(
            host = host, 
            port = port,
            clientId = deviceIdentity.id,
            username = deviceIdentity.keyId, 
            password = deviceIdentity.keySecret)
            
    connection = session.connect(mqttConnInfo, onConnected, onMsgReceived, onConfigUpdated)

    # Override global var with acquired device ID 
    global deviceId
    deviceId = deviceIdentity.id

    # Set configuration settings as returned from the platform - if any
    global config
    config = session.config or config

    # Start your data read & write loop
    connection.start_loop(readAndWrite)

def connectWithDeviceCredentials(session, host, port, deviceID, deviceKeyId, deviceKeySecret):
 
    # Override global var with given device ID 
    global deviceId
    deviceId = deviceID    

    mqttConnInfo = MqttConnInfo(
            host = host, 
            port = port,
            clientId = deviceId,
            username = deviceKeyId, 
            password = deviceKeySecret)
    
    connection = session.connect(mqttConnInfo, onConnected, onMsgReceived)

    # Start your data read & write loop
    connection.start_loop(readAndWrite)

if __name__ == '__main__':
    # Default is our test environment - replace with your Connio host
    BROKER_HOST = os.environ.get("CONNIO_BROKER_HOST", "mqtt.connio.cloud")
    BROKER_PORT = 1883

    print("Connecting to " + BROKER_HOST + " via port " + str(BROKER_PORT))

    #
    # OPTION 1: Connecting using device Key
    #
    # Set device credentials
    # See device cheatsheet page on Connio Portal for device credentials
    #
    deviceId = os.environ.get("CONNIO_DEVICE_ID", "<your device id>")
    deviceKeyId = os.environ.get("CONNIO_DEVICE_KEY_ID", "<your device key id>")
    deviceKeySecret = os.environ.get("CONNIO_DEVICE_KEY_SECRET", "<your device key secret>")

    connectWithDeviceCredentials(Session(), BROKER_HOST, BROKER_PORT, deviceId, deviceKeyId, deviceKeySecret)

    #    
    # OPTION 2: Connecting through provisioning mechanism
    #
    # Set provisioning key credentials
    # See https://docs.connio.com/docs/provisioning for provisioning mechanism.
    #
    # provisioningKeyId = os.environ.get("CONNIO_PROVISION_KEY_ID", "<your provisioning key id>")
    # provisioningKeySecret = os.environ.get("CONNIO_PROVISION_KEY_SECRET", "<your provisioning key secret>")
    # cidValue = os.environ.get("CONNIO_DEVICE_SN", "<device serial number>")

    # connectThruProvisioning(Session(), BROKER_HOST, BROKER_PORT, provisioningKeyId, provisioningKeySecret, cidValue, "sn")
        
