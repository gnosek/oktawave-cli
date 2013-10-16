import json
import requests
import datetime
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
        self.debug = debug

    def call(self, method, **kwargs):
        req = kwargs
        resp = self.session.post(self.url + method, data=json.dumps(req))
        if resp.status_code != 200:
            pprint.pprint(req)
            pprint.pprint(resp.content)
        resp.raise_for_status()
        parsed = resp.json()
        if self.debug:
            pprint.pprint(parsed)
        if len(parsed) == 1:
            return parsed.values().pop()
        return parsed

    def parse_date(self, value):
        assert value.startswith('/Date(')
        plus = value.index('+')
        timestamp = int(value[len('/Date('):plus]) / 1000
        tz_hour = int(value[plus+1:plus+3])
        tz_min = int(value[plus+3:plus+5])

        timestamp += 3600 * tz_hour + 60 * tz_min
        return datetime.datetime.fromtimestamp(timestamp)
