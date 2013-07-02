from client import ApiClient
from printer import Printer
from suds.sax.element import Element
import sys
import suds
from suds import null
try:
    from swiftclient import Connection
except ImportError:
    from swift.common.client import Connection
import itertools
import socket


# Patching some stuff in suds to get it working with SOAP 1.2
suds.bindings.binding.envns = (
    'SOAP-ENV', 'http://www.w3.org/2003/05/soap-envelope')


class SudsClientPatched(suds.client.SoapClient):

    def headers(self):
        """
        Get http headers or the http/https request.
        @return: A dictionary of header/values.
        @rtype: dict
        """
        action = self.method.soap.action
        if isinstance(action, unicode):
            action = action.encode('utf-8')
        stock = {'Content-Type':
                 'application/soap+xml; charset=utf-8', 'SOAPAction': action}
        result = dict(stock, **self.options.headers)
        suds.client.log.debug('headers = %s', result)
        return result
suds.client.SoapClient = SudsClientPatched

# WSDL addresses
wsdl_common = 'https://api.oktawave.com/CommonService.svc?wsdl'
wsdl_clients = 'https://api.oktawave.com/ClientsService.svc?wsdl'

# Fixing WSDL to work with suds
ans = ('a', 'http://www.w3.org/2005/08/addressing')


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


