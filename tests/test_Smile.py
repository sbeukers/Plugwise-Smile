"""Plugwise Home Assistant module."""

import time
import pytest
import pytest_asyncio
import pytest_aiohttp

import asyncio
import aiohttp
import os

from lxml import etree

from Plugwise_Smile.Smile import Smile

# Prepare aiohttp app routes
# taking smile_type (i.e. directory name under tests/{smile_app}/
# as inclusion point
async def setup_app():
    global smile_type
    if not smile_type:
        return False
    app = aiohttp.web.Application()
    app.router.add_get('/core/appliances',smile_appliances)
    app.router.add_get('/core/direct_objects',smile_direct_objects)
    app.router.add_get('/core/domain_objects',smile_domain_objects)
    app.router.add_get('/core/locations',smile_locations)
    app.router.add_get('/core/modules',smile_modules)
    return app

# Wrapper for appliances uri
async def smile_appliances(request):
    global smile_type
    f=open('tests/{}/core.appliances.xml'.format(smile_type),'r')
    data=f.read()
    f.close()
    return aiohttp.web.Response(text=data)

async def smile_direct_objects(request):
    global smile_type
    f=open('tests/{}/core.direct_objects.xml'.format(smile_type),'r')
    data=f.read()
    f.close()
    return aiohttp.web.Response(text=data)

async def smile_domain_objects(request):
    global smile_type
    f=open('tests/{}/core.domain_objects.xml'.format(smile_type),'r')
    data=f.read()
    f.close()
    return aiohttp.web.Response(text=data)

async def smile_locations(request):
    global smile_type
    f=open('tests/{}/core.locations.xml'.format(smile_type),'r')
    data=f.read()
    f.close()
    return aiohttp.web.Response(text=data)

async def smile_modules(request):
    global smile_type
    f=open('tests/{}/core.modules.xml'.format(smile_type),'r')
    data=f.read()
    f.close()
    return aiohttp.web.Response(text=data)

# Test if at least modules functions before going further
# note that this only tests the modules-app for functionality
# if this fails, none of the actual tests against the Smile library
# will function correctly
async def test_mock(aiohttp_client, loop):
    global smile_type
    smile_type = 'anna_without_boiler'
    app = aiohttp.web.Application()
    app.router.add_get('/core/modules',smile_modules)
    client = await aiohttp_client(app)
    resp = await client.get('/core/modules')
    assert resp.status == 200
    text = await resp.text()
    assert 'xml' in text

# Generic connect
@pytest.mark.asyncio
async def connect():
    global smile_type
    if not smile_type:
        return False
    port =  aiohttp.test_utils.unused_port()

    app = await setup_app()

    server = aiohttp.test_utils.TestServer(app,port=port,scheme='http',host='127.0.0.1')
    await server.start_server()

    client = aiohttp.test_utils.TestClient(server)
    websession = client.session

    url = '{}://{}:{}/core/modules'.format(server.scheme,server.host,server.port)
    resp = await websession.get(url)
    assert resp.status == 200
    text = await resp.text()
    assert 'xml' in text
    assert '<vendor_name>Plugwise</vendor_name>' in text

    smile = Smile( host=server.host, password='abcdefgh', port=server.port, websession=websession)
    assert smile._timeout == 20
    assert smile._domain_objects == None

    """Connect to the smile"""
    connection = await smile.connect()
    assert connection == True
    return server,smile,client


# GEneric list_devices
@pytest.mark.asyncio
async def list_devices(server,smile):
    device_list={}
    devices = smile.get_devices()
    for dev in devices:
        if dev['name'] == 'Controlled Device':
            ctrl_id = dev['id']
        else:
            device_list[dev['id']]={'name': dev['name'], 'ctrl': ctrl_id}
    #print(device_list)
    return device_list


# Generic disconnect
@pytest.mark.asyncio
async def disconnect(server,client):
    if not server:
        return False
    await server.close()
    await client.session.close()

# Actual test for directory 'Anna' without a boiler
@pytest.mark.asyncio
async def test_connect_anna_without_boiler():
    # testdata is a dictionary with key ctrl_id_dev_id => keys:values
    #testdata={ 'ctrl_id:dev_id': { 'type': 'thermostat', 'battery': None }
    testdata={
        "c46b4794d28149699eacf053deedd003_c34c6864216446528e95d88985e714cc": {
                'type': 'thermostat',
                'setpoint_temp': 16.0,
                'current_temp': 20.62,
                'selected_schedule': 'Normal',
                'boiler_state': None,
                'battery': None,
            }
        }
    global smile_type
    smile_type = 'anna_without_boiler'
    server,smile,client = await connect()
    device_list = await list_devices(server,smile)
    #print(device_list)
    for dev_id,details in device_list.items():
        data = smile.get_device_data(dev_id, details['ctrl'])
        test_id = '{}_{}'.format(details['ctrl'],dev_id)
        assert test_id in testdata
        for testkey in testdata[test_id]:
            print('Asserting {}'.format(testkey))
            assert data[testkey] == testdata[test_id][testkey]

    out_temp = smile.get_outdoor_temperature()
    print('Asserting outdoor temperature')
    assert float(out_temp) == 10.8      # Actual value
    illuminance = smile.get_illuminance()
    print('Asserting illuminance')
    assert float(illuminance) == 35.0   # Actual value

    await disconnect(server,client)

# Actual test for directory 'Adam'
# living room floor radiator valve and separate zone thermostat
# an three rooms with conventional radiators
@pytest.mark.asyncio
async def test_connect_adam():
    global smile_type
    smile_type = 'adam_living_floor_plus_3_rooms'
    server,smile,client = await connect()
    device_list = await list_devices(server,smile)
    print(device_list)
    #testdata dictionary with key ctrl_id_dev_id => keys:values
    testdata={}
    for dev_id,details in device_list.items():
        data = smile.get_device_data(dev_id, details['ctrl'])
        test_id = '{}_{}'.format(details['ctrl'],dev_id)
        #assert test_id in testdata
        print(data)
    await disconnect(server,client)

# Actual test for directory 'Adam + Anna'
@pytest.mark.asyncio
async def test_connect_adam_plus_anna():
    #testdata dictionary with key ctrl_id_dev_id => keys:values
    testdata={
        '2743216f626f43948deec1f7ab3b3d70_009490cc2f674ce6b576863fbb64f867': {
                'type': 'thermostat',
                'setpoint_temp': 20.5,
                'current_temp': 20.55,
                'active_preset': 'home',
                'selected_schedule': 'Weekschema',
                'boiler_state': None,
                'battery': None,
                'dhw_state': False,
            }
        }
    global smile_type
    smile_type = 'adam_plus_anna'
    server,smile,client = await connect()
    device_list = await list_devices(server,smile)
    #print(device_list)
    for dev_id,details in device_list.items():
        data = smile.get_device_data(dev_id, details['ctrl'])
        test_id = '{}_{}'.format(details['ctrl'],dev_id)
        #assert test_id in testdata
        for testkey in testdata[test_id]:
            print('Asserting {}'.format(testkey))
            assert data[testkey] == testdata[test_id][testkey]

    out_temp = smile.get_outdoor_temperature()
    print('Asserting outdoor temperature')
    assert float(out_temp) == 12.4      # Actual value
    illuminance = smile.get_illuminance()
    print('Asserting illuminance (none)')
    assert illuminance == None   # Adam has no illuminance
    await disconnect(server,client)
