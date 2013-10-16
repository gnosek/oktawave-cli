import json
import requests
import pprint

class ApiClient(object):

    def __init__(self, url, username, password, debug=False):
        if not url.endswith('/'):
            url = url + '/'
        self.url = url
        session = requests.session()
        session.auth = ('API\\' + username, password)
        session.headers.update(**{'Content-Type': 'text/json'})
        self.session = session
        self.debug = debug or True

    def call(self, method, **kwargs):
        req = kwargs
        resp = self.session.post(self.url + method, data=json.dumps(req))
        resp.raise_for_status()
        parsed = resp.json()
        if self.debug:
            pprint.pprint(parsed)
        if len(parsed) == 1:
            return parsed.values().pop()
        return parsed
