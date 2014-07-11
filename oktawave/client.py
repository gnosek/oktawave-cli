import json
import requests
import datetime
import pprint

from oktawave.exceptions import OktawaveAPIError

def parse_api_error(fault_text):
    import xml.etree.cElementTree as etree
    xmlns = '{http://schemas.datacontract.org/2004/07/K2.CloudsFactory.Common.Communication.Models}'

    resp = etree.fromstring(fault_text)
    error_code = int(resp.find('.//{0}ErrorCode'.format(xmlns)).text)
    error_msg = resp.find('.//{0}ErrorMsg'.format(xmlns)).text
    return error_code, error_msg

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
        if self.debug:
            print '-- request to %s%s --' % (self.url, method)
            pprint.pprint(req)
            print '-- response --'
            pprint.pprint(resp.content)
        if resp.status_code == 500:
            try:
                api_error, api_msg = parse_api_error(resp.content)
            except (AttributeError, ValueError):
                pass
            else:
                raise OktawaveAPIError(api_error, api_msg)
        resp.raise_for_status()
        parsed = json.loads(resp.content)
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
