import json

from redis import Redis

from .api_wrapper import APIWrapper


class DataWrapper:
    def __init__(self, username, password, redis_host='localhost', proxy=None):
        self.api = APIWrapper(username, password, proxy)
        self.api.login()
        self.redis = Redis(redis_host)

    def get_messages(self):
        data = self.api.call_function('message')
        try:
            messages = {}
            for entry in data:
                if 'properties' in entry:
                    properties = entry['properties']
                    device_name = None
                    if 'deviceName' in properties:
                        device_name = properties['deviceName']
                    elif 'deviceGroup' in properties:
                        device_name = properties['deviceGroup']
                else:
                    device_name = entry['type']

                if device_name and device_name in messages:
                    messages[device_name].append(entry)
                else:
                    messages[device_name] = [entry]
        except Exception as e:
            raise ValueError(f"Received data is invalid: {json.dumps(data)}") from e
        return messages

    def get_devices(self):
        redis_key = 'devices'
        raw = self.redis.get(redis_key)
        devices = json.loads(raw) if raw else {}
        if not devices:
            data = self.api.call_function('device')
            try:
                for item in data:
                    if item['type'] == 'RST':
                        config = item['config']
                        name = config['name']
                        devices[name] = {
                            'id': item['id'],
                            'name': name,
                            'type': item['type'],
                            'serialNumber': item['serialNumber'],
                            'capabilities': [cap_path[len('/capability/'):] for cap_path in item['capabilities']],
                            'location': item['location'][len('/location/'):] if 'location' in item else 'N/A',
                            'raw': item
                        }
                self.redis.set(redis_key, json.dumps(devices), ex=30)
            except Exception as e:
                raise ValueError(f"Received data is invalid: {json.dumps(data)}") from e
        return devices

    def get_locations(self):
        redis_key = 'locations'
        raw = self.redis.get(redis_key)
        locations = json.loads(raw) if raw else {}
        if not locations:
            data = self.api.call_function('location')
            try:
                for item in data:
                    name = item['config']['name']
                    locations[name] = {
                        'id': item['id']
                    }
            except Exception as e:
                raise ValueError(f"Received data is invalid: {json.dumps(data)}") from e

        self.redis.set(redis_key, json.dumps(locations), ex=24 * 3600)
        return locations

    def get_capability_states(self):
        redis_key = 'capability_states'
        raw = self.redis.get(redis_key)
        capability_states = json.loads(raw) if raw else {}
        if not capability_states:
            data = self.api.call_function('capability/states')
            try:
                for item in data:
                    item_id = item['id']
                    capability_states[item_id] = item['state']
                self.redis.set(redis_key, json.dumps(capability_states), ex=14)
            except Exception as e:
                raise ValueError(f"Received data is invalid: {json.dumps(data)}") from e
        return capability_states

    def get_devices_by_location(self):
        locations = self.get_locations()
        devices = self.get_devices()
        location_devices = {}
        for location_name, location in sorted(locations.items()):
            location_devices[location_name] = {
                'id': location['id'],
                'devices': [],
            }
            for device_name, device in sorted(devices.items()):
                device_location = device['location']
                if device_location == location['id']:
                    location_devices[location_name]['devices'].append(device)
        return location_devices

    def action(self, target, params):
        res = self.api.action(target=target, params=params)
        data = res.json()
        return data


