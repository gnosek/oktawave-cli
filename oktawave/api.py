from client import ApiClient
from exceptions import *
from time import time
try:
    from swiftclient import Connection
except ImportError:
    from swift.common.client import Connection

# JSON API endpoints
jsonapi_common = 'https://api.oktawave.com/CommonService.svc/json'
jsonapi_clients = 'https://api.oktawave.com/ClientsService.svc/json'

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
    'OCI_CLASSES_DICT_ID': 12,
    'OVS_TIERS_DICT_ID': 17,
    'OVS_PAYMENT_ID': 33,
    'OPN_PAYMENT_ID': 33
}

class CloneType(object):
    Runtime = 869
    AbsoluteCopy = 870

class TemplateType(object):
    vApps = 173
    Machine = 174
    Database = 324

class PowerStatus(object):
    PowerOn = 86
    PowerOff = 87

    def __init__(self, status):
        self.status = status

    def __str__(self):
        if self.status == self.PowerOn:
            return 'Powered on'
        elif self.status == self.PowerOff:
            return 'Powered off'
        else:
            return 'unknown status #%d' % self.status

class DictionaryItem(object):
    LANGUAGE_ID = 2
    ITEM_ID_FIELD = 'DictionaryItemId'
    NAME_LIST_FIELD = 'DictionaryItemNames'
    NAME_FIELD = 'ItemName'

    def _dict_names(self, data, field):
        return [item[field] for item in data if item['LanguageDictId'] == self.LANGUAGE_ID]

    def _dict_item_name(self, data):
        return self._dict_names(data[self.NAME_LIST_FIELD], self.NAME_FIELD)[0]

    def __init__(self, item):
        self.id = item[self.ITEM_ID_FIELD]
        self.name = self._dict_item_name(item)
        self.item = item

    def __str__(self):
        return self.name

    def __int__(self):
        return self.id

    def __eq__(self, other):
        try:
            if str(self) == str(other):
                return True
        except ValueError:
            pass
        return str(self) == str(other)

    def __ne__(self, other):
        return not self == other

class TemplateCategory(DictionaryItem):
    ITEM_ID_FIELD = 'TemplateCategoryId'
    NAME_LIST_FIELD = 'TemplateCategoryNames'
    NAME_FIELD = 'CategoryName'

    def __init__(self, data, parent_id):
        super(TemplateCategory, self).__init__(data)
        self.parent_id = parent_id
        self.description = self._dict_names(data[self.NAME_LIST_FIELD], 'CategoryDescription')[0]
        self.tree_path = '/'.join(self._dict_names(data[self.NAME_LIST_FIELD], self.NAME_FIELD))

