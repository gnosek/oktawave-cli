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
        self.client.options.headers.update(**{'Content-Type':
                 'application/soap+xml; charset=utf-8'})
        self.hc = headersCreator
        self.debug = debug

    def call(self, soap_method, *args):
        method = getattr(self.client.service, soap_method)
        self.client.set_options(soapheaders=self.hc(soap_method))
        res = method(*args)
        if self.debug:
            print res
        return res

    def create(self, obj_type, *args):
        return self.client.factory.create(obj_type, *args)  # TODO: try to resolve namespace prefix based on wsdl

    def __str__(self):
        return str(self.client)
