import json
import requests
import datetime
import pprint

from oktawave.exceptions import OktawaveAPIError, OktawaveAccessDenied, OktawaveFault

def raise_api_error(fault_text):
    import xml.etree.cElementTree as etree
    ws_xmlns = '{http://schemas.microsoft.com/ws/2005/05/envelope/none}'
    k2_xmlns = '{http://schemas.datacontract.org/2004/07/K2.CloudsFactory.Common.Communication.Models}'

    resp = etree.fromstring(fault_text)
    auth_error = resp.find('.//{0}Detail/{1}AuthorizationErrorDescription'.format(ws_xmlns, k2_xmlns))
    if auth_error:
        error_msg = auth_error.find('.//{0}ErrorMsg'.format(k2_xmlns)).text
        raise OktawaveAccessDenied(error_msg)

    error_code = resp.find('.//{0}ErrorCode'.format(k2_xmlns))
    error_msg = resp.find('.//{0}ErrorMsg'.format(k2_xmlns))
    if error_code is not None and error_msg is not None:
        error_code = int(error_code.text)
        error_msg = error_msg.text
        raise OktawaveAPIError(error_code, error_msg)

    error_msg = resp.find('.//{0}Text'.format(ws_xmlns))
    if error_msg is not None:
        raise OktawaveFault(error_msg.text)


class ApiClient(object):

    def __init__(self, url, username, password, debug=False):
        if not url.endswith('/'):
            url += '/'
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
            raise_api_error(resp.content)
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
