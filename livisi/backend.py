from livisi.data_wrapper import DataWrapper


class Livisi:
    def __init__(self, username, password, redis_host=None, proxy=None):
        self.wrapper = DataWrapper(username, password, redis_host=redis_host, proxy=proxy)

    def get_messages(self):
        return self.wrapper.get_messages()

    def get_device_information(self, device_id, location_devices=None, capability_states=None):
        if location_devices is None:
            location_devices = self.wrapper.get_devices_by_location()
        if capability_states is None:
            capability_states = self.wrapper.get_capability_states()
        for location_name, location in location_devices.items():
            devices = location['devices']
            for device in devices:
                if device['id'] == device_id:
                    information = {
                        'id': device_id,
                        'name': device['name'],
                        'serial_number': device['serialNumber'],
                    }
                    capabilites = [capability_states[cap_id] for cap_id in device['capabilities']]
                    name_map = {
                        'pointTemperature': 'temperature_set',
                        'temperature': 'temperature_actual',
                        'humidity': 'humidity',
                    }
                    for cap in capabilites:
                        information.update({
                            name_map[key_source]: cap[key_source]['value']
                            for key_source in name_map.keys()
                            if key_source in cap.keys()
                        })

                    return information
        return None

    def get_devices(self, operationMode=None):
        devices_information = {}
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
                            if not operationMode or mode == operationMode:
                                device_data = self.get_device_information(device_id=device['id'],
                                                                          location_devices=location_devices,
                                                                          capability_states=capability_states)
                                device_data.update({
                                    'cap_id': cur_cap_id,
                                    'local_index': local_index,
                                    'mode': mode,
                                })
                                #if mode not in device_states:
                                #    device_states[mode] = {}
                                if location_name not in devices_information: #device_states[mode]:
                                    devices_information[location_name] = []
                                    #device_states[mode][location_name] = []
                                #device_states[mode][location_name].append(device_data)
                                devices_information[location_name].append(device_data)
                local_index += 1
        return devices_information

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
