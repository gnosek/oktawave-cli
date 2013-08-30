from oktawave.api import OktawaveApi, OCSConnection, DICT as OktawaveConstants
from oktawave.exceptions import *
from oktawave.printer import Printer
import sys

class OktawaveCli(object):

    def __init__(self, args, debug=False, output=sys.stdout):
        self.p = Printer(output)
        self.api = OktawaveApi(
            username=args.username, password=args.password,
            debug=debug)
        self.ocs = OCSConnection(
            username=args.ocs_username, password=args.ocs_password)
        self.args = args
        try:
            self.api._logon(only_common=False)
        except OktawaveLoginError:
            print "ERROR: Couldn't login to Oktawave."
            sys.exit(1)

    def _print_table(self, head, results, mapper_func):
        items = map(mapper_func, results)
        if items:
            self.p.print_table([head] + items)
            return True
        return False

    def Account_Settings(self, args):
        res = self.api.Account_Settings()
        tab = [
            ['Key', 'Value'],
            ['Time zone', res['time_zone']],
            ['Currency', res['currency']],
            ['Date format', res['date_format']],
            ['Availability zone', res['availability_zone']],
            ['24h clock', 'Yes' if res['24h_clock'] else 'No']
        ]
        self.p._print("Account settings:")
        self.p.print_table(tab)

    def Account_RunningJobs(self, args):
        ops = self.api.Account_RunningJobs()
        def fmt(op):
            return [
                op['id'],
                op['creation_date'],
                op['creation_user_name'],
                op['type'],
                '%(object_type)s: %(object_name)s' % op,
                '%(progress_percent)d%%' % op,
                op['status']
            ]
        if not self._print_table(
            ['Operation ID', 'Started at', 'Started by', 'Operation type', 'Object', 'Progress', 'Status'],
            ops, fmt):
            print "No running operations"

    def Account_Users(self, args):
        """Print users in client account."""
        users = self.api.Account_Users()
        def fmt(user):
            return [
                self.api.client_id,
                user['email'],
                user['name']
            ]

        self._print_table(
            ['Client ID', 'E-mail', 'Name'],
            users, fmt)

    def OCI_Test(self, args):
        self.api.OCI_Test()

    def OCI_TemplateCategories(self, args):
        """Lists available template categories"""
        cats = self.api.OCI_TemplateCategories()
        def fmt(cat):
            tc_id = cat['id']
            if cat['parent_id'] is not None:
                tc_id = '  ' + str(tc_id)
            return [tc_id, cat['name'], cat['description']]

        self._print_table(
            ['Template category ID', 'Name', 'Description'],
            cats, fmt)

    def OCI_Templates(self, args, name_filter=''):
        """Lists templates in a category"""
        templates = self.api.OCI_Templates(args.id, name_filter)
        if templates:
            res = dict((k, [v]) for k, v in templates.items())
            self.p.print_hash_table(res, ['Template ID', 'Template name'])
        else:
            print "No templates in this category.\n"

    def OCI_TemplateInfo(self, args):
        """Shows more detailed info about a particular template"""
        ti = self.api.OCI_TemplateInfo(args.id)

        def _hdd_label(hdd):
            if hdd['is_primary']:
                return '%(name)s (%(capacity_gb)d GB, Primary)' % hdd
            else:
                return '%(name)s (%(capacity_gb)d GB)' % hdd

        tab = [['Key', 'Value']]
        tab.extend([
            ['Template ID', ti['template_id']],
            ['VM class', '%s (class ID: %s)' % (ti['vm_class_name'], ti['vm_class_id'])],
            ['Name', ti['label']],
            ['Template name', ti['template_name']],
            ['System category', ti['system_category_name']],
            ['Template category', ti['template_category']],
            ['Software', ti['software']],
            ['Ethernet controllers', ti['eth_count']],
            ['Connection', ti['connection_type']],
            ['Disk drives', ', '.join(_hdd_label(hdd) for hdd in ti['disks'])],
            ['Description', ti['description']],
            ])
        self.p.print_table(tab)

    def OCI_List(self, args):
        """Lists client's virtual machines"""
        vms = self.api.OCI_List()
        def fmt(vm):
            return [vm['id'], vm['name'], vm['class_name']]

        self._print_table(
            ['Virtual machine ID', 'Name', 'Class'], vms, fmt)

    def OCI_Restart(self, args):
        """Restarts given VM"""
        self.api.OCI_Restart(args.id)

    def OCI_TurnOff(self, args):
        """Turns given VM off"""
        self.api.OCI_TurnOff(args.id)

    def OCI_TurnOn(self, args):
        """Turns given virtual machine on"""
        self.api.OCI_TurnOn(args.id)

    def OCI_Delete(self, args):
        """Deletes given virtual machine"""
        self.api.OCI_Delete(args.id)

    def OCI_Logs(self, args):
        """Shows virtual machine logs"""
        logs = self.api.OCI_Logs(args.id)
        def fmt(op):
            return [
                op['time'],
                op['type'],
                op['user_name'],
                op['status'],
            ]

        self._print_table(
            ['Time', 'Operation type', 'User', 'Status'],
            logs, fmt)

    def OCI_Settings(self, args):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        settings = self.api.OCI_Settings(args.id)

        base_tab = [['Key', 'Value']]
        base_tab.extend([
            ['Autoscaling', settings['autoscaling']],
            ['Connection', settings['connection_type']],
            ['CPU (MHz)', settings['cpu_mhz']],
            ['CPU usage (MHz)', settings['cpu_usage_mhz']],
            ['Creation date', settings['creation_date']],
            ['Created by', settings['creation_user_name']],
            ['IOPS usage', settings['iops_usage']],
            ['Last changed', settings['last_change_date']],
            ['Payment type', settings['payment_type']],
            ['RAM (MB)', settings['memory_mb']],
            ['RAM usage (MB)', settings['memory_usage_mb']],
            ['Status', settings['status']],
            ['Name', settings['name']],
            ['Class', settings['vm_class_name']]
        ])
        self.p._print('Basic VM settings and statistics')
        self.p.print_table(base_tab)

        def fmt_disk(disk):
            return [
                disk['name'],
                disk['capacity_gb'],
                disk['creation_date'],
                disk['creation_user_name'],
                'Yes' if disk['is_primary'] else 'No'
            ]
        self.p._print("Hard disks")
        self._print_table(
            ['Name', 'Capacity (GB)', 'Created at', 'Created by', 'Primary'],
            settings['disks'], fmt_disk)

        def fmt_ip(ip):
            return [
                ip['ipv4'] + '/' + ip['netmask'],
                ip['ipv6'],
                ip['creation_date'],
                ip['dhcp_branch'],
                ip['gateway'],
                ip['status'],
                ip['last_change_date'],
                ip['macaddr']
            ]
        self.p._print("IP addresses")
        self._print_table([
            'IPv4 address',
            'IPv6 address',
            'Created at',
            'DHCP branch',
            'Gateway',
            'Status',
            'Last changed',
            'MAC address'
        ], settings['ips'], fmt_ip)

        if settings['vlans']:
            self.p._print("Private vlans")
            def fmt_vlan(vlan):
                return [
                    vlan['ipv4'],
                    vlan['creation_date'],
                    vlan['macaddr'],
                ]

            self._print_table(
                ['IPv4 address', 'Created at', 'MAC address'],
                settings['vlans'], fmt_vlan)

    def OCI_Create(self, args, forced_type='Machine', db_type=None):
        """Creates a new instance from template"""
        try:
            self.api.OCI_Create(args.name, args.template, args.oci_class, forced_type, db_type)
        except OktawaveOCIClassNotFound:
            print "OCI class not found"

    def OCI_ChangeClass(self, args):
        """Changes running VM class"""
        self.api.OCI_ChangeClass(args.id, args.oci_class)

    def OCI_Clone(self, args):
        """Clones a VM"""
        self.api.OCI_Clone(args.id, args.name, args.clonetype)

    def _ocs_split_params(self, args):
        container = args.container
        path = args.path
        if path is None:
            container, _slash, path = container.partition('/')
            if path == '':
                path = None
        return container, path

    def OCS_ListContainers(self, args):
        """Lists containers"""
        headers, containers = self.ocs.get_account()
        self.p.print_hash_table(
            dict((o['name'], [o['count'], o['bytes']]) for o in containers),
            ['Container name', 'Objects count', 'Size in bytes']
        )

    def OCS_Get(self, args):
        """Gets an object or file"""
        container, path = self._ocs_split_params(args)
        if path is None:
            self.p.print_swift_container(self.ocs.get_container(container))
        else:
            self.p.print_swift_file(
                self.ocs.get_object(container, path))

    def OCS_List(self, args):
        """Lists content of a directory or container"""
        container, path = self._ocs_split_params(args)
        obj = self.ocs.get_container(
            container)  # TODO: perhaps we can optimize it not to download the whole container when not necessary
        self.p.list_swift_objects(obj, path, cname=container)

    def OCS_CreateContainer(self, args):
        """Creates a new container"""
        container, path = self._ocs_split_params(args)
        self.ocs.put_container(name)
        print "OK"

    def OCS_CreateDirectory(self, args):
        """Creates a new directory within a container"""
        container, path = self._ocs_split_params(args)
        self.ocs.put_object(
            container, path, None, content_type='application/directory')
        print "OK"

    def OCS_Put(self, args):
        """Uploads a file to the server"""
        container, path = self._ocs_split_params(args)
        fh = open(local_path, 'r')
        self.ocs.put_object(container, path, fh)
        print "OK"

    def OCS_Delete(self, args):
        """Deletes an object from a container"""
        container, path = self._ocs_split_params(args)
        self.ocs.delete_object(container, path)
        print "OK"

    def OCS_DeleteContainer(self, args):
        """Deletes a whole container"""
        container, path = self._ocs_split_params(args)
        self.ocs.delete_container(container)
        print "OK"

    def OVS_List(self, args):
        """Lists disks"""
        disks = self.api.OVS_List()
        def fmt(disk):
            return [
                disk['id'],
                disk['name'],
                disk['tier'],
                '%d GB' % disk['capacity_gb'],
                '%d GB' % disk['used_gb'],
                'Yes' if disk['is_shared'] else 'No',
                ', '.join('%(id)d (%(name)s)' % vm for vm in disk['vms']) if disk['vms'] else 'None'
            ]

        self._print_table(
            ['ID', 'Name', 'Tier', 'Capacity', 'Used', 'Shared', 'VMs'],
            disks, fmt)

    def OVS_Delete(self, args):
        """Deletes a disk"""
        try:
            self.api.OVS_Delete(args.id)
        except OktawaveOVSDeleteError:
            print "ERROR: Disk cannot be deleted (is it mapped to any OCI instances?)."
        else:
            print "OK"

    def OVS_Create(self, args):
        """Adds a disk"""
        self.api.OVS_Create(args.name, args.capacity, args.tier, (args.disktype=='shared'))
        print "OK"

    def OVS_Map(self, args):
        """Maps a disk into an instance"""
        try:
            self.api.OVS_Map(args.disk_id, args.oci_id)
        except OktawaveOVSMappedError:
            print "ERROR: Disk is already mapped to this instance"
            return 1
        except OktawaveOVSMapError:
            print "ERROR: Disk cannot be mapped."
        else:
            print "OK"

    def OVS_Unmap(self, args):
        """Unmaps a disk from an instance"""
        try:
            self.api.OVS_Unmap(args.disk_id, args.oci_id)
        except OktawaveOVSUnmappedError:
            print "ERROR: Disk is not mapped to this instance"
            return 1
        except OktawaveOVSUnmapError:
            print "ERROR: Disk cannot be unmapped."
        else:
            print "OK"

    def ORDB_List(self, args):
        """Lists databases"""
        dbs = self.api.ORDB_List()
        def fmt(db):
            return [
                db['id'],
                db['name'],
                db['type'],
                db['size'],
                db['available_space']
            ]
        self._print_table(
            ['Virtual machine ID', 'Name', 'Type', 'Size', 'Available space'],
            dbs, fmt)

    def ORDB_TurnOn(self, args):
        """Turns a database on"""
        self.api.ORDB_TurnOn(args.id)

    def ORDB_TurnOff(self, args):
        """Turns a database off"""
        self.api.ORDB_TurnOff(args.id)

    def ORDB_Restart(self, args):
        """Restarts a database"""
        self.api.ORDB_Restart(args.id)

    def ORDB_Clone(self, args):
        """Clones a database VM"""
        self.OCI_Clone(args)

    def ORDB_Delete(self, args):
        """Deletes a database or VM"""
        self.api.ORDB_Delete(args.id, args.db_name)

    def ORDB_Logs(self, args):
        """Shows database VM logs"""
        self.OCI_Logs()

    def ORDB_LogicalDatabases(self, args):
        """Shows logical databases"""
        dbs = self.api.ORDB_LogicalDatabases(args.id)
        def fmt(db):
            return [
                db['id'],
                db['name'],
                db['type'],
                db['encoding'],
                'Yes' if db['is_running'] else 'No',
                db['QPS'],
                db['Size']
            ]
        self._print_table(
            ['Virtual machine ID', 'Name', 'Type', 'Encoding', 'Running', 'QPS', 'Size'],
            dbs, fmt)

    def ORDB_Settings(self, args):
        """Shows database VM settings"""
        self.OCI_Settings(args)

    def ORDB_Create(self, args):
        """Creates a database VM"""
        try:
            self.api.ORDB_Create(args.name, args.template, args.oci_class)
        except OktawaveORDBInvalidTemplateError:
            print "ERROR: Selected template is not a database template"
            return 1

    def ORDB_GlobalSettings(self, args):
        """Shows global database engine settings"""
        settings = self.api.ORDB_GlobalSettings(args.id)
        def fmt(item):
            return [item['name'], item['value']]
        self._print_table(['Name', 'Value'], settings, fmt)

    def ORDB_Templates(self, args):
        """Lists database VM templates"""
        print "\nCategory: MySQL"
        args.id = OktawaveConstants['MYSQL_TEMPLATE_CATEGORY']
        self.OCI_Templates(args, 'ORDB')
        print "Category: PostgreSQL"
        args.id = OktawaveConstants['POSTGRESQL_TEMPLATE_CATEGORY']
        self.OCI_Templates(args, 'ORDB')

    def ORDB_TemplateInfo(self, args):
        """Shows information about a template"""
        self.OCI_TemplateInfo(args, category_id=OktawaveConstants['DB_VM_CATEGORY'])

    def ORDB_CreateLogicalDatabase(self, args):
        """Creates a new logical database within an instance"""
        self.api.ORDB_CreateLogicalDatabase(args.id, args.name, args.encoding)
        print "OK"

    def ORDB_BackupLogicalDatabase(self, args):
        """Creates a backup of logical database"""
        self.api.ORDB_BackupLogicalDatabase(args.id, args.name)
        print "OK"

    def ORDB_MoveLogicalDatabase(self, args):
        """Moves a logical database"""
        self.api.ORDB_MoveLogicalDatabase(args.id_from, args.id_to, args.name)
        print "OK"

    def ORDB_Backups(self, args):
        """Lists logical database backups"""
        backups = self.api.ORDB_Backups()
        def fmt(b):
            return [b['file_name'], b['type'], b['path']]

        self._print_table(
            ['File name', 'Database type', 'Full path'],
            backups, fmt)

    def ORDB_RestoreLogicalDatabase(self, args):
        """Restores a database from backup"""
        self.api.ORDB_RestoreLogicalDatabase(args.id, args.name, args.backup_file)
        print "OK"
