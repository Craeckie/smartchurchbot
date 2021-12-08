import json

from redis import Redis

from livisi.utils import login, get_token, call_function, action


class DataWrapper:
    def __init__(self, username, password):
        session, redirect_url = login(username, password)
        self.auth_header = get_token(session, redirect_url)
        self.redis = Redis()

    def get_messages(self):
        messages = call_function('message', self.auth_header)
        return messages

    def get_devices(self):
        redis_key = 'devices'
        raw = self.redis.get(redis_key)
        devices = json.loads(raw) if raw else {}
        if not devices:
            data = call_function('device', self.auth_header)
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
                        'location': item['location'][len('/location/'):],
                        'raw': item
                    }
            self.redis.set(redis_key, json.dumps(devices), ex=3600)
        return devices

    def get_locations(self):
        redis_key = 'locations'
        raw = self.redis.get(redis_key)
        locations = json.loads(raw) if raw else {}
        if not locations:
            data = call_function('location', self.auth_header)
            for item in data:
                name = item['config']['name']
                locations[name] = {
                    'id': item['id']
                }
        self.redis.set(redis_key, json.dumps(locations), ex=24 * 3600)
        return locations

    def get_capability_states(self):
        redis_key = 'capability_states'
        raw = self.redis.get(redis_key)
        capability_states = json.loads(raw) if raw else {}
        if not capability_states:
            data = call_function('capability/states', self.auth_header)
            for item in data:
                item_id = item['id']
                capability_states[item_id] = item['state']
            self.redis.set(redis_key, json.dumps(capability_states), ex=15)
        return capability_states

    def get_devices_by_location(self):
        locations = self.get_locations()
        devices = self.get_devices()
        location_devices = {}
        for location_name, location in locations.items():
            location_devices[location_name] = {
                'id': location['id'],
                'devices': [],
            }
            for device_name, device in devices.items():
                device_location = device['location']
                if device_location == location['id']:
                    location_devices[location_name]['devices'].append(device)
        return location_devices

    def action(self, target, params):
        res = action(self.auth_header, target=target, params=params)
        data = res.json()
        return data