class SoftwareItem(DictionaryItem):
    ITEM_ID_FIELD = 'SoftwareId'
    NAME_LIST_FIELD = 'SoftwareNames'
    NAME_FIELD = 'Name'

    def __init__(self, data):
        super(SoftwareItem, self).__init__(data)
        self.tree_path = '/'.join(self._dict_names(data[self.NAME_LIST_FIELD], self.NAME_FIELD))

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

    def _simple_vm_method(self, method, vm_id):
        """Wraps around common simple virtual machine method call pattern"""
        self._logon()
        return self.clients.call(method, virtualMachineId=vm_id, clientId=self.client_id)

    def _find_disk(self, disk_id):
        """Finds a disk (OVS) by id"""
        dsp = {
            'ClientId': self.client_id,
        }
        disks = [d for d in self.clients.call(
            'GetDisks', searchParams=dsp)['_results'] if d['ClientHddId'] == disk_id]
        if len(disks) == 0:
            return None
        res = disks[0]
        if res['VirtualMachineHdds'] is None:
            res['VirtualMachineHdds'] = []
        return res

    def _get_machine_ip(self):
        return '127.0.0.1'

    def _dict_item(self, dict_id, key):
        items = self.common.call(
            'GetDictionaryItems', dictionary=dict_id, clientId=self.client_id)
        for item in items:
            item = DictionaryItem(item)
            if item.name == key:
                return item

    def _oci_class(self, class_name):
        """Returns a dictionary item for OCI class with a given name"""
        return self._dict_item(DICT['OCI_CLASSES_DICT_ID'], class_name)

    def _ovs_tier(self, tier):
        """Returns ID of a given disk tier"""
        tier_name = 'Tier ' + str(tier)
        tier_obj = self._dict_item(DICT['OVS_TIERS_DICT_ID'], tier_name)
        if not tier_obj:
            raise OktawaveOVSTierNotFound()
        return tier_obj

    def _ovs_disk_mod(self, disk):
        vms = [
            vm['VirtualMachine']['VirtualMachineId'] for vm in disk['VirtualMachineHdds']]

        lock_vms = [
            vm['VirtualMachine']['VirtualMachineId'] for vm in disk['VirtualMachineHdds'] if
            vm['VirtualMachine']['StatusDictId'] == PowerStatus.PowerOn or
            not vm['IsPrimary']
        ]

        disk_mod = {
            'CapacityGB': disk['CapacityGB'],
            'ClientHddId': disk['ClientHddId'],
            'ClusterId': disk['Cluster']['ClusterId'],
            'HddName': disk['HddName'],
            'IsShared': disk['IsShared'],
            'HddStandardId': disk['HddStandard']['DictionaryItemId'],
            'PaymentTypeId': disk['PaymentType']['DictionaryItemId'],
            'VirtualMachineIds': vms,
            'LockVirtualMachineIds': lock_vms,
        }
        return disk_mod

    def _container_simple(self, container_id):
        """Fetches a container's information using GetContainersSimpleWithVM"""
        self._logon()
        cs = self.clients.call('GetContainersSimpleWithVM', clientId=self.client_id)
        for c in cs:
            self._d([c, container_id])
            if str(c['ContainerId']) == str(container_id):
                return c
        raise OktawaveContainerNotFoundError()


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
            'currency': DictionaryItem(client['Currency']),
            'date_format': DictionaryItem(client['DateFormat']),
            'availability_zone': DictionaryItem(
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
                'type': op['OperationTypeName'],
                'object_type': op['ObjectTypeName'],
                'object_name': op['ObjectName'],
                'progress_percent': op['Progress'],
                'status': op['StatusName']
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

    def OCI_TemplateCategories(self):
        """Lists available template categories"""
        self._logon()
        data = self.common.call('GetTemplateCategories', clientId=self.client_id)
        self._d(data)

        for tc in data:
            yield TemplateCategory(tc, None)
            if tc['CategoryChildren'] is not None:
                for tcc in tc['CategoryChildren']:
                    yield TemplateCategory(tcc, tc['TemplateCategoryId'])

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

        template_category = TemplateCategory(data['TemplateCategory'], None)
        software = [SoftwareItem(item['Software']) for item in data['SoftwareList']]

        return {
            'template_id': data['TemplateId'],
            'template_name': data['TemplateName'],
            'template_category': template_category.tree_path,
            'vm_class_id': data['VMClass']['DictionaryItemId'],
            'vm_class_name': DictionaryItem(data['VMClass']),
            'system_category_name': DictionaryItem(data['TemplateSystemCategory']),
            'label': data['Name'],
            'software': software,
            'eth_count': data['EthernetControllersCount'],
            'connection_type': DictionaryItem(data['ConnectionType']),
            'disks': [{
                'name': hdd['HddName'],
                'capacity_gb': hdd['CapacityGB'],
                'is_primary': hdd['IsPrimary']
                } for hdd in data['DiskDrives']],
            'description': data['Description']
        }

    def OCI_List(self):
        """Lists client's virtual machines' basic info"""
        self._logon()
        vms = self.clients.call('GetVirtualMachinesSimple', clientId=self.client_id)
        self._d(vms)
        for vm in vms:
            yield {
                'id': vm['VirtualMachineId'],
                'name': vm['VirtualMachineName'],
                'status': PowerStatus(vm['StatusDictId']),
            }

    def OCI_ListDetails(self):
        """Lists client's virtual machines"""
        self._logon()
        sp = { 'ClientId': self.client_id }
        vms = self.clients.call('GetVirtualMachines', searchParams=sp)
        self._d(vms)
        for vm in vms['_results']:
            yield {
                'id': vm['VirtualMachineId'],
                'name': vm['VirtualMachineName'],
                'status': PowerStatus(vm['StatusDictId']),
                'class_name': DictionaryItem(vm['VMClass']),
                'cpu_mhz': vm['CpuMhz'],
                'cpu_usage_mhz': vm['CpuMhzUsage'],
                'memory_mb': vm['RamMB'],
                'memory_usage_mb': vm['RamMBUsage'],
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
                'type': DictionaryItem(op['OperationType']),
                'user_name': op['CreationUser']['FullName'],
                'status': DictionaryItem(op['Status']),
                'parameters': [item['Value'] for item in op['Parameters']],
            }

    def OCI_DefaultPassword(self, oci_id):
        logs = self.OCI_Logs(oci_id)
        for entry in logs:
            if entry['type'] == 'Instance access details':
                try:
                    return entry['parameters'][0]
                except IndexError:
                    return  # no data yet

    def OCI_Settings(self, oci_id):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        data = self._simple_vm_method('GetVirtualMachineById', oci_id)

        res = {
            'autoscaling': DictionaryItem(data['AutoScalingType']),
            'connection_type': DictionaryItem(data['ConnectionType']),
            'cpu_mhz': data['CpuMhz'],
            'cpu_usage_mhz': data['CpuMhzUsage'],
            'creation_date': self.clients.parse_date(data['CreationDate']),
            'creation_user_name': data['CreationUserSimple']['FullName'],
            'iops_usage': data['IopsUsage'],
            'last_change_date': self.clients.parse_date(data['LastChangeDate']),
            'payment_type': DictionaryItem(data['PaymentType']),
            'memory_mb': data['RamMB'],
            'memory_usage_mb': data['RamMBUsage'],
            'status': DictionaryItem(data['Status']),
            'name': data['VirtualMachineName'],
            'vm_class_name': DictionaryItem(data['VMClass']),
            'disks': [{
                'id': disk['ClientHddId'],
                'name': disk['ClientHdd']['HddName'],
                'capacity_gb': disk['ClientHdd']['CapacityGB'],
                'creation_date': self.clients.parse_date(disk['ClientHdd']['CreationDate']),
                'creation_user_name': disk['ClientHdd']['CreationUser']['FullName'],
                'is_primary': disk['IsPrimary'],
                'is_shared': disk['ClientHdd']['IsShared']
                } for disk in data['DiskDrives']],
            'ips': [{
                'ipv4': ip['Address'],
                'netmask': ip['NetMask'],
                'ipv6': ip['AddressV6'],
                'creation_date': self.clients.parse_date(ip['CreationDate']),
                'dhcp_branch': ip['DhcpBranch'],
                'gateway': ip['Gateway'],
                'status': DictionaryItem(ip['IPStatus']),
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
        oci_class_obj = self._oci_class(oci_class)
        if not oci_class_obj:
            raise OktawaveOCIClassNotFound()
        oci['VMClass'] = oci_class_obj.item
        self._d(oci)
        oci.setdefault('PrivateIpv4', '')
        self.clients.call(
            'UpdateVirtualMachine', machine=oci, clientId=self.client_id, classChangeInScheduler=at_midnight)

    def _subregion_id(self, subregion):
        if str(subregion) == 'Auto':
            return None
        if str(subregion) == '1':
            return 1
        return 4

    def OCI_Create(self, name, template, oci_class=None, forced_type=TemplateType.Machine, db_type=None, subregion='Auto'):
        """Creates a new instance from template"""
        self._logon()
        oci_class_id = None
        if oci_class is not None:
            oci_class_obj = self._oci_class(oci_class)
            if not oci_class_obj:
                raise OktawaveOCIClassNotFound()
            oci_class_id = oci_class_obj.id
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
                          autoScalingTypeId=DICT['OCI_AUTOSCALING_ID'],
                          clusterId=self._subregion_id(subregion)
                          )

    def OCI_Clone(self, oci_id, name, clonetype):
        """Clones a VM"""
        self._logon()
        self.clients.call('CloneVirtualMachine',
                          virtualMachineId=oci_id,
                          cloneName=name,
                          cloneType=clonetype,
                          clientId=self.client_id)

    # OVS (disks) ###

    def OVS_List(self):
        """Lists disks"""
        self._logon()
        dsp = {
            'ClientId': self.client_id,
        }
        data = self.clients.call('GetDisks', searchParams=dsp)
        for disk in data['_results']:
            if disk['VirtualMachineHdds'] is None:
                vms = []
            else:
                vms = [{
                    'id': vm['VirtualMachine']['VirtualMachineId'],
                    'name': vm['VirtualMachine']['VirtualMachineName'],
                    'primary': vm['IsPrimary'],
                    'vm_status': PowerStatus(vm['VirtualMachine']['StatusDictId']),
                    } for vm in disk['VirtualMachineHdds']]
            yield {
                'id': disk['ClientHddId'],
                'name': disk['HddName'],
                'tier': DictionaryItem(disk['HddStandard']),
                'capacity_gb': disk['CapacityGB'],
                'used_gb': disk['UsedCapacityGB'],
                'is_shared': disk['IsShared'],
                'vms': vms,
            }

    def OVS_Delete(self, ovs_id):
        """Deletes a disk"""
        self._logon()
        res = self.clients.call('DeleteDisk', clientHddId=ovs_id, clientId=self.client_id)
        if not res:
            raise OktawaveOVSDeleteError()

    def OVS_Create(self, name, capacity_gb, tier, shared, subregion='Auto'):
        """Adds a disk"""
        self._logon()
        disk = {
            'CapacityGB': capacity_gb,
            'HddName': name,
            'HddStandardId': self._ovs_tier(tier).id,
            'IsShared': shared,
            'PaymentTypeId': DICT['OVS_PAYMENT_ID'],
            'VirtualMachineIds': [],
            'ClusterId': self._subregion_id(subregion)
        }
        self.clients.call('CreateDisk', clientHdd=disk, clientId=self.client_id)

    def OVS_Map(self, ovs_id, oci_id):
        """Maps a disk into an instance"""
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        disk_mod = self._ovs_disk_mod(disk)
        if oci_id in disk_mod['VirtualMachineIds']:
            raise OktawaveOVSMappedError()
        disk_mod['VirtualMachineIds'].append(oci_id)

        res = self.clients.call('UpdateDisk', clientHdd=disk_mod, clientId=self.client_id)
        if not res:
            raise OktawaveOVSMapError()

    def OVS_Unmap(self, ovs_id, oci_id):
        """Unmaps a disk from an instance"""
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        disk_mod = self._ovs_disk_mod(disk)
        if oci_id not in disk_mod['VirtualMachineIds']:
            raise OktawaveOVSUnmappedError()

        disk_mod['VirtualMachineIds'].remove(oci_id)

        res = self.clients.call('UpdateDisk', clientHdd=disk_mod, clientId=self.client_id)
        if not res:
            raise OktawaveOVSUnmapError()

    def OVS_ChangeTier(self, ovs_id, tier):
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        disk_mod = self._ovs_disk_mod(disk)
        disk_mod['HddStandardId'] = self._ovs_tier(tier).id

        self.clients.call('UpdateDisk', clientHdd=disk_mod, clientId=self.client_id)

    def OVS_Extend(self, ovs_id, capacity_gb):
        self._logon()
        disk = self._find_disk(ovs_id)
        if disk is None:
            raise OktawaveOVSNotFoundError()

        disk_mod = self._ovs_disk_mod(disk)
        if disk_mod.pop('LockVirtualMachineIds'):
            raise OktawaveOVSMappedError()

        if disk_mod['CapacityGB'] > capacity_gb:
            raise OktawaveOVSTooSmallError()

        disk_mod['CapacityGB'] = capacity_gb

        self.clients.call('UpdateDisk', clientHdd=disk_mod, clientId=self.client_id)

    # ORDB (databases) ###

    def ORDB_List(self):
        """Lists databases"""
        self._logon()
        sp = {
            'ClientId': self.client_id,
        }
        data = self.clients.call('GetDatabaseInstances', searchParams=sp)
        for db in data['_results']:
            yield {
                'id': db['VirtualMachineId'],
                'name': db['VirtualMachineName'],
                'type': DictionaryItem(db['DatabaseType']),
                'size': db['Size'],
                'available_space': db['AvailableSpace'],
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
                'DeleteDatabase', virtualMachineId=oci_id, databaseName=db_name,
                clientId=self.client_id)

    ORDB_Logs = OCI_Logs

    def ORDB_LogicalDatabases(self, oci_id):
        """Shows logical databases"""
        self._logon()
        sp = {
            'ClientId': self.client_id,
        }
        data = self.clients.call('GetDatabaseInstances', searchParams=sp)

        for vm in data['_results']:
            if oci_id is not None and str(vm['VirtualMachineId']) != str(oci_id):
                continue

            for db in vm['Databases']:
                yield {
                    'id': db['VirtualMachineId'],
                    'name': db['DatabaseName'],
                    'type': DictionaryItem(db['DatabaseType']),
                    'encoding': db['Encoding'],
                    'is_running': db['IsRunning'],
                    'qps': db['QPS'],
                    'size': db['Size']
                }

    ORDB_Settings = OCI_Settings

    def ORDB_Create(self, name, template, oci_class=None, subregion='Auto'):
        """Creates a database VM"""
        self._logon()
        data = self.clients.call('GetTemplate', templateId=template, clientId=self.client_id)
        if str(data['TemplateType']['DictionaryItemId']) != str(DICT['DB_VM_CATEGORY']):
            raise OktawaveORDBInvalidTemplateError()
        self.OCI_Create(name, template,
                        forced_type=TemplateType.Database,
                        db_type=data['DatabaseType']['DictionaryItemId'],
                        subregion=subregion,
                        oci_class=oci_class)

    def ORDB_GlobalSettings(self, oci_id):
        """Shows global database engine settings"""
        self._logon()
        data = self.clients.call('GetDatabaseConfig', virtualMachineId=oci_id, clientId=self.client_id)

        for item in data:
            yield {
                'name': item.Name,
                'value': item.Value
            }

    def ORDB_CreateLogicalDatabase(self, oci_id, name, encoding):
        """Creates a new logical database within an instance"""
        self._logon()
        self.clients.call(
            'CreateDatabase',
            virtualMachineId=oci_id,
            databaseName=name,
            encodingDictId=DICT[encoding.upper() + '_ENCODING'],
            clientId=self.client_id)

    def ORDB_BackupLogicalDatabase(self, oci_id, name):
        """Creates a backup of logical database"""
        self._logon()
        self.clients.call('BackupDatabase', virtualMachineId=oci_id,
                          databaseName=name, clientId=self.client_id)

    def ORDB_MoveLogicalDatabase(self, oci_id_from, oci_id_to, name):
        """Moves a logical database"""
        self._logon()
        self.clients.call(
            'MoveDatabase',
            virtualMachineIdFrom=oci_id_from,
            virtualMachineIdTo=oci_id_to,
            databaseName=name,
            clientId=self.client_id)

    def ORDB_Backups(self):
        """Lists logical database backups"""
        self._logon()
        mysql_data = self.clients.call(
            'GetBackups', databaseTypeDictId=DICT['MYSQL_DB'], clientId=self.client_id) or []
        pgsql_data = self.clients.call(
            'GetBackups', databaseTypeDictId=DICT['POSTGRESQL_DB'], clientId=self.client_id) or []

        for b in mysql_data:
            yield {
                'file_name': b['Name'],
                'type': 'MySQL',
                'path': b['ContainerName'] +
                "/" + b['FullPath']
            }

        for b in pgsql_data:
            yield {
                'file_name': b['Name'],
                'type': 'PostgreSQL',
                'path': b['ContainerName'] +
                "/" + b['FullPath']
            }

    def ORDB_RestoreLogicalDatabase(self, oci_id, name, backup_file):
        """Restores a database from backup"""
        self._logon()
        self.clients.call('RestoreDatabase', virtualMachineId=oci_id,
                          databaseName=name, backupFileName=backup_file,
                          clientId=self.client_id)


    def Container_List(self):
        """Lists client's containers' basic info"""
        self._logon()
        containers = self.clients.call('GetContainers', clientId=self.client_id)
        for c in containers:
            yield {
                'id': c['ContainerId'],
                'name': c['ContainerName'],
                'vms': c['VirtualMachineCount']
            }

    def Container_Get(self, container_id):
        """Displays a container's information"""
        self._logon()
        c = self.clients.call('GetContainer', containerId=container_id)
        res = {
            'autoscaling': DictionaryItem(c['AutoScalingType']),
            'id': c['ContainerId'],
            'name': c['ContainerName'],
            'healthcheck': c['IsServiceCheckAvailable'],
            'load_balancer': c['IsLoadBalancer'],
            'master_service_id': c['MasterServiceId'],
            'master_service_name': c['MasterServiceName'],
            'proxy_cache': c['IsProxyCache'],
            'ssl': c['IsSSLUsed'],
            'port': c['PortNumber'],
            'schedulers': c['SchedulersCount'],
            'vms': c['VirtualMachineCount'],
            'db_user': c['DatabaseUserLogin'],
            'db_password': c['DatabaseUserPassword']
        }
        for label, item in (
            ('ip_version', 'IPVersion'),
            ('load_balancer_algorithm', 'LoadBalancerAlgorithm'),
            ('service', 'Service'),
            ('session_type', 'SessionType')):
            if c[item]:
                res[label] = DictionaryItem(c[item])
            else:
                res[label] = None
        res['ips'] = [
            {'ipv4': ip['Address'], 'ipv6': ip['AddressV6']} for ip in c['IPs']
        ]
        return res

    def Container_OCIList(self, container_id):
        c_simple = self._container_simple(container_id)
        for vm in c_simple['VirtualMachines']:
            vms = vm['VirtualMachineSimple']
            yield {
                'oci_id': vms['VirtualMachineId'],
                'oci_name': vms['VirtualMachineName'],
                'status': PowerStatus(vms['StatusDictId'])
            }

    def Container_RemoveOCI(self, container_id, oci_id):
        """Removes an instance from container"""
        self._logon()
        c_simple = self._container_simple(container_id)
        found = False
        for vm in c_simple['VirtualMachines']:
            if vm['VirtualMachineId'] == oci_id:
                found = True
                break
        if not found:
            raise OktawaveOCINotInContainer()
        vm_ids = [vm['VirtualMachineId']
            for vm in c_simple['VirtualMachines']
            if vm['VirtualMachineId'] != oci_id]
        c = self.clients.call('GetContainer', containerId=container_id)
        self._d(vm_ids)
        self.clients.call('UpdateContainer', container=c, virtualMachinesId=vm_ids)

    def Container_AddOCI(self, container_id, oci_id):
        """Adds an instance to container"""
        self._logon()
        c_simple = self._container_simple(container_id)
        found = False
        for vm in c_simple['VirtualMachines']:
            if vm['VirtualMachineId'] == oci_id:
                found = True
                break
        if found:
            raise OktawaveOCIInContainer()
        vm_ids = [vm['VirtualMachineId']
            for vm in c_simple['VirtualMachines']] + [oci_id]
        c = self.clients.call('GetContainer', containerId=container_id)
        self.clients.call('UpdateContainer', container=c, virtualMachinesId=vm_ids)

    def Container_Delete(self, container_id):
        self._logon()
        self.clients.call('DeleteContainers', containerIds=[container_id],
            clientId=self.client_id)

    def _container_service_id(self, service):
        services = {'HTTP' : 43, 'HTTPS' : 44, 'SMTP' : 45, 'MySQL' : 287, 'Port' : 155}
        return services[service]

    def _load_balancer_algorithm_id(self, algorithm):
        algorithms = {'least_response_time' : 282, 'least_connections' : 281, 'source_ip_hash' : 288, 'round_robin' : 612}
        return algorithms[algorithm]

    def _session_type_id(self, s_type):
        s_types = {'none' : 47, 'by_source_ip' : 46, 'by_cookie' : 280}
        return s_types[s_type]

    def _ip_version_id(self, version):
        versions = {'4' : 115, '6' : 116, 'both' : 565}
        return versions[version]

    def _autoscaling_id(self, autoscaling):
        types = {'on' : 185, 'off' : 184}
        return types[autoscaling]

    def Container_Create(
            self, name, load_balancer, service, port, proxy_cache, ssl,
            healthcheck, master_id, session, lb_algorithm, ip_version, autoscaling):
        if lb_algorithm == 'least_response_time' and service != 'HTTP' and service != 'HTTPS':
            raise OktawaveLRTNotAllowed()
        self._logon()
        vm_ids = [] if master_id is None else [master_id]
        result = self.clients.call('CreateContainer', container = {
            'OwnerClientId' : self.client_id,
            'ContainerName' : name,
            'IsLoadBalancer' : load_balancer,
            'Service' : {'DictionaryItemId' : self._container_service_id(service)},
            'LoadBalancerAlgorithm' : {'DictionaryItemId' : self._load_balancer_algorithm_id(lb_algorithm)},
            'IsSSLUsed' : ssl,
            'IsProxyCache' : proxy_cache,
            'MasterServiceId' : master_id,
            'PortNumber' : port,
            'SessionType' : {'DictionaryItemId' : self._session_type_id(session)},
            'IPVersion' : {'DictionaryItemId' : self._ip_version_id(ip_version)},
            'AutoScalingType' : {'DictionaryItemId' : self._autoscaling_id(autoscaling)},
            'IsServiceCheckAvailable' : healthcheck
        }, virtualMachinesId = vm_ids)
        return result

    # TODO: allow to change only selected parameters, add more validation
    # without relying on the UpdateContainer API method.
    def Container_Edit(
            self, container_id, name, load_balancer, service, port, proxy_cache, ssl,
            healthcheck, master_id, session, lb_algorithm, ip_version, autoscaling):
        self._logon()
        if lb_algorithm == 'least_response_time' and service != 'HTTP' and service != 'HTTPS':
            raise OktawaveLRTNotAllowed()
        c = self.clients.call('GetContainer', containerId=container_id)
        c_simple = self._container_simple(container_id)
        c['ContainerName'] = name
        c['IsLoadBalancer'] = load_balancer
        c['Service'] = {'DictionaryItemId' : self._container_service_id(service)}
        c['LoadBalancerAlgorithm'] = {'DictionaryItemId' : self._load_balancer_algorithm_id(lb_algorithm)}
        c['IsSSLUsed'] = ssl
        c['IsProxyCache'] = proxy_cache
        c['MasterServiceId'] = master_id
        c['PortNumber'] = port
        c['SessionType'] = {'DictionaryItemId' : self._session_type_id(session)}
        c['IPVersion'] = {'DictionaryItemId' : self._ip_version_id(ip_version)}
        c['AutoScalingType'] = {'DictionaryItemId' : self._autoscaling_id(autoscaling)}
        c['AutoScalingTypeDictId'] = self._autoscaling_id(autoscaling)
        c['IsServiceCheckAvailable'] = healthcheck
        self._d(c)
        self.clients.call('UpdateContainer', container=c,
            virtualMachinesId=[vm['VirtualMachineId'] for vm in c_simple['VirtualMachines']])


    def _address_pool_id(self, name):
        pools = {'10.0.0.0/24' : 278, '192.168.0.0/24' : 279}
        return pools[name]
        
    def OPN_List(self):
        """Lists client's OPNs"""
        self._logon()
        vlans = self.clients.call('GetVlansByClientId', clientId=self.client_id)
        for v in vlans:
            yield {
                'id': v['VlanId'],
                'name': v['VlanName'],
                'address_pool': DictionaryItem(v['AddressPool']),
                'payment_type': DictionaryItem(v['PaymentType'])
            }

    def OPN_Get(self, opn_id):
        self._logon()
        v = self.clients.call('GetVlanById', vlanId=opn_id, clientId=self.client_id)
        vms = self.clients.call('GetVirtualMachineVlansByVlanId', vlanId=opn_id, clientId=self.client_id)
        return {
            'id': v['VlanId'],
            'name': v['VlanName'],
            'address_pool': DictionaryItem(v['AddressPool']),
            'payment_type': DictionaryItem(v['PaymentType']),
            'vms': vms
        }

    def OPN_Create(self, name, address_pool):
        self._logon()
        self._d(self.client_object)
        return self.clients.call('CreateVlan', vlan={
            'VlanName' : name,
            'AddressPool' : {'DictionaryItemId' : self._address_pool_id(address_pool)},
            'OwnerClient' : self.client_object['Client'],
            'PaymentType' : {'DictionaryItemId' : DICT['OPN_PAYMENT_ID']},
            'CreationUserId' : self.client_id
        })

    def OPN_Delete(self, opn_id):
        self._logon()
        return self.clients.call('DeleteVlan', vlanId=opn_id, clientId=self.client_id)

    def OPN_AddOCI(self, opn_id, oci_id, ip_address):
        self._logon()
        oci = self.clients.call('GetVirtualMachineById', virtualMachineId=oci_id, clientId=self.client_id)
        vlan = self.clients.call('GetVlanById', vlanId=opn_id, clientId=self.client_id)
        for opn in oci['PrivateIpv4']:
            if opn['Vlan']['VlanId'] == opn_id:
                raise OktawaveOCIInOPN()
        oci['PrivateIpv4'].append({
            'PrivateIpAddress' : ip_address,
            'VirtualMachine' : {'VirtualMachineName' : oci['VirtualMachineName'], 'VirtualMachineId' : oci_id, 'StatusDictId' : oci['Status']['DictionaryItemId']},
            'Vlan' : vlan,
            'CreationDate' : '/Date(' + str(int(time()) * 100) + '+0000)/', # for some reason API server does not fill this field automatically
        })
        return self.clients.call('UpdateVirtualMachine', machine=oci, clientId=self.client_id, classChangeInScheduler=False)

    def OPN_RemoveOCI(self, opn_id, oci_id):
        self._logon()
        oci = self.clients.call('GetVirtualMachineById', virtualMachineId=oci_id, clientId=self.client_id)
        vlan = self.clients.call('GetVlanById', vlanId=opn_id, clientId=self.client_id)
        l1 = len(oci['PrivateIpv4'])
        oci['PrivateIpv4'] = filter(lambda x: x['Vlan']['VlanId'] != opn_id, oci['PrivateIpv4'])
        if l1 == len(oci['PrivateIpv4']):
            raise OktawaveOCINotInOPN()
        return self.clients.call('UpdateVirtualMachine', machine=oci, clientId=self.client_id, classChangeInScheduler=False)

    def OPN_Rename(self, opn_id, name):
        self._logon()
        vlan = self.clients.call('GetVlanById', vlanId=opn_id, clientId=self.client_id)
        vlan['VlanName'] = name
        return self.clients.call('UpdateVlan', vlan=vlan)



class OCSConnection(Connection):
    def __init__(self, username, password):
        super(OCSConnection, self).__init__(
            'https://ocs-pl.oktawave.com/auth/v1.0', username, password)

