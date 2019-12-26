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

import paho.mqtt.client as mqtt
from paho.mqtt.client import connack_string
from paho.mqtt.client import MQTTv311

import json
import random
import sys
from threading import Timer

class CidMap:
    def __init__(self, typ, id):
        self.type = typ
        self.id = id

class DeviceIdentity:
    def __init__(self, id, keyId, keySecret):
        self.id = id
        self.keyId = keyId
        self.keySecret = keySecret       

class MqttConnInfo:
    def __init__(self, host, username, password, clientId = "_???_" + str(random.randint(11111111,99999999)), port = 8883):
        self.host = host
        self.port = port
        self.clientId = clientId
        self.username = username
        self.password = password

class Session(object):
    class Connection:
        def __init__(self, client):
            self._client = client
        
        def publish(self, topic, data, qos=0, retain=False):
            return self._client.publish(topic, data, qos, retain)

        def subscribe(self, topic, qos=0):
            return self._client.subscribe(topic, qos)

        def unsubscribe(self, topic):
            self._client.unsubscribe(topic)

        def start_loop(self, loopingFn):
            self._client.loop_start()
            loopingFn(self)
            self._client.loop_stop()

        def client(self):
            return self._client


    def __init__(self):
        self._timer = None
        self.configPropertyName = None

    def _provisionTimedout(self):
        print("Provisioning timed out! See https://docs.connio.com/docs/provisioning for details.")
        
    def provision(self, mqttConnInfo, cidMap, cfgPropName=None, timeout=10, keepAlive = 60):
        self.timer = Timer(timeout, self._provisionTimedout)
        self.timer.start()

        self.configPropertyName = cfgPropName

        # The callback for when the client receives a CONNACK response from the server.
        def on_connect(client, userdata, flags, rc):
            print("MQTT Broker returned connection result: " + connack_string(rc))
            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.            
            client.subscribe("connio/provisions/{}".format(mqttConnInfo.clientId))

        def on_disconnect(client, userdata, rc):            
            client.loop_stop()

        # The callback for when a PUBLISH message is received from the server.
        def on_message(client, userdata, msg):
            self.timer.cancel()           
            client.disconnect()

            if (sys.version_info > (3, 0)):
                response = json.loads(str(msg.payload, 'utf-8'))
            else:
                response = json.loads(str(msg.payload))

            self.deviceId = response.get('deviceId')
            self.deviceKeyId = response.get('apiKeyId')
            self.deviceKeySecret = response.get('apiSecret')
            self.config = response.get(cfgPropName)

            print("Device provisioning is complete")

        def on_subscribe(client, userdata, mid, granted_qos):
            payload = json.dumps({cidMap.type: cidMap.id, 'configProperty': cfgPropName})   
            client.publish("connio/provisions", payload)

        def on_publish(client, userdata, mid):
            pass

        client = mqtt.Client(client_id=mqttConnInfo.clientId, clean_session=True, userdata=None, protocol=MQTTv311)

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.on_subscribe = on_subscribe
        client.on_publish = on_publish

        client.username_pw_set(username=mqttConnInfo.username, password=mqttConnInfo.password)
        client.connect_async(mqttConnInfo.host, mqttConnInfo.port, keepAlive)

        client.loop_forever()
        return DeviceIdentity(self.deviceId, self.deviceKeyId, self.deviceKeySecret)

    def connect(self, mqttConnInfo, onConnected, onMessageReceived, onConfigUpdated=None, onPublish=None, onSubscribed=None, keepAlive=30):        
        def on_connect(client, connection, flags, rc):       
            onConnected(connection)

        def on_disconnect(client, connection, rc):
            print("Connection with the broker is lost: " + connack_string(rc))

        def on_message(client, connection, msg):
            if (sys.version_info > (3, 0)):
                data = json.loads(str(msg.payload, "utf-8"))
            else:
                data = json.loads(str(msg.payload))
            
            prop = str(msg.topic).split('/')[-1]
            if (self.configPropertyName is not None and prop == self.configPropertyName and onConfigUpdated is not None):
                onConfigUpdated(data)
            else:
                onMessageReceived(str(msg.topic), data)

        def on_subscribe(client, connection, mid, granted_qos):
            if onSubscribed:
                onSubscribed(connection, mid, granted_qos)
            else:
                pass

        def on_publish(client, connection, mid):
            if onPublish:
                onPublish(connection, mid)
            else:
                pass

        client = mqtt.Client(client_id=mqttConnInfo.clientId, clean_session=True, userdata=self, protocol=MQTTv311)
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.on_subscribe = on_subscribe
        client.on_publish = on_publish

        client.username_pw_set(username=mqttConnInfo.username, password=mqttConnInfo.password)
        client.connect_async(mqttConnInfo.host, mqttConnInfo.port, keepAlive)

        connection = self.Connection(client)
        client.user_data_set(connection)

        return connection