class OktawaveApi:

    def __init__(self, args, output=sys.stdout):
        """Initialize the API instance

        Arguments:
        - args - reserved for future use
        - output - stream to which the results should be printed
        """
        self.p = Printer(output)
        self.debug = args.debug

    # HELPER METHODS ###
    # methods starting with "_" will not be autodispatched to client commands
    # ###

    def _d(self, what):
        if self.debug:
            print what

    def _init_common(self, args):
        """Convenience method to initialize CommonService client"""
        if hasattr(self, 'common'):
            return
        self.common = ApiClient(
            wsdl_common, args.username, args.password, hc_common, docs_common, args.debug)
        self._d(self.common)

    def _init_clients(self, args):
        """Convenience method to initialize ClientsService client"""
        if hasattr(self, 'clients'):
            return
        self.clients = ApiClient(
            wsdl_clients, args.username, args.password, hc_clients, docs_clients, args.debug)
        self.clients.client.factory.separator('########')
        self._d(self.clients)

    def _init_both_apis(self, args):
        """Convenience method to initialize both of the above clients"""
        self._init_common(args)
        self._init_clients(args)

    def _print(self, *args):
        """Proxy method to print strings"""
        self.p._print(*args)

    def _logon(self, args, only_common=False):
        """Initializes CommonService client and calls LogonUser method.

        Returns the User object, as returned by LogonUser.
        Also sets self.client_id for convenience.
        """
        self._init_common(args)
        if not only_common:
            self._init_clients(args)
        if hasattr(self, 'client_object'):
            return self.client_object
        try:
            res = self.common.call(
                'LogonUser', args.username, args.password, self._get_machine_ip(), "Oktawave CLI")
        except AttributeError:
            print "ERROR: Couldn't login to Oktawave."
            sys.exit(1)
        self.client_id = res._x003C_Client_x003E_k__BackingField.ClientId
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
        return [getattr(item, field) for item in data if item.LanguageDictId == 2]

    def _dict_item_name(self, data, sep=', ', field='ItemName'):
        return self._dict_names(data.DictionaryItemNames[0], field)[0]

    def _simple_vm_method(self, method, args):
        """Wraps around common simple virtual machine method call pattern"""
        self._logon(args)
        self.clients.call(method, args.id, self.client_id)
        print "OK"

    def _ocs_prepare(self, args):
        """Wrapper method for OCS/swift API initialization"""
        # swift_username = self._logon(args, only_common =
        # True)._x003C_Client_x003E_k__BackingField.VmwareFriendlyName
        self.sc = Connection(
            'https://ocs-pl.oktawave.com/auth/v1.0', args.ocs_username, args.ocs_password)
        if hasattr(args, 'path'):
            if args.path == None:
                (c, x, p) = args.container.partition('/')
                args.container = c
                if p != '':
                    args.path = p

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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        res = s.getsockname()[0]
        s.close()
        return res

    def _oci_class_id(self, class_name):
        """Returns ID of an OCI class with a given name"""
        classes = self.common.call(
            'GetDictionaryItems', DICT['OCI_CLASSES_DICT_ID'], self.client_id)
        name2id = dict([(self._dict_item_name(x), x['DictionaryItemId'])
                       for x in classes[0]])
        self._d(name2id)
        if class_name in name2id:
            return name2id[class_name]
        return 0

    # API methods below ###

    # General / Account ###

    def Account_Settings(self, args):
        """Print basic settings of the client account

        args is an object containing at least the following fields:
        - username - Oktawave username
        - password - Oktawave client password
        Typically args will be the object returned from argparse.

        """
        self._logon(args, only_common=True)
        res = {}
        client = self.client_object
        res['Time zone'] = [
            client._x003C_TimeZone_x003E_k__BackingField.DisplayName]
        res['Currency'] = [self._dict_item_name(
            client._x003C_Currency_x003E_k__BackingField)]
        res['Date format'] = [self._dict_item_name(
            client._x003C_DateFormat_x003E_k__BackingField)]
        res['Availability zone'] = [self._dict_item_name(
            self.common.call('GetDictionaryItemById', client._x003C_AvailabilityZone_x003E_k__BackingField))]
        res['24h clock'] = [
            'Yes' if client._x003C_Is24HourClock_x003E_k__BackingField else 'No']
        self._print("Account settings:")
        self.p.print_hash_table(res, ['Key', 'Value'])
        # TODO: probably print more settings

    def Account_RunningJobs(self, args):
        self._logon(args)
        res = self.common.call('GetRunningOperations', self.client_id)
        if str(res) == '':
            print "No running operations"
            return
        self.p.print_table([['Operation ID', 'Started at', 'Started by', 'Operation type', 'Object', 'Progress', 'Status']] + [[
            op.AsynchronousOperationId,
            op.CreationDate,
            op.CreationUserFullName,
            self._dict_item_name(op.OperationType),
            self._dict_item_name(op.ObjectType) + ": " + op.ObjectName,
            str(op.Progress) + "%",
            self._dict_item_name(op.Status)
        ] for op in res[0]])

    def Account_Users(self, args):
        """Print users in client account."""
        self._logon(args)
        users = self.clients.call('GetClientUsers', self.client_id)
        res = [['Client ID', 'E-mail', 'Name']]
        self._d(users)
        res.extend([[
            self.client_id,
            user._x003C_Email_x003E_k__BackingField,
            user._x003C_FullName_x003E_k__BackingField
        ] for user in users[0]])
        self.p.print_table(res)

    # OCI (VMs) ###

    def OCI_Test(self, args):
        self._logon(args)
        self._d(self._oci_class_id('Large'))

    def OCI_TemplateCategories(self, args):
        """Lists available template categories"""
        self._logon(args)
        data = self.common.call('GetTemplateCategories', self.client_id)
        self._d(data)
        tcat = [[[tc.TemplateCategoryId,
                self._dict_names(
                    tc.TemplateCategoryNames[0], 'CategoryName')[0],
                self._dict_names(
                    tc.TemplateCategoryNames[0], 'CategoryDescription')[0]
                  ], [[tcc.TemplateCategoryId,
                self._dict_names(
                    tcc.TemplateCategoryNames[0], 'CategoryName')[0],
                self._dict_names(
                    tcc.TemplateCategoryNames[0], 'CategoryDescription')[0]
                ] for tcc in ([] if tc.CategoryChildren is None else tc.CategoryChildren[0])]] for tc in data[0]]
        ht = [['Template category ID', 'Name', 'Description']]
        for mcat in tcat:
            ht.extend([mcat[0]])
            ht.extend([['  ' + str(t[0]), t[1], t[2]] for t in mcat[1]])
        self.p.print_table(ht)

    def OCI_Templates(self, args, name_filter=''):
        """Lists templates in a category"""
        self._logon(args)
        data = self.common.call(
            'GetTemplatesByCategory', args.id, None, None, self.client_id)
        try:
            res = dict((template.TemplateId, [template.TemplateName])
                       for template in data[0] if template.TemplateName.find(name_filter) != -1)
            self.p.print_hash_table(res, ['Template ID', 'Template name'])
        except IndexError:
            print "No templates in this category.\n"

    def OCI_TemplateInfo(self, args):
        """Shows more detailed info about a particular template"""
        self._logon(args)
        data = self.clients.call('GetTemplate', args.id, self.client_id)
        res = {
            '-1 Template ID': [data.TemplateId],
            '0 VM class': [self._dict_item_name(data.VMClass) + " (class ID: " + str(data.VMClass.DictionaryItemId) + ")"],
            '1 Name': [data.Name],
            '2 Template name': [data.TemplateName],
            '3 System category': [self._dict_item_name(data.TemplateSystemCategory)],
            '4 Template category': ['/'.join(self._dict_names(data.TemplateCategory.TemplateCategoryNames[0], field='CategoryName'))],
            '5 Software': [', '.join(['/'.join(self._dict_names(s.Software.SoftwareNames[0], field="Name")) for s in data.SoftwareList[0]])],
            '6 Ethernet controllers': [data.EthernetControllersCount],
            '7 Connection': [self._dict_item_name(data.ConnectionType)],
            '8 Disk drives': [', '.join([hdd.HddName + " (" + str(hdd.CapacityGB) + " GB" + (', Primary' if hdd.IsPrimary else '') + ")" for hdd in data.DiskDrives[0]])],
            '9 Description': [data.Description]
        }
        self.p.print_hash_table(res, ['Key', 'Value'], order=True)

    def OCI_List(self, args):
        """Lists client's virtual machines"""
        self._logon(args)
        sp = self._search_params(
            self.clients.create('ns3:VirtualMachineSearchParams'))
        sp.ClientId = self.client_id
        vms = self.clients.call('GetVirtualMachines', sp)
        self._d(vms)
        res = [['Virtual machine ID', 'Name', 'Class']]
        res.extend([[
            vm.VirtualMachineId,
            vm.VirtualMachineName,
            self._dict_item_name(vm.VMClass)
        ] for vm in vms._results[0]])
        self.p.print_table(res)

    def OCI_Restart(self, args):
        """Restarts given VM"""
        self._simple_vm_method('RestartVirtualMachine', args)

    def OCI_TurnOff(self, args):
        """Turns given VM off"""
        self._simple_vm_method('TurnoffVirtualMachine', args)

    def OCI_TurnOn(self, args):
        """Turns given virtual machine on"""
        self._simple_vm_method('TurnOnVirtualMachine', args)

    def OCI_Delete(self, args):
        """Deletes given virtual machine"""
        self._simple_vm_method('DeleteVirtualMachine', args)

    def OCI_Logs(self, args):
        """Shows virtual machine logs"""
        self._logon(args)
        sp = self._search_params(
            self.clients.create('ns3:VirtualMachineHistoriesSearchParams'))
        sp.VirtualMachineId = args.id
        sp.PageSize = 100
        sp.SortingDirection = 'Descending'
        data = self.clients.call(
            'GetVirtualMachineHistories', sp, self.client_id)
        self._d(data)
        res = [['Time', 'Operation type', 'User', 'Status']]
        res.extend([[
            op.CreationDate,
            self._dict_item_name(op.OperationType),
            op.CreationUser.FullName,
            self._dict_item_name(op.Status)
        ] for op in data._results[0]])
        self.p.print_table(res)

    def OCI_Settings(self, args):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        self._logon(args)
        data = self.clients.call(
            'GetVirtualMachineById', args.id, self.client_id)
        print 'Basic VM settings and statistics'
        res = {
            '0 Autoscaling': [self._dict_item_name(data.AutoScalingType)],
            '1 Connection': [self._dict_item_name(data.ConnectionType)],
            '2 CPU (MHz)': [data.CpuMhz],
            '3 CPU usage (MHz)': [data.CpuMhzUsage],
            '4 Creation date': [data.CreationDate],
            '5 Created by': [data.CreationUserSimple.FullName],
            '6 IOPS usage': [data.IopsUsage],
            '7 Last changed': [data.LastChangeDate],
            '8 Payment type': [self._dict_item_name(data.PaymentType)],
            '9 RAM (MB)': [data.RamMB],
            '10 RAM usage (MB)': [data.RamMBUsage],
            '11 Status': [self._dict_item_name(data.Status)],
            '12 Name': [data.VirtualMachineName],
            '13 Class': [self._dict_item_name(data.VMClass)]
        }
        self.p.print_hash_table(res, ['Key', 'Value'], order=True)
        disks = [[
            'Name',
            'Capacity (GB)',
            'Created at',
            'Created by',
            'Primary'
        ]]
        disks.extend([
            [
            disk.ClientHdd.HddName,
            disk.ClientHdd.CapacityGB,
            disk.ClientHdd.CreationDate,
            disk.ClientHdd.CreationUser.FullName,
            'Yes' if disk.IsPrimary else 'No'
            ] for disk in data.DiskDrives[0]
        ])
        print "Hard disks"
        self.p.print_table(disks)
        ips = [[
            'IPv4 address',
            'IPv6 address',
            'Created at',
               #			'Created by',
               'DHCP branch',
               'Gateway',
               'Status',
               #			'Primary',
               'Last changed',
               'MAC address'
               ]]
        self._d(data.IPs[0])
