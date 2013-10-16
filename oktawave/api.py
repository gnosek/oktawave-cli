from client import ApiClient
from exceptions import *
from suds.sax.element import Element
import sys
import suds
try:
    from swiftclient import Connection
except ImportError:
    from swift.common.client import Connection
import itertools


# Patching some stuff in suds to get it working with SOAP 1.2
suds.bindings.binding.envns = (
    'SOAP-ENV', 'http://www.w3.org/2003/05/soap-envelope')


# WSDL addresses
wsdl_common = 'https://api.oktawave.com/CommonService.svc?wsdl'
wsdl_clients = 'https://api.oktawave.com/ClientsService.svc?wsdl'

# Fixing WSDL to work with suds
ans = ('a', 'http://www.w3.org/2005/08/addressing')

# JSON API endpoints
jsonapi_common = 'https://api.oktawave.com/CommonService.svc/json'
jsonapi_clients = 'https://api.oktawave.com/ClientsService.svc/json'

def header(key, value, namespace=ans):
    return Element(key, ns=namespace).setText(value)


def hc_common(method):
    return [
        header('Action', 'http://K2.CloudsFactory/ICommon/' + method),
        header('To', 'https://adamm.cloud.local:450/CommonService.svc')
    ]


def hc_clients(method):
    return [
        header('Action', 'http://K2.CloudsFactory/IClients/' + method),
        header('To', 'https://adamm.cloud.local:450/ClientsService.svc')
    ]

docs_common = [
    'http://schemas.datacontract.org/2004/07/K2.CloudsFactory.Common',
    'http://schemas.microsoft.com/2003/10/Serialization/'
]
docs_clients = [
    'http://schemas.microsoft.com/2003/10/Serialization/',
    'http://schemas.microsoft.com/2003/10/Serialization/Arrays',
    'http://schemas.datacontract.org/2004/07/K2.CloudsFactory.Common',
    'http://schemas.datacontract.org/2004/07/K2.CloudsFactory.Common.Models'
]

DICT = {
    'DB_VM_CATEGORY': 324,
    'MYSQL_TEMPLATE_CATEGORY': 28,
    'POSTGRESQL_TEMPLATE_CATEGORY': 29,
    'UTF8_ENCODING': 549,
    'LATIN2_ENCODING': 550,
    'MYSQL_DB': 325,
    'POSTGRESQL_DB': 326,
    'OCI_CONNECTION_ID': 37,
    'OCI_PAYMENT_ID': 33,
    'OCI_AUTOSCALING_ID': 184,
    'OCI_CLASSES_DICT_ID': 12
}

class CloneType(object):
    Runtime = 0
    AbsoluteCopy = 1

class TemplateType(object):
    vApps = 0
    Machine = 1
    Database = 2

