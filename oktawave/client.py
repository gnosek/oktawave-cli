from suds.client import Client
from suds.xsd.doctor import Import, ImportDoctor
import suds
import sys

# wrapper over suds.Client


class ApiClient:

    def __init__(self, wsdl, username, password, headersCreator=lambda: [], doctors=[], debug=False):
        schema_imports = [Import(path) for path in doctors]
        schema_doctor = ImportDoctor(*schema_imports)
        self.client = Client(username='API\\' + username,
                             password=password, url=wsdl, doctor=schema_doctor)
        self.hc = headersCreator
        self.debug = debug

    def call(self, soap_method, *args):
        method = getattr(self.client.service, soap_method)
        self.client.set_options(soapheaders=self.hc(soap_method))
        try:
            res = method(*args)
        except suds.WebFault as detail:
            print "ERROR: " + detail.fault.Reason.Text
            if hasattr(detail.fault, 'Detail'):
                for attr in [x for x in dir(detail.fault.Detail) if x[0] != '_']:
                    attr_value = getattr(detail.fault.Detail, attr)
                    if hasattr(attr_value, 'ErrorMsg'):
                        print "Details: " + attr_value.ErrorMsg
            sys.exit(1)
        if self.debug:
            print res
        return res

    def create(self, obj_type, *args):
        return self.client.factory.create(obj_type, *args)  # TODO: try to resolve namespace prefix based on wsdl

    def __str__(self):
        return str(self.client)
