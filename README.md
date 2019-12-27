# Connio Device Code Sample in Python
Example python code showing how to connect Connio from edge devices.

## Installation

Download the code from github, and install dependencies using pip, a package manager for Python.

`pip install paho-mqtt`

`pip install pytz`

## Access Credentials

In order to use the code, you need to set the following environment variables with your accounts values:

### Host

```
BROKER_HOST
BROKER_PORT
```

### Option 1: Access using device credentials
```
CONNIO_DEVICE_ID
CONNIO_DEVICE_KEY_ID
CONNIO_DEVICE_KEY_SECRET
```
### Option 2: Access using provisioning mechanism

```
CONNIO_PROVISION_KEY_ID
CONNIO_PROVISION_KEY_SECRET
CONNIO_DEVICE_SN
```

## Documentation

The documentation for this sample can be found [here](https://docs.connio.com/docs/device-code-example).