#		sys.exit(0)
        ips.extend([
            [
            ip.Address,
            ip.AddressV6,
            ip.CreationDate,
            #				ip.CreationUser._x003C_FullName_x003E_k__BackingField,
            ip.DhcpBranch,
            ip.Gateway,
            self._dict_item_name(ip.IPStatus),
#				'Yes' if ip.IsPrimary else 'No',
            ip.LastChangeDate,
            ip.MacAddress
            ] for ip in data.IPs[0]
        ])
        print "IP addresses"
        self.p.print_table(ips)
        if data.PrivateIpv4:
            vlans = [[
                'IPv4 address',
                'Created at',
                'MAC address'
            ]]
            vlans.extend([
                [
                vlan.PrivateIpAddress,
                vlan.CreationDate,
                vlan.MacAddress,
                ] for vlan in data.PrivateIpv4[0]
            ])
            print "Private vlans"
            self.p.print_table(vlans)
#		self._d(self.common)

    def OCI_Create(self, args, forced_type='Machine', db_type=null()):
        """Creates a new instance from template"""
        self._logon(args)
        template = self.clients.call(
            'GetTemplate', args.template, self.client_id)
        oci_class_id = null()
        if args.oci_class:
            oci_class_id = self._oci_class_id(args.oci_class)
            if not oci_class_id:
                print "OCI class not found"
                return
        self._d(self.clients.client)
        self.clients.call('CreateVirtualMachine',
                          args.template,
                          null(),
                          null(),
                          args.name,
                          oci_class_id,
                          null(),
                          DICT['OCI_PAYMENT_ID'],
                          DICT['OCI_CONNECTION_ID'],
                          self.client_id,
                          null(),
                          forced_type,
                          db_type,
                          null(),
                          DICT['OCI_AUTOSCALING_ID']
                          )
        print "OK"

    def OCI_Clone(self, args):
        """Clones a VM"""
        self._logon(args)
        self.clients.call(
            'CloneVirtualMachine', args.id, args.name, args.clonetype, self.client_id)
        print "OK"

    # OCS (storage) ###

    def OCS_ListContainers(self, args):
        """Lists containers"""
        self._ocs_prepare(args)
        account = self.sc.get_account()
        if str(account.__class__) == "<type 'tuple'>":
            account = account[1]
        self.p.print_hash_table(
            dict((o['name'], [o['count'], o['bytes']]) for o in account),
            ['Container name', 'Objects count', 'Size in bytes']
        )

    def OCS_Get(self, args):
        """Gets an object or file"""
        self._ocs_prepare(args)
        if args.path == None:
            self.p.print_swift_container(self.sc.get_container(args.container))
        else:
            self.p.print_swift_file(
                self.sc.get_object(args.container, args.path))

    def OCS_List(self, args):
        """Lists content of a directory or container"""
        self._ocs_prepare(args)
        obj = self.sc.get_container(
            args.container)  # TODO: perhaps we can optimize it not to download the whole container when not necessary
        self.p.list_swift_objects(obj, args.path, cname=args.container)

    def OCS_CreateContainer(self, args):
        """Creates a new container"""
        self._ocs_prepare(args)
        self.sc.put_container(args.name)
        print "OK"

    def OCS_CreateDirectory(self, args):
        """Creates a new directory within a container"""
        self._ocs_prepare(args)
        self.sc.put_object(
            args.container, args.path, None, content_type='application/directory')
        print "OK"

    def OCS_Put(self, args):
        """Uploads a file to the server"""
        self._ocs_prepare(args)
        fh = open(args.local_path, 'r')
        self.sc.put_object(args.container, args.path, fh)
        print "OK"

    def OCS_Delete(self, args):
        """Deletes an object from a container"""
        self._ocs_prepare(args)
        self.sc.delete_object(args.container, args.path)
        print "OK"

    def OCS_DeleteContainer(self, args):
        """Deletes a whole container"""
        self._ocs_prepare(args)
        self.sc.delete_container(args.container)
        print "OK"

    # OVS (disks) ###

    def OVS_List(self, args):
        """Lists disks"""
        self._logon(args)
        dsp = self._search_params(self.clients.create('ns3:DisksSearchParams'))
        dsp.ClientId = self.client_id
        data = self.clients.call('GetDisks', dsp)
        self.p.print_table([['ID', 'Name', 'Tier', 'Capacity', 'Used', 'Shared', 'VMs']] + [[
            disk.ClientHddId,
            disk.HddName,
            self._dict_item_name(disk.HddStandard),
            str(disk.CapacityGB) + " GB",
            str(disk.UsedCapacityGB) + " GB",
            "Yes" if disk.IsShared else "No",
            "None" if disk.VirtualMachineHdds == None else ', '.join(
            [str(hdd.VirtualMachine.VirtualMachineId) + " (" + hdd.VirtualMachine.VirtualMachineName + ")" for hdd in disk.VirtualMachineHdds[0]])
        ] for disk in data._results[0]])

    def OVS_Delete(self, args):
        """Deletes a disk"""
        self._logon(args)
        res = self.clients.call('DeleteDisk', args.id, self.client_id)
        print "OK" if res else "ERROR: Disk cannot be deleted (is it mapped to any OCI instances?)."

    def OVS_Create(self, args):
        """Adds a disk"""
        self._logon(args)
        disk = self.clients.create('ns3:ClientHddWithVMIds')
        disk.CapacityGB = args.capacity
        disk.HddName = args.name
        disk.HddStandardId = 47 + int(args.tier)
        if args.disktype == 'shared':
            disk.IsShared = True
        else:
            disk.IsShared = False
        disk.PaymentTypeId = 37
        disk.VirtualMachineIds = ''  # this seems to solve the empty-array error problem, but certainly is not nice
        self.clients.call('CreateDisk', disk, self.client_id)
        print "OK"

    def OVS_Map(self, args):
        """Maps a disk into an instance"""
        self._logon(args)
        disk = self._find_disk(args.disk_id)
        if disk == None:
            print "ERROR: No such disk found"
            return 1
        vms = [
            vm.VirtualMachine.VirtualMachineId for vm in disk.VirtualMachineHdds[0]]
        if args.oci_id in vms:
            print "ERROR: Disk is already mapped to this instance"
            return 1
        disk_mod = self.clients.create('ns3:ClientHddWithVMIds')
        for attr in ['CapacityGB', 'ClientHddId', 'HddName', 'IsShared']:
            setattr(disk_mod, attr, getattr(disk, attr))
        disk_mod.HddStandardId = disk.HddStandard.DictionaryItemId
        disk_mod.PaymentTypeId = disk.PaymentType.DictionaryItemId
        disk_mod.VirtualMachineIds = self.clients.create('ns6:ArrayOfint')
        disk_mod.VirtualMachineIds[0].extend(vms + [args.oci_id])
        res = self.clients.call('UpdateDisk', disk_mod, self.client_id)
        print "OK" if res else "ERROR: Disk cannot be mapped."

    def OVS_Unmap(self, args):
        """Unmaps a disk from an instance"""
        self._logon(args)
        disk = self._find_disk(args.disk_id)
        if disk == None:
            print "ERROR: No such disk found"
            return 1
        vms = [
            vm.VirtualMachine.VirtualMachineId for vm in disk.VirtualMachineHdds[0]]
        if not args.oci_id in vms:
            print "ERROR: Disk is not mapped to this instance"
            return 1
        print disk
        disk_mod = self.clients.create('ns3:ClientHddWithVMIds')
        for attr in ['CapacityGB', 'ClientHddId', 'HddName', 'IsShared']:
            setattr(disk_mod, attr, getattr(disk, attr))
        disk_mod.HddStandardId = disk.HddStandard.DictionaryItemId
        disk_mod.PaymentTypeId = disk.PaymentType.DictionaryItemId
        disk_mod.VirtualMachineIds = self.clients.create('ns6:ArrayOfint')
        disk_mod.VirtualMachineIds[0].extend(
            [vm for vm in vms if vm != args.oci_id])
        if len(disk_mod.VirtualMachineIds[0]) == 0:
            disk_mod.VirtualMachineIds = ''
        res = self.clients.call('UpdateDisk', disk_mod, self.client_id)
        print "OK" if res else "ERROR: Disk cannot be unmapped."

    # ORDB (databases) ###

    def ORDB_List(self, args):
        """Lists databases"""
        self._logon(args)
        sp = self._search_params(
            self.clients.create('ns3:DatabaseInstanceSearchParams'))
        sp.ClientId = self.client_id
        data = self.clients.call('GetDatabaseInstances', sp)
        self.p.print_table([['Virtual machine ID', 'Name', 'Type', 'Size', 'Available space']] + [[
            db.VirtualMachineId,
            db.VirtualMachineName,
            self._dict_item_name(db.DatabaseType),
            db.Size,
            db.AvailableSpace
        ] for db in data._results[0]])

    def ORDB_TurnOn(self, args):
        """Turns a database on"""
        self._simple_vm_method('TurnOnVirtualMachine', args)

    def ORDB_TurnOff(self, args):
        """Turns a database off"""
        self._simple_vm_method('TurnoffVirtualMachine', args)

    def ORDB_Restart(self, args):
        """Restarts a database"""
        self._simple_vm_method('RestartVirtualMachine', args)

    def ORDB_Clone(self, args):
        """Clones a database VM"""
        self.OCI_Clone(args)

    def ORDB_Delete(self, args):
        """Deletes a database or VM"""
        self._logon(args)
        if args.db_name == None:
            self._simple_vm_method('DeleteVirtualMachine', args)
        else:
            self.clients.call(
                'DeleteDatabase', args.id, args.db_name, self.client_id)

    def ORDB_Logs(self, args):
        """Shows database VM logs"""
        self.OCI_Logs(args)

    def ORDB_LogicalDatabases(self, args):
        """Shows logical databases"""
        self._logon(args)
        sp = self._search_params(
            self.clients.create('ns3:DatabaseInstanceSearchParams'))
        sp.ClientId = self.client_id
        data = self.clients.call('GetDatabaseInstances', sp)
        self.p.print_table([['Virtual machine ID', 'Name', 'Type', 'Encoding', 'Running', 'QPS', 'Size']] + list(itertools.chain.from_iterable([
            [[
             db.VirtualMachineId,
             db.DatabaseName,
             self._dict_item_name(db.DatabaseType),
             db.Encoding,
             'Yes' if db.IsRunning else 'No',
             db.QPS,
             db.Size
             ] for db in vm.Databases[0]]
            for vm in data._results[0] if (args.id == None or str(vm.VirtualMachineId) == str(args.id))])))

    def ORDB_Settings(self, args):
        """Shows database VM settings"""
        self.OCI_Settings(args)

    def ORDB_Create(self, args):
        """Creates a database VM"""
        self._logon(args)
        data = self.clients.call('GetTemplate', args.template, self.client_id)
        if str(data.TemplateType.DictionaryItemId) != str(DICT['DB_VM_CATEGORY']):
            print "ERROR: Selected template is not a database template"
            return 1
        self.OCI_Create(args,
                        forced_type='Database', db_type=data.DatabaseType.DictionaryItemId)

    def ORDB_GlobalSettings(self, args):
        """Shows global database engine settings"""
        self._logon(args)
        data = self.clients.call('GetDatabaseConfig', args.id, self.client_id)
        self.p.print_table([['Name', 'Value']] + [[
            item.Name,
            item.Value
        ] for item in data[0]])

    def ORDB_Templates(self, args):
        """Lists database VM templates"""
        print "\nCategory: MySQL"
        args.id = DICT['MYSQL_TEMPLATE_CATEGORY']
        self.OCI_Templates(args, 'ORDB')
        print "Category: PostgreSQL"
        args.id = DICT['POSTGRESQL_TEMPLATE_CATEGORY']
        self.OCI_Templates(args, 'ORDB')

    def ORDB_TemplateInfo(self, args):
        """Shows information about a template"""
        self.OCI_TemplateInfo(args, category_id=DICT['DB_VM_CATEGORY'])

    def ORDB_CreateLogicalDatabase(self, args):
        """Creates a new logical database within an instance"""
        self._logon(args)
        self.clients.call('CreateDatabase', args.id, args.name, DICT[
                          args.encoding.upper() + '_ENCODING'], self.client_id)
        print "OK"
