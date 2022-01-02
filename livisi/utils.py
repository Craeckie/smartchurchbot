import requests
import json
import re
import random
from urllib import parse
from bs4 import BeautifulSoup


def login(username: str, password: str, proxy: str = None):
    session = requests.session()
    session.proxies.update({
        'http': proxy,
        'https': proxy
    })
    url = 'https://auth.services-smarthome.de/authorize?response_type=code&client_id=35903586&redirect_uri=https%3A%2F%2Fhome.livisi.de%2F%23%2Fauth&scope=&lang=de-DE&state=1065019c-f600-41d4-9037-c65830ad199a'
    res = session.get(url)
    h = BeautifulSoup(res.text, 'html.parser')
    form = h.form
    form_data = {element.attrs['name']: element.attrs.get('value', '') for element in
                 form.find_all('input', {'name': True})}
    form_url = parse.urljoin(url, form.attrs['action'])
    form_data['UserName'] = username
    form_data['Password'] = password

    res = session.post(form_url, data=form_data, allow_redirects=False)
    if res.status_code != 302:
        print(res.text)
        return None
    else:
        redirect_url = res.headers['location']
        return (session, redirect_url)


def get_token(session: requests.Session, redirect_url):
    params = parse.parse_qs(parse.urlparse(redirect_url).fragment.split('?')[1])
    res = session.post('https://auth.services-smarthome.de/token', data={"Code": params['code'][0],
                                                                         "Grant_Type": "authorization_code",
                                                                         "Redirect_Uri": "https://home.livisi.de/#/auth"},
                       auth=('35903586', 'NoSecret'))

    token = res.json()
    auth_header = {'Authorization': f'Bearer {token["access_token"]}'}
    session.headers.update(auth_header)
    return session


def call_function(session: requests.Session, function):
    res = session.get(parse.urljoin('https://api.services-smarthome.de/', function), timeout=40)
    return res.json()


def action(session: requests.Session, target: str, params: dict, type='SetState', id=None):
    if not id:
        id = hex(random.getrandbits(128))[2:]
    data = {
        'id': id,
        "type": type,
        "namespace": "core.RWE",
        "target": target,
        "params": params
    }
    res = session.post('https://api.services-smarthome.de/action', json=data)
    return res