class OktawaveApi(object):

    def __init__(self, username, password, debug=False):
        """Initialize the API instance

        Arguments:
        - username (string) - Oktawave account username
        - password (string) - Oktawave account password
        - debug (bool) - enable debug output?
        """
        self.username = username
        self.password = password
        self.debug = debug

    # HELPER METHODS ###
    # methods starting with "_" will not be autodispatched to client commands
    # ###

    def _d(self, what):
        if self.debug:
            print what

    def _init_common(self):
        """Convenience method to initialize CommonService client"""
        if hasattr(self, 'common'):
            return
        self.common = ApiClient(
            jsonapi_common, self.username, self.password, self.debug)
        self._d(self.common)

    def _init_clients(self):
        """Convenience method to initialize ClientsService client"""
        if hasattr(self, 'clients'):
            return
        self.clients = ApiClient(
            jsonapi_clients, self.username, self.password, self.debug)
        self._d(self.clients)

    def _logon(self, only_common=False):
        """Initializes CommonService client and calls LogonUser method.

        Returns the User object, as returned by LogonUser.
        Also sets self.client_id for convenience.
        """
        self._init_common()
        if not only_common:
            self._init_clients()
        if hasattr(self, 'client_object'):
            return self.client_object
        try:
            res = self.common.call(
                'LogonUser',
                user=self.username,
                password=self.password,
                ipAddress=self._get_machine_ip(),
                userAgent="Oktawave CLI")
        except AttributeError:
            raise
            raise OktawaveLoginError()
        self.client_id = res['Client']['ClientId']
        self.client_object = res
        return res

    def _search_params(self, sp):
        # getting rid of NoneType non-special attributes, required for
        # searchParams
        self._d(sp)
        for param in [m for m in dir(sp) if m[0] != '_']:
            if type(getattr(sp, param)) is not "NoneType":
                delattr(sp, param)
        return sp

    def _dict_names(self, data, field='ItemName'):
        return [item[field] for item in data if item['LanguageDictId'] == 2]

    def _dict_item_name(self, data):
        return self._dict_names(data['DictionaryItemNames'], 'ItemName')[0]

    def _simple_vm_method(self, method, vm_id):
        """Wraps around common simple virtual machine method call pattern"""
        self._logon()
        return self.clients.call(method, virtualMachineId=vm_id, clientId=self.client_id)

    def _find_disk(self, disk_id):
        """Finds a disk (OVS) by id"""
        dsp = self._search_params(self.clients.create('ns3:DisksSearchParams'))
        dsp.ClientId = self.client_id
        disks = [d for d in self.clients.call(
            'GetDisks', dsp)._results[0] if d.ClientHddId == disk_id]
        if len(disks) == 0:
            return None
        res = disks[0]
        if res.VirtualMachineHdds == None:
            res.VirtualMachineHdds = [[]]
        return res

    def _get_machine_ip(self):
        return '127.0.0.1'

    def _oci_class_id(self, class_name):
        """Returns ID of an OCI class with a given name"""
        classes = self.common.call(
            'GetDictionaryItems', dictionaryId=DICT['OCI_CLASSES_DICT_ID'], clientId=self.client_id)
        name2id = dict((self._dict_item_name(cls), cls['DictionaryItemId']) for cls in classes)
        self._d(name2id)
        if class_name in name2id:
            return name2id[class_name]
        return 0

    # API methods below ###

    # General / Account ###

    def Account_Settings(self):
        """Print basic settings of the client account

        args is an object containing at least the following fields:
        - username - Oktawave username
        - password - Oktawave client password
        Typically args will be the object returned from argparse.

        """
        self._logon(only_common=True)
        client = self.client_object
        # TODO: probably get more settings
        return {
            'time_zone': client['TimeZone']['DisplayName'],
            'currency': self._dict_item_name(client['Currency']),
            'date_format': self._dict_item_name(client['DateFormat']),
            'availability_zone': self._dict_item_name(
                self.common.call('GetDictionaryItemById', dictionaryItemId=client['AvailabilityZone'])),
            '24h_clock': client['Is24HourClock'],
        }

    def Account_RunningJobs(self):
        self._logon()
        res = self.common.call('GetRunningOperations', clientId=self.client_id)
        if not res:
            return
        for op in res:
            yield {
                'id': op['AsynchronousOperationId'],
                'creation_date': op['CreationDate'],
                'creation_user_name': op['CreationUserFullName'],
                'type': self._dict_item_name(op['OperationType']),
                'object_type': self._dict_item_name(op['ObjectType']),
                'object_name': op['ObjectName'],
                'progress_percent': op['Progress'],
                'status': self._dict_item_name(op['Status'])
            }

    def Account_Users(self):
        """Print users in client account."""
        self._logon()
        users = self.clients.call('GetClientUsers', clientId=self.client_id)
        self._d(users)
        for user in users:
            yield {
                'email': user['Email'],
                'name': user['FullName'],
            }

    # OCI (VMs) ###

    def OCI_Test(self):
        self._logon()
        self._d(self._oci_class_id('Large'))

    def OCI_TemplateCategories(self):
        """Lists available template categories"""
        self._logon()
        data = self.common.call('GetTemplateCategories', clientId=self.client_id)
        self._d(data)

        def _tc_info(tc, parent_id):
            return {
                'id': tc['TemplateCategoryId'],
                'name': self._dict_names(
                    tc['TemplateCategoryNames'], 'CategoryName')[0],
                'description': self._dict_names(
                    tc['TemplateCategoryNames'], 'CategoryDescription')[0],
                'parent_id': parent_id,
            }

        for tc in data:
            yield _tc_info(tc, None)
            if tc['CategoryChildren'] is not None:
                for tcc in tc['CategoryChildren']:
                    yield _tc_info(tcc, tc['TemplateCategoryId'])

    def OCI_Templates(self, category_id, name_filter=''):
        """Lists templates in a category"""
        self._logon()
        data = self.common.call(
            'GetTemplatesByCategory', categoryId=category_id, categorySystemId=None, type=None, clientId=self.client_id)
        if data:
            return dict((template['TemplateId'], template['TemplateName'])
                       for template in data if name_filter in template['TemplateName'])

    def OCI_TemplateInfo(self, template_id):
        """Shows more detailed info about a particular template"""
        self._logon()
        data = self.clients.call('GetTemplate', templateId=template_id, clientId=self.client_id)

        template_category = '/'.join(self._dict_names(
            data['TemplateCategory']['TemplateCategoryNames'], field='CategoryName'))

        software = ', '.join(
            '/'.join(self._dict_names(s['Software']['SoftwareNames'], field="Name"))
            for s in data['SoftwareList'])

        return {
            'template_id': data['TemplateId'],
            'template_name': data['TemplateName'],
            'template_category': template_category,
            'vm_class_id': data['VMClass']['DictionaryItemId'],
            'vm_class_name': self._dict_item_name(data['VMClass']),
            'system_category_name': self._dict_item_name(data['TemplateSystemCategory']),
            'label': data['Name'],
            'software': software,
            'eth_count': data['EthernetControllersCount'],
            'connection_type': self._dict_item_name(data['ConnectionType']),
            'disks': [{
                    'name': hdd['HddName'],
                    'capacity_gb': hdd['CapacityGB'],
                    'is_primary': hdd['IsPrimary']
                } for hdd in data['DiskDrives']],
            'description': data['Description']
        }

    def OCI_List(self):
        """Lists client's virtual machines"""
        self._logon()
        sp = { 'ClientId': self.client_id }
        vms = self.clients.call('GetVirtualMachines', searchParams=sp)
        self._d(vms)
        for vm in vms['_results']:
            yield {
                'id': vm['VirtualMachineId'],
                'name': vm['VirtualMachineName'],
                'class_name': self._dict_item_name(vm['VMClass'])
            }

    def OCI_Restart(self, oci_id):
        """Restarts given VM"""
        self._simple_vm_method('RestartVirtualMachine', oci_id)

    def OCI_TurnOff(self, oci_id):
        """Turns given VM off"""
        self._simple_vm_method('TurnoffVirtualMachine', oci_id)

    def OCI_TurnOn(self, oci_id):
        """Turns given virtual machine on"""
        self._simple_vm_method('TurnOnVirtualMachine', oci_id)

    def OCI_Delete(self, oci_id):
        """Deletes given virtual machine"""
        self._simple_vm_method('DeleteVirtualMachine', oci_id)

    def OCI_Logs(self, oci_id):
        """Shows virtual machine logs"""
        self._logon()
        sp = {
            'VirtualMachineId': oci_id,
            'PageSize': 100,
            'SortingDirection': 0,  # descending
        }
        data = self.clients.call(
            'GetVirtualMachineHistories', searchParams=sp, clientId=self.client_id)
        self._d(data)
        for op in data['_results']:
            yield {
                'time': self.clients.parse_date(op['CreationDate']),
                'type': self._dict_item_name(op['OperationType']),
                'user_name': op['CreationUser']['FullName'],
                'status': self._dict_item_name(op['Status'])
            }

    def OCI_Settings(self, oci_id):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        data = self._simple_vm_method('GetVirtualMachineById', oci_id)

        res = {
            'autoscaling': self._dict_item_name(data['AutoScalingType']),
            'connection_type': self._dict_item_name(data['ConnectionType']),
            'cpu_mhz': data['CpuMhz'],
            'cpu_usage_mhz': data['CpuMhzUsage'],
            'creation_date': self.clients.parse_date(data['CreationDate']),
            'creation_user_name': data['CreationUserSimple']['FullName'],
            'iops_usage': data['IopsUsage'],
            'last_change_date': self.clients.parse_date(data['LastChangeDate']),
            'payment_type': self._dict_item_name(data['PaymentType']),
            'memory_mb': data['RamMB'],
            'memory_usage_mb': data['RamMBUsage'],
            'status': self._dict_item_name(data['Status']),
            'name': data['VirtualMachineName'],
            'vm_class_name': self._dict_item_name(data['VMClass']),
            'disks': [{
                'name': disk['ClientHdd']['HddName'],
                'capacity_gb': disk['ClientHdd']['CapacityGB'],
                'creation_date': self.clients.parse_date(disk['ClientHdd']['CreationDate']),
                'creation_user_name': disk['ClientHdd']['CreationUser']['FullName'],
                'is_primary': disk['IsPrimary']
            } for disk in data['DiskDrives']],
            'ips': [{
                'ipv4': ip['Address'],
                'netmask': ip['NetMask'],
                'ipv6': ip['AddressV6'],
                'creation_date': self.clients.parse_date(ip['CreationDate']),
                'dhcp_branch': ip['DhcpBranch'],
                'gateway': ip['Gateway'],
                'status': self._dict_item_name(ip['IPStatus']),
                'last_change_date': self.clients.parse_date(ip['LastChangeDate']),
                'macaddr': ip['MacAddress'],
            } for ip in data['IPs']],
            'vlans': [],
        }
        if data['PrivateIpv4']:
            res['vlans'] = [{
                'ipv4': vlan['PrivateIpAddress'],
                'creation_date': self.clients.parse_date(vlan['CreationDate']),
                'macaddr': vlan['MacAddress'],
            } for vlan in data['PrivateIpv4']]

        return res

    def OCI_ChangeClass(self, oci_id, oci_class, at_midnight=False):
        """Changes running VM class, potentially rebooting it"""
        oci = self._simple_vm_method('GetVirtualMachineById', oci_id)
        oci_class_id = self._oci_class_id(oci_class)
        if not oci_class_id:
            raise OktawaveOCIClassNotFound()
        oci['VMClass'] = self.common.call('GetDictionaryItemById', dictionaryItemId=oci_class_id)
        self._d(oci)
        oci.setdefault('PrivateIpv4', '')
        self.clients.call(
            'UpdateVirtualMachine', machine=oci, clientId=self.client_id, classChangeInScheduler=at_midnight)

    def OCI_Create(self, name, template, oci_class=None, forced_type=TemplateType.Machine, db_type=None):
        """Creates a new instance from template"""
        self._logon()
        template = self.clients.call(
            'GetTemplate', templateId=template, clientId=self.client_id)
        oci_class_id = None
        if oci_class:
            oci_class_id = self._oci_class_id(oci_class)
            if not oci_class_id:
                raise OktawaveOCIClassNotFound()
        self.clients.call('CreateVirtualMachine',
                          templateId=template,
                          disks=None,
                          additionalDisks=None,
                          machineName=name,
                          selectedClass=oci_class_id,
                          selectedContainer=None,
                          selectedPaymentMethod=DICT['OCI_PAYMENT_ID'],
                          selectedConnectionType=DICT['OCI_CONNECTION_ID'],
                          clientId=self.client_id,
                          providervAppClientId=None,
                          vAppType=forced_type,
                          databaseTypeId=db_type,
                          clientVmParameter=None,
                          autoScalingTypeId=DICT['OCI_AUTOSCALING_ID']
                          )

    def OCI_Clone(self, oci_id, name, clonetype):
        """Clones a VM"""
        self._logon()
        self.clients.call('CloneVirtualMachine',
                          virtualMachineID=oci_id,
                          cloneName=name,
                          cloneType=clonetype,
                          clientId=self.client_id)

    # OVS (disks) ###

    def OVS_List(self):
        """Lists disks"""
        self._logon()
        dsp = self._search_params(self.clients.create('ns3:DisksSearchParams'))
        dsp.ClientId = self.client_id
        data = self.clients.call('GetDisks', dsp)
        for disk in data._results[0]:
            if disk.VirtualMachineHdds is None:
                vms = []
            else:
                vms = [{
                    'id': vm.VirtualMachine.VirtualMachineId,
                    'name': vm.VirtualMachine.VirtualMachineName,
                } for vm in disk.VirtualMachineHdds[0]]
            yield {
                'id': disk.ClientHddId,
                'name': disk.HddName,
                'tier': self._dict_item_name(disk.HddStandard),
                'capacity_gb': disk.CapacityGB,
                'used_gb': disk.UsedCapacityGB,
                'is_shared': disk.IsShared,
                'vms': vms,
            }

    def OVS_Delete(self, ovs_id):
        """Deletes a disk"""
        self._logon()
        res = self.clients.call('DeleteDisk', ovs_id, clientId=self.client_id)
        if not res:
            raise OktawaveOVSDeleteError()

    def OVS_Create(self, name, capacity_gb, tier, shared):
        """Adds a disk"""
        self._logon()
        disk = self.clients.create('ns3:ClientHddWithVMIds')
        disk.CapacityGB = capacity_gb
        disk.HddName = name
        disk.HddStandardId = 47 + int(tier)
        disk.IsShared = shared
        disk.PaymentTypeId = 37
        disk.VirtualMachineIds = ''  # this seems to solve the empty-array error problem, but certainly is not nice
        self.clients.call('CreateDisk', disk, clientId=self.client_id)

    def OVS_Map(self, ovs_id, oci_id):
        """Maps a disk into an instance"""
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        vms = [
            vm.VirtualMachine.VirtualMachineId for vm in disk.VirtualMachineHdds[0]]
        if oci_id in vms:
            raise OktawaveOVSMappedError()

        disk_mod = self.clients.create('ns3:ClientHddWithVMIds')
        for attr in ['CapacityGB', 'ClientHddId', 'HddName', 'IsShared']:
            setattr(disk_mod, attr, getattr(disk, attr))
        disk_mod.HddStandardId = disk.HddStandard.DictionaryItemId
        disk_mod.PaymentTypeId = disk.PaymentType.DictionaryItemId
        disk_mod.VirtualMachineIds = self.clients.create('ns6:ArrayOfint')
        disk_mod.VirtualMachineIds[0].extend(vms + [oci_id])
        res = self.clients.call('UpdateDisk', disk_mod, clientId=self.client_id)
        if not res:
            raise OktawaveOVSMapError()

    def OVS_Unmap(self, ovs_id, oci_id):
        """Unmaps a disk from an instance"""
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        vms = [
            vm.VirtualMachine.VirtualMachineId for vm in disk.VirtualMachineHdds[0]]
        if oci_id not in vms:
            raise OktawaveOVSUnmappedError()

        disk_mod = self.clients.create('ns3:ClientHddWithVMIds')
        for attr in ['CapacityGB', 'ClientHddId', 'HddName', 'IsShared']:
            setattr(disk_mod, attr, getattr(disk, attr))
        disk_mod.HddStandardId = disk.HddStandard.DictionaryItemId
        disk_mod.PaymentTypeId = disk.PaymentType.DictionaryItemId
        disk_mod.VirtualMachineIds = self.clients.create('ns6:ArrayOfint')
        disk_mod.VirtualMachineIds[0].extend(
            [vm for vm in vms if vm != oci_id])
        if len(disk_mod.VirtualMachineIds[0]) == 0:
            disk_mod.VirtualMachineIds = ''
        res = self.clients.call('UpdateDisk', disk_mod, clientId=self.client_id)
        if not res:
            raise OktawaveOVSUnmapError()

    # ORDB (databases) ###

    def ORDB_List(self):
        """Lists databases"""
        self._logon()
        sp = self._search_params(
            self.clients.create('ns3:DatabaseInstanceSearchParams'))
        sp.ClientId = self.client_id
        data = self.clients.call('GetDatabaseInstances', sp)
        if not data._results:
            return
        for db in data._results[0]:
            yield {
                'id': db.VirtualMachineId,
                'name': db.VirtualMachineName,
                'type': self._dict_item_name(db.DatabaseType),
                'size': db.Size,
                'available_space': db.AvailableSpace,
            }

    def ORDB_TurnOn(self, oci_id):
        """Turns a database on"""
        self._simple_vm_method('TurnOnVirtualMachine', oci_id)

    def ORDB_TurnOff(self, oci_id):
        """Turns a database off"""
        self._simple_vm_method('TurnoffVirtualMachine', oci_id)

    def ORDB_Restart(self, oci_id):
        """Restarts a database"""
        self._simple_vm_method('RestartVirtualMachine', oci_id)

    ORDB_Clone = OCI_Clone

    def ORDB_Delete(self, oci_id, db_name=None):
        """Deletes a database or VM"""
        self._logon()
        if db_name is None:
            self._simple_vm_method('DeleteVirtualMachine', oci_id)
        else:
            self.clients.call(
                'DeleteDatabase', oci_id, db_name, clientId=self.client_id)

    ORDB_Logs = OCI_Logs

    def ORDB_LogicalDatabases(self, oci_id):
        """Shows logical databases"""
        self._logon()
        sp = self._search_params(
            self.clients.create('ns3:DatabaseInstanceSearchParams'))
        sp.ClientId = self.client_id
        data = self.clients.call('GetDatabaseInstances', sp)
        if not data._results:
            return

        for vm in data._results[0]:
            if oci_id is not None and str(vm.VirtualMachineId) != str(oci_id):
                continue

            for db in vm.Databases[0]:
                yield {
                    'id': db.VirtualMachineId,
                    'name': db.DatabaseName,
                    'type': self._dict_item_name(db.DatabaseType),
                    'encoding': db.Encoding,
                    'is_running': db.IsRunning,
                    'qps': db.QPS,
                    'size': db.Size
                }

    ORDB_Settings = OCI_Settings

    def ORDB_Create(self, name, template, oci_class=None):
        """Creates a database VM"""
        self._logon()
        data = self.clients.call('GetTemplate', template, clientId=self.client_id)
        if str(data.TemplateType.DictionaryItemId) != str(DICT['DB_VM_CATEGORY']):
            raise OktawaveORDBInvalidTemplateError()
        self.OCI_Create(name, template,
                        forced_type=TemplateType.Database, db_type=data.DatabaseType.DictionaryItemId)

    def ORDB_GlobalSettings(self, oci_id):
        """Shows global database engine settings"""
        self._logon()
        data = self.clients.call('GetDatabaseConfig', oci_id, clientId=self.client_id)
        if not data:
            return

        for item in data[0]:
            yield {
                'name': item.Name,
                'value': item.Value
            }

    def ORDB_CreateLogicalDatabase(self, oci_id, name, encoding):
        """Creates a new logical database within an instance"""
        self._logon()
        self.clients.call('CreateDatabase', oci_id, name, DICT[
                          encoding.upper() + '_ENCODING'], clientId=self.client_id)

    def ORDB_BackupLogicalDatabase(self, oci_id, name):
        """Creates a backup of logical database"""
        self._logon()
        self.clients.call('BackupDatabase', oci_id, name, clientId=self.client_id)

    def ORDB_MoveLogicalDatabase(self, oci_id_from, oci_id_to, name):
        """Moves a logical database"""
        self._logon()
        self.clients.call(
            'MoveDatabase', oci_id_from, oci_id_to, name, clientId=self.client_id)

    def ORDB_Backups(self):
        """Lists logical database backups"""
        self._logon()
        mysql_data = self.clients.call(
            'GetBackups', DICT['MYSQL_DB'], clientId=self.client_id) or [[]]
        pgsql_data = self.clients.call(
            'GetBackups', DICT['POSTGRESQL_DB'], clientId=self.client_id) or [[]]

        for db in mysql_data[0]:
            yield {
                'file_name': b.Name,
                'type': 'MySQL',
                'path': b.ContainerName +
                    "/" + b.FullPath
            }

        for db in pgsql_data[0]:
            yield {
                'file_name': b.Name,
                'type': 'PostgreSQL',
                'path': b.ContainerName +
                    "/" + b.FullPath
            }

    def ORDB_RestoreLogicalDatabase(self, oci_id, name, backup_file):
        """Restores a database from backup"""
        self._logon()
        self.clients.call('RestoreDatabase', oci_id,
                          name, backup_file, clientId=self.client_id)

class OCSConnection(Connection):
    def __init__(self, username, password):
        super(OCSConnection, self).__init__(
            'https://ocs-pl.oktawave.com/auth/v1.0', username, password)