#	def ORDB_LogicalDatabaseStats(self, args):
#		"""Shows logical database statistics"""
#		self._logon(args)
#		print "Not implemented yet"

    def ORDB_BackupLogicalDatabase(self, args):
        """Creates a backup of logical database"""
        self._logon(args)
        self.clients.call('BackupDatabase', args.id, args.name, self.client_id)
        print "OK"

    def ORDB_MoveLogicalDatabase(self, args):
        """Moves a logical database"""
        self._logon(args)
        self.clients.call(
            'MoveDatabase', args.id_from, args.id_to, args.name, self.client_id)
        print "OK"

    def ORDB_Backups(self, args):
        """Lists logical database backups"""
        self._logon(args)
        mysql_data = self.clients.call(
            'GetBackups', DICT['MYSQL_DB'], self.client_id) or [[]]
        psql_data = self.clients.call(
            'GetBackups', DICT['POSTGRESQL_DB'], self.client_id) or [[]]
        self.p.print_table([['File name', 'Database type', 'Full path']] + [[
            b._x003C_Name_x003E_k__BackingField,
            'MySQL',
            b._x003C_ContainerName_x003E_k__BackingField +
            "/" + b._x003C_FullPath_x003E_k__BackingField
        ] for b in mysql_data[0]] + [[
            b._x003C_Name_x003E_k__BackingField,
            'PostgreSQL',
            b._x003C_ContainerName_x003E_k__BackingField +
            "/" + b._x003C_FullPath_x003E_k__BackingField
        ] for b in psql_data[0]])

    def ORDB_RestoreLogicalDatabase(self, args):
        """Restores a database from backup"""
        self._logon(args)
        self.clients.call('RestoreDatabase', args.id,
                          args.name, args.backup_file, self.client_id)
        print "OK"


# MISC ####
#	def ORDB_Debug(self, args):
#		"""Lists all dictionary items, useful for debugging, but slow"""
#		self._logon(args)
#		for d in xrange(1, 100):
#			print d
#			data = self.common.call('GetDictionaryItems', d)
#			if str(data) == '':
#				continue
#			for item in data[0]:
# print "  " + str(item.DictionaryItemId) + "  " +
# self._dict_item_name(item)
