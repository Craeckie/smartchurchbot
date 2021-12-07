from livisi.utils import login, call_function, get_token


class Livisi:
    def __init__(self, username, password):
        session, redirect_url = login(username, password)
        self.auth_header = get_token(session, redirect_url)

    def get_messages(self):
        messages = call_function('message', self.auth_header)
        return messages

    def get_device_states(self):
        device_states = {}
        devices = call_function('device', self.auth_header)
        capability_states = call_function('capability/states', self.auth_header)
        for device in devices:
            if device['type'] == 'RST':
                name = device['config']['name']
                # print(f"{device['id']}: {name}")
                state = None
                dev_cap_ids = [cap_path[len('/capability/'):] for cap_path in device['capabilities']]
                # print(dev_cap_ids)
                for cur_state in capability_states:
                    cur_cap_id = cur_state['id']
                    if cur_cap_id in dev_cap_ids:
                        state = cur_state['state']
                        if 'operationMode' in state:
                            mode = state['operationMode']['value']
                            device_data = {
                                'name': name,
                                'cap_id': cur_cap_id
                            }
                            if mode in device_states:
                                device_states[mode].append(device_data)
                            else:
                                device_states[mode] = [device_data]
                            # print(f"  {cur_state['id']}: {}")
        return device_states
