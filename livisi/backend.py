import time

from livisi.data_wrapper import DataWrapper

from .config import Config

class Livisi:
    def __init__(self, config: Config):
        self.wrapper = DataWrapper(config)

    def get_messages(self, byType=False):
        return self.wrapper.get_messages(byType=byType)

    def get_device_information(self, device_id, location_devices=None, capabilities=None, capability_states=None):
        if location_devices is None:
            location_devices = self.wrapper.get_devices_by_location()
        if capability_states is None:
            capability_states = self.wrapper.get_capability_states()
        if capabilities is None:
            capabilities = self.wrapper.get_capabilities()
        for location_name, location in location_devices.items():
            devices = location['devices']
            for device in devices:
                if device['id'] == device_id:
                    information = {
                        'id': device_id,
                        'name': device['name'],
                        'serial_number': device['serialNumber'],
                    }
                    cur_states = [capability_states[cap_id] for cap_id in device['capabilities']]
                    cur_capabilities = [capabilities[cap_id] for cap_id in device['capabilities']]
                    name_map = {
                        'pointTemperature': 'temperature_set',
                        'temperature': 'temperature_actual',
                        'humidity': 'humidity',
                        'maxTemperature': 'temperature_max',
                        'minTemperature': 'temperature_min',
                    }
                    for cap in cur_states + cur_capabilities:
                        information.update({
                            name_map[key_source]: cap[key_source]['value'] if type(cap[key_source]) is dict else cap[
                                key_source]
                            for key_source in name_map.keys()
                            if key_source in cap.keys()
                        })

                    return information
        return None

    def get_devices(self, operationMode=None, minActualTemp=None):
        devices_information = {}
        location_devices = self.wrapper.get_devices_by_location()
        capability_states = self.wrapper.get_capability_states()
        capabilities = self.wrapper.get_capabilities()
        local_index = 0
        for location_name, location in location_devices.items():
            devices = location['devices']
            for device in devices:
                if device['type'] != 'RST':
                    continue
                minmax_cap_id = None
                operation_cap, operation_cap_id = None, None

                for cur_cap_id in device['capabilities']:
                    if cur_cap_id in capabilities.keys():
                        cap = capabilities[cur_cap_id]
                        if 'maxTemperature' in cap and 'minTemperature' in cap:
                            minmax_cap_id = cur_cap_id
                            # minmaxtemp_capability = capabilities[cur_cap_id]
                    if cur_cap_id in capability_states.keys() and 'operationMode' in capability_states[cur_cap_id]:
                        operation_cap = capability_states[cur_cap_id]
                        operation_cap_id = cur_cap_id

                if not operation_cap:
                    continue

                mode = operation_cap['operationMode']['value']
                if operationMode and mode != operationMode:
                    continue
                device_data = self.get_device_information(device_id=device['id'],
                                                          location_devices=location_devices,
                                                          capabilities=capabilities,
                                                          capability_states=capability_states)
                if minActualTemp and float(device_data['temperature_actual']) < minActualTemp:
                    continue

                device_data.update({
                    'operation_cap_id': operation_cap_id,
                    'minmax_cap_id': minmax_cap_id,
                    'local_index': local_index,
                    'mode': mode,
                })
                # if mode not in device_states:
                #    device_states[mode] = {}
                if location_name not in devices_information:  # device_states[mode]:
                    devices_information[location_name] = []
                    # device_states[mode][location_name] = []
                # device_states[mode][location_name].append(device_data)
                devices_information[location_name].append(device_data)
                local_index += 1
        return devices_information

    def change_device_state(self, local_index, state='Auto'):
        devices_by_location = self.get_devices()
        op_cap_id = None
        for location_name, devices in devices_by_location.items():
            for device in devices:
                if device['local_index'] == local_index:
                    cap_id = device['operation_cap_id']
                    break
        res = self.wrapper.action(target=f'/capability/{cap_id}',
                                  params={"operationMode": {"type": "Constant", "value": state}})

        return 'resultCode' in res and res['resultCode'] == 'Success'

    def change_devices_max_temperature(self, temperature):
        devices_by_location = self.get_devices()
        count = 0
        for location_name, devices in devices_by_location.items():
            for device in devices:
                cap_id = device['minmax_cap_id']
                device_id = device['id']
                data = \
                    {
                        "config":
                            {
                                "name": "Target Temperature",
                                "activityLogActive": True,
                                "VRCCSetPoint": "PointTemperature",
                                "maxTemperature": temperature,
                                "minTemperature": 6,
                                "childLock": False,
                                "windowOpenTemperature": 6
                            },
                        "id": cap_id,
                        "device": f"/device/{device_id}",
                        "type": "ThermostatActuator"
                    }

                success = self.wrapper.configure(target=f'/capability/{cap_id}',
                                             data=data)
                if not success:
                    return 0
                else:
                    count += 1
                time.sleep(2)

        return count
