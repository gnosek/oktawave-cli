from oktawave.api import OktawaveApi, DICT as OktawaveConstants
from oktawave.exceptions import *
import sys

class OktawaveCli(OktawaveApi):

    def _logon(self, args, only_common=False):
        try:
            return super(OktawaveCli, self)._logon(args, only_common)
        except OktawaveLoginError:
            print "ERROR: Couldn't login to Oktawave."
            sys.exit(1)

    def _simple_vm_method(self, method, args):
        """Wraps around common simple virtual machine method call pattern"""
        super(OktawaveCli, self)._simple_vm_method(method, args)
        print "OK"

    def Account_Settings(self, args):
        res = super(OktawaveCli, self).Account_Settings(args)
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

    def _print_table(self, head, results, mapper_func):
        items = map(mapper_func, results)
        if items:
            self.p.print_table([head] + items)

    def Account_RunningJobs(self, args):
        ops = super(OktawaveCli, self).Account_RunningJobs(args)
        head = [['Operation ID', 'Started at', 'Started by', 'Operation type', 'Object', 'Progress', 'Status']]
        items = [[
            op['id'],
            op['creation_date'],
            op['creation_user_name'],
            op['type'],
            '%(object_type)s: %(object_name)s' % op,
            '%(progress_percent)d%%' % op,
            op['status'],
        ] for op in ops]
        if items:
            self.p.print_table(head + items)
        else:
            print "No running operations"

    def Account_Users(self, args):
        """Print users in client account."""
        users = super(OktawaveCli, self).Account_Users(args)
        res = [['Client ID', 'E-mail', 'Name']]
        res.extend([[
            self.client_id,
            user['email'],
            user['name']
        ] for user in users])
        self.p.print_table(res)

    def OCI_Test(self, args):
        super(OktawaveCli, self).OCI_Test(args)

    def OCI_TemplateCategories(self, args):
        """Lists available template categories"""
        ht = [['Template category ID', 'Name', 'Description']]
        for cat in super(OktawaveCli, self).OCI_TemplateCategories(args):
            tc_id = cat['id']
            if cat['parent_id'] is not None:
                tc_id = '  ' + str(tc_id)
            ht.append([tc_id, cat['name'], cat['description']])
        self.p.print_table(ht)

    def OCI_Templates(self, args, name_filter=''):
        """Lists templates in a category"""
        templates = super(OktawaveCli, self).OCI_Templates(args, name_filter)
        if templates:
            res = dict((k, [v]) for k, v in templates.items())
            self.p.print_hash_table(res, ['Template ID', 'Template name'])
        else:
            print "No templates in this category.\n"

    def OCI_TemplateInfo(self, args):
        """Shows more detailed info about a particular template"""
        ti = super(OktawaveCli, self).OCI_TemplateInfo(args)

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
        vms = super(OktawaveCli, self).OCI_List(args)
        res = [['Virtual machine ID', 'Name', 'Class']]
        for vm in vms:
            res.append([vm['id'], vm['name'], vm['class_name']])
        self.p.print_table(res)

    def OCI_Restart(self, args):
        """Restarts given VM"""
        super(OktawaveCli, self).OCI_Restart(args)

    def OCI_TurnOff(self, args):
        """Turns given VM off"""
        super(OktawaveCli, self).OCI_TurnOff(args)

    def OCI_TurnOn(self, args):
        """Turns given virtual machine on"""
        super(OktawaveCli, self).OCI_TurnOn(args)

    def OCI_Delete(self, args):
        """Deletes given virtual machine"""
        super(OktawaveCli, self).OCI_Delete(args)

    def OCI_Logs(self, args):
        """Shows virtual machine logs"""
        logs = super(OktawaveCli, self).OCI_Logs(args)
        res = [['Time', 'Operation type', 'User', 'Status']]
        for op in logs:
            res.append([
                op['time'],
                op['type'],
                op['user_name'],
                op['status'],
            ])
        self.p.print_table(res)

    def OCI_Settings(self, args):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        settings = super(OktawaveCli, self).OCI_Settings(args)

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

        disks = [[
            'Name',
            'Capacity (GB)',
            'Created at',
            'Created by',
            'Primary'
        ]]
        disks.extend([
            [
            disk['name'],
            disk['capacity_gb'],
            disk['creation_date'],
            disk['creation_user_name'],
            'Yes' if disk['is_primary'] else 'No'
            ] for disk in settings['disks']
        ])
        self.p._print("Hard disks")
        self.p.print_table(disks)

        ips = [[
            'IPv4 address',
            'IPv6 address',
            'Created at',
            'DHCP branch',
            'Gateway',
            'Status',
            'Last changed',
            'MAC address'
        ]]
        ips.extend([
            [
            ip['ipv4'],
            ip['ipv6'],
            ip['creation_date'],
            ip['dhcp_branch'],
            ip['gateway'],
            ip['status'],
            ip['last_change_date'],
            ip['macaddr']
            ] for ip in settings['ips']
        ])
        self.p._print("IP addresses")
        self.p.print_table(ips)

        if settings['vlans']:
            vlans = [[
                'IPv4 address',
                'Created at',
                'MAC address'
            ]]
            vlans.extend([
                [
                vlan['ipv4'],
                vlan['creation_date'],
                vlan['macaddr'],
                ] for vlan in settings['vlans']
            ])
            self.p._print("Private vlans")
            self.p.print_table(vlans)

    def OCI_Create(self, args, forced_type='Machine', db_type=None):
        """Creates a new instance from template"""
        try:
            super(OktawaveCli, self).OCI_Create(args, forced_type, db_type)
        except OktawaveOCIClassNotFound:
            print "OCI class not found"

    def OCI_Clone(self, args):
        """Clones a VM"""
        super(OktawaveCli, self).OCI_Clone(args)

    def OCS_ListContainers(self, args):
        """Lists containers"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        headers, containers = sc.get_account()
        self.p.print_hash_table(
            dict((o['name'], [o['count'], o['bytes']]) for o in containers),
            ['Container name', 'Objects count', 'Size in bytes']
        )

    def OCS_Get(self, args):
        """Gets an object or file"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        if args.path == None:
            self.p.print_swift_container(sc.get_container(args.container))
        else:
            self.p.print_swift_file(
                sc.get_object(args.container, args.path))

    def OCS_List(self, args):
        """Lists content of a directory or container"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        obj = sc.get_container(
            args.container)  # TODO: perhaps we can optimize it not to download the whole container when not necessary
        self.p.list_swift_objects(obj, args.path, cname=args.container)

    def OCS_CreateContainer(self, args):
        """Creates a new container"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        sc.put_container(args.name)
        print "OK"

    def OCS_CreateDirectory(self, args):
        """Creates a new directory within a container"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        sc.put_object(
            args.container, args.path, None, content_type='application/directory')
        print "OK"

    def OCS_Put(self, args):
        """Uploads a file to the server"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        fh = open(args.local_path, 'r')
        sc.put_object(args.container, args.path, fh)
        print "OK"

    def OCS_Delete(self, args):
        """Deletes an object from a container"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        sc.delete_object(args.container, args.path)
        print "OK"

    def OCS_DeleteContainer(self, args):
        """Deletes a whole container"""
        sc = super(OktawaveCli, self)._ocs_prepare(args)
        sc.delete_container(args.container)
        print "OK"

    def OVS_List(self, args):
        """Lists disks"""
        disks = super(OktawaveCli, self).OVS_List(args)
        disk = dict()
        self.p.print_table([['ID', 'Name', 'Tier', 'Capacity', 'Used', 'Shared', 'VMs']] + [[
            disk['id'],
            disk['name'],
            disk['tier'],
            '%d GB' % disk['capacity_gb'],
            '%d GB' % disk['used_gb'],
            'Yes' if disk['is_shared'] else 'No',
            ', '.join('%(id)d (%(name)s)' % vm for vm in disk['vms']) if disk['vms'] else 'None'
        ] for disk in disks])

    def OVS_Delete(self, args):
        """Deletes a disk"""
        try:
            super(OktawaveCli, self).OVS_Delete(args)
        except OktawaveOVSDeleteError:
            print "ERROR: Disk cannot be deleted (is it mapped to any OCI instances?)."
        else:
            print "OK"

    def OVS_Create(self, args):
        """Adds a disk"""
        super(OktawaveCli, self).OVS_Create(args)
        print "OK"

    def OVS_Map(self, args):
        """Maps a disk into an instance"""
        try:
            super(OktawaveCli, self).OVS_Map(args)
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
            super(OktawaveCli, self).OVS_Unmap(args)
        except OktawaveOVSUnmappedError:
            print "ERROR: Disk is not mapped to this instance"
            return 1
        except OktawaveOVSUnmapError:
            print "ERROR: Disk cannot be unmapped."
        else:
            print "OK"

    def ORDB_List(self, args):
        """Lists databases"""
        dbs = super(OktawaveCli, self).ORDB_List(args)
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
        super(OktawaveCli, self).ORDB_TurnOn(args)

    def ORDB_TurnOff(self, args):
        """Turns a database off"""
        super(OktawaveCli, self).ORDB_TurnOff(args)

    def ORDB_Restart(self, args):
        """Restarts a database"""
        super(OktawaveCli, self).ORDB_Restart(args)

    def ORDB_Clone(self, args):
        """Clones a database VM"""
        self.OCI_Clone(args)

    def ORDB_Delete(self, args):
        """Deletes a database or VM"""
        super(OktawaveCli, self).ORDB_Delete(args)

    def ORDB_Logs(self, args):
        """Shows database VM logs"""
        self.OCI_Logs(args)

    def ORDB_LogicalDatabases(self, args):
        """Shows logical databases"""
        dbs = super(OktawaveCli, self).ORDB_LogicalDatabases(args)
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
            super(OktawaveCli, self).ORDB_Create(args)
        except OktawaveORDBInvalidTemplateError:
            print "ERROR: Selected template is not a database template"
            return 1

    def ORDB_GlobalSettings(self, args):
        """Shows global database engine settings"""
        settings = super(OktawaveCli, self).ORDB_GlobalSettings(args)
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
        super(OktawaveCli, self).ORDB_CreateLogicalDatabase(args)
        print "OK"

    def ORDB_BackupLogicalDatabase(self, args):
        """Creates a backup of logical database"""
        super(OktawaveCli, self).ORDB_BackupLogicalDatabase(args)
        print "OK"

    def ORDB_MoveLogicalDatabase(self, args):
        """Moves a logical database"""
        super(OktawaveCli, self).ORDB_MoveLogicalDatabase(args)
        print "OK"

    def ORDB_Backups(self, args):
        """Lists logical database backups"""
        backups = super(OktawaveCli, self).ORDB_Backups(args)
        def fmt(b):
            return [b['file_name'], b['type'], b['path']]

        self._print_table(
            ['File name', 'Database type', 'Full path'],
            backups, fmt)

    def ORDB_RestoreLogicalDatabase(self, args):
        """Restores a database from backup"""
        super(OktawaveCli, self).ORDB_RestoreLogicalDatabase(args)
        print "OK"
