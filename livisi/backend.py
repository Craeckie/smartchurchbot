from livisi.data_wrapper import DataWrapper
from livisi.utils import action


class Livisi:
    def __init__(self, username, password, redis_host=None, proxy=None):
        self.wrapper = DataWrapper(username, password, redis_host=redis_host, proxy=proxy)

    def get_messages(self):
        return self.wrapper.get_messages()

    def get_device_states(self):
        device_states = {}
        location_devices = self.wrapper.get_devices_by_location()
        capability_states = self.wrapper.get_capability_states()
        local_index = 0
        for location_name, location in location_devices.items():
            devices = location['devices']
            for device in devices:
                for cur_cap_id, state in capability_states.items():
                    if cur_cap_id in device['capabilities']:
                        if 'operationMode' in state:
                            mode = state['operationMode']['value']
                            device_data = {
                                'name': device['name'],
                                'cap_id': cur_cap_id,
                                'local_index': local_index,
                            }
                            if mode not in device_states:
                                device_states[mode] = {}
                            if location_name not in device_states[mode]:
                                device_states[mode][location_name] = []
                            device_states[mode][location_name].append(device_data)
                local_index += 1
        return device_states

    def change_device_state(self, local_index, state='Auto'):
        device_states = self.get_device_states()
        cap_id = None
        for mode, location_data in device_states.items():
            for location_name, devices in location_data.items():
                for device in devices:
                    if device['local_index'] == local_index:
                        cap_id = device['cap_id']
                        break
        res = self.wrapper.action(target=f'/capability/{cap_id}',
                            params={"operationMode": {"type": "Constant", "value": state}})

        return 'resultCode' in res and res['resultCode'] == 'Success'
