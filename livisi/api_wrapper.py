import logging
import time

import requests
from requests.auth import HTTPBasicAuth
import random
from urllib import parse
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from .config import Config

class APIWrapper:
    def __init__(self, config: Config):
        self.config = config
        self.session = None
        self.redirect_url = None

    def login(self) -> bool:
        self.session = requests.session()
        if self.config.proxy:
            self.session.proxies.update({
                'http': self.config.proxy,
                'https': self.config.proxy
            })
        retries = Retry(total=5,
                             backoff_factor=0.1,
                             status_forcelist=[500, 502, 503, 504])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        
        # If using Livisi Cloud:
        #res = self.session.get(self.config.login_url)
        #h = BeautifulSoup(res.text, 'html.parser')
        #form = h.form
        #form_data = {element.attrs['name']: element.attrs.get('value', '') for element in
        #             form.find_all('input', {'name': True})}
        #form_url = parse.urljoin(self.config.login_url, form.attrs['action'])
        #form_data['UserName'] = self.config.username
        #form_data['Password'] = self.config.password

        #res = self.session.post(self.config.login_url, json=form_data, allow_redirects=False)
        #if res.status_code != 302:
        #    print(res.text)
        #    return False
        #else:
        #    self.redirect_url = res.headers['location']

        return self.refresh_token()

    def refresh_token(self) -> bool:
        #query = parse.urlparse(self.redirect_url)
        #params = parse.parse_qs(fragment.split('?')[1])
        #basic_auth = HTTPBasicAuth('clientId', 'clientPass')
        headers = {
            "Authorization": "Basic Y2xpZW50SWQ6Y2xpZW50UGFzcw==",
            "Content-type": "application/json",
            "Accept": "application/json",
        }
        res = self.session.post(self.config.login_url, # http://IP:8080/auth/token
                                json={"username": self.config.username,
                                      "password": self.config.password,
                                      "grant_type": "password"},
                                headers=headers)
        #res = self.session.post('https://auth.services-smarthome.de/token', data={"Code": params['code'][0],
        #                                                                          "Grant_Type": "authorization_code",
        #                                                                          "Redirect_Uri": "https://home.livisi.de/#/auth"},
        #                        auth=('35903586', 'NoSecret'))

        data = res.json()
        logging.info(data)
        try:
            auth_header = {'Authorization': f'Bearer {data["access_token"]}'}
            self.session.headers.update(auth_header)
            return True
        except KeyError as e:
            logging.error(data)
            raise ValueError(f"Got an unexpected response:\n{data}") from e

    def call_function(self, function):
        url = parse.urljoin(self.config.base_url, function)
        res = self.session.get(url, timeout=15)
        data = res.json()
        if 'errorcode' in data and data['errorcode'] == 2007:
            if self.login():
                res = self.session.get(url, timeout=15)
                data = res.json()
            else:
                data = {'msg': 'Login failed!'}

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

    def configure(self, target: str, data: dict):
        tries = 0
        backoff_time = 3
        max_tries = 5
        while tries < max_tries:
            res = self.session.put(f'https://api.services-smarthome.de{target}', json=data)
            if res.status_code == 200:
                return True
            elif res.status_code == 409:
                tries += 1
                print(f'Request got rate limited, try: {tries}, backoff: {backoff_time}s')
                time.sleep(backoff_time)
                backoff_time *= 2
            else:
                return False
        return False
