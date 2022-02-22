import requests
import json
import re
import random
from urllib import parse
from bs4 import BeautifulSoup


class APIWrapper:
    def __init__(self):
        self.session = None
        self.redirect_url = None

    def login(self, username: str, password: str, proxy: str = None):
        self.session = requests.session()
        self.session.proxies.update({
            'http': proxy,
            'https': proxy
        })
        url = 'https://auth.services-smarthome.de/authorize?response_type=code&client_id=35903586&redirect_uri=https%3A%2F%2Fhome.livisi.de%2F%23%2Fauth&scope=&lang=de-DE&state=1065019c-f600-41d4-9037-c65830ad199a'
        res = self.session.get(url)
        h = BeautifulSoup(res.text, 'html.parser')
        form = h.form
        form_data = {element.attrs['name']: element.attrs.get('value', '') for element in
                     form.find_all('input', {'name': True})}
        form_url = parse.urljoin(url, form.attrs['action'])
        form_data['UserName'] = username
        form_data['Password'] = password

        res = self.session.post(form_url, data=form_data, allow_redirects=False)
        if res.status_code != 302:
            print(res.text)
            return False
        else:
            self.redirect_url = res.headers['location']
            return True

    def refresh_token(self):
        params = parse.parse_qs(parse.urlparse(self.redirect_url).fragment.split('?')[1])
        res = self.session.post('https://auth.services-smarthome.de/token', data={"Code": params['code'][0],
                                                                             "Grant_Type": "authorization_code",
                                                                             "Redirect_Uri": "https://home.livisi.de/#/auth"},
                           auth=('35903586', 'NoSecret'))

        token = res.json()
        auth_header = {'Authorization': f'Bearer {token["access_token"]}'}
        self.session.headers.update(auth_header)

    def call_function(self, function):
        url = parse.urljoin('https://api.services-smarthome.de/', function)
        res = self.session.get(url, timeout=40)
        data = res.json()
        if 'errorcode' in data and data['errorcode'] == 2007:
            self.refresh_token()
            res = self.session.get(url, timeout=40)
        data = res.json()
        return data

    def action(self, target: str, params: dict, type='SetState', id=None):
        if not id:
            id = hex(random.getrandbits(128))[2:]
        data = {
            'id': id,
            "type": type,
            "namespace": "core.RWE",
            "target": target,
            "params": params
        }
        res = self.session.post('https://api.services-smarthome.de/action', json=data)
        return res
