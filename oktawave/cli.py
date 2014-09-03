import sys
import os

from oktawave.api import (
    OktawaveApi,
    OCSConnection,
    DICT as OktawaveConstants,
    CloneType,
    TemplateType,
    PowerStatus
)
from oktawave.exceptions import *
from oktawave.printer import Printer


class OktawaveNameNotFound(ValueError):
    pass


class OktawaveDuplicateName(ValueError):
    pass


class NamedItemId(object):
    def __init__(self, item_id):
        self.item_id = item_id

    @classmethod
    def list_items(cls, api):
        raise NotImplementedError()

    def as_int(self, api):
        try:
            return int(self.item_id)
        except ValueError:
            pass

        found_item_id = None
        for item_id, item_name in self.list_items(api):
            if item_name == self.item_id:
                if found_item_id is not None:
                    raise OktawaveDuplicateName()
                found_item_id = item_id

        if found_item_id is None:
            raise OktawaveNameNotFound()

        return found_item_id


class OCIid(NamedItemId):
    @classmethod
    def list_items(cls, api):
        for item in api.OCI_List():
            yield item['id'], item['name']


class ORDBid(NamedItemId):
    @classmethod
    def list_items(cls, api):
        for item in api.ORDB_List():
            yield item['id'], item['name']


class OPNid(NamedItemId):
    @classmethod
    def list_items(cls, api):
        for item in api.OPN_List():
            yield item['id'], item['name']


class OVSid(NamedItemId):
    @classmethod
    def list_items(cls, api):
        for item in api.OVS_List():
            yield item['id'], item['name']


class ContainerId(NamedItemId):
    @classmethod
    def list_items(cls, api):
        for item in api.Container_List():
            yield item['id'], item['name']


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

    def _name_to_id(self, name_or_id):
        if isinstance(name_or_id, int):
            return name_or_id
        return name_or_id.as_int(self.api)

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

    def OCI_TemplateCategories(self, args):
        """Lists available template categories"""
        cats = self.api.OCI_TemplateCategories()

        def fmt(cat):
            tc_id = cat.id
            if cat.parent_id is not None:
                tc_id = '  ' + str(tc_id)
            return [tc_id, cat.name, cat.description]

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
            ['Software', ', '.join(str(s) for s in ti['software'])],
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
            return [vm['id'], vm['name'], vm['status']]

        self._print_table(
            ['Virtual machine ID', 'Name', 'Status'], vms, fmt)

    def OCI_ListDetails(self, args):
        """Lists client's virtual machines"""
        vms = self.api.OCI_ListDetails()

        def fmt(vm):
            return [vm['id'], vm['name'], vm['status'], vm['class_name'],
                    '%d/%d MHz' % (vm['cpu_usage_mhz'], vm['cpu_mhz']),
                    '%d/%d MB' % (vm['memory_usage_mb'], vm['memory_mb'])]

        self._print_table(
            ['Virtual machine ID', 'Name', 'Status', 'Class', 'CPU', 'Memory'], vms, fmt)

    def OCI_Restart(self, args):
        """Restarts given VM"""
        oci_id = self._name_to_id(args.id)
        self.api.OCI_Restart(oci_id)

    def OCI_TurnOff(self, args):
        """Turns given VM off"""
        oci_id = self._name_to_id(args.id)
        self.api.OCI_TurnOff(oci_id)

    def OCI_TurnOn(self, args):
        """Turns given virtual machine on"""
        oci_id = self._name_to_id(args.id)
        self.api.OCI_TurnOn(oci_id)

    def OCI_Delete(self, args):
        """Deletes given virtual machine"""
        oci_id = self._name_to_id(args.id)
        self.api.OCI_Delete(oci_id)

    def OCI_Logs(self, args):
        """Shows virtual machine logs"""
        oci_id = self._name_to_id(args.id)
        logs = self.api.OCI_Logs(oci_id)

        def fmt(op):
            return [
                op['time'],
                op['type'],
                op['user_name'],
                op['status'],
                ' '.join(op['parameters'])
            ]

        self._print_table(
            ['Time', 'Operation type', 'User', 'Status', 'Parameters'],
            logs, fmt)

    def OCI_Settings(self, args):
        """Shows basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
        oci_id = self._name_to_id(args.id)
        settings = self.api.OCI_Settings(oci_id)

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
                disk['id'],
                disk['name'],
                disk['capacity_gb'],
                disk['creation_date'],
                disk['creation_user_name'],
                'Yes' if disk['is_primary'] else 'No',
                'Yes' if disk['is_shared'] else 'No'
            ]

        self.p._print("Hard disks")
        self._print_table(
            ['ID', 'Name', 'Capacity (GB)', 'Created at', 'Created by', 'Primary', 'Shared'],
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
        forced_type = getattr(TemplateType, forced_type)
        if not args.oci_class:
            args.oci_class = None
        try:
            self.api.OCI_Create(args.name, args.template, args.oci_class, forced_type, db_type, args.subregion)
        except OktawaveOCIClassNotFound:
            print "OCI class not found"

    def OCI_ChangeClass(self, args):
        """Changes running VM class"""
        oci_id = self._name_to_id(args.id)
        self.api.OCI_ChangeClass(oci_id, args.oci_class)

    def OCI_Clone(self, args):
        """Clones a VM"""
        oci_id = self._name_to_id(args.id)
        clonetype = getattr(CloneType, args.clonetype)
        self.api.OCI_Clone(oci_id, args.name, clonetype)

    def _oci_ip(self, oci_id):
        settings = self.api.OCI_Settings(oci_id)
        return settings['ips'][0]['ipv4']

    def OCI_ping(self, args):
        oci_id = self._name_to_id(args.id)
        ip = self._oci_ip(oci_id)
        os.execvp('ping', ('ping', ip) + tuple(args.exec_args))

    def OCI_ssh(self, args):
        oci_id = self._name_to_id(args.id)
        ip = self._oci_ip(oci_id)
        print 'Default OCI password: %s' % self.api.OCI_DefaultPassword(oci_id)
        remote = '%s@%s' % (args.user, ip)
        os.execvp('ssh', ('ssh', remote) + tuple(args.exec_args))

    def OCI_ssh_copy_id(self, args):
        oci_id = self._name_to_id(args.id)
        ip = self._oci_ip(oci_id)
        print 'Default OCI password: %s' % self.api.OCI_DefaultPassword(oci_id)
        remote = '%s@%s' % (args.user, ip)
        os.execvp('ssh-copy-id', ('ssh-copy-id', remote) + tuple(args.exec_args))

    def _ocs_split_params(self, args):
        container = args.container
        path = args.path
        if path is None:
            container, _slash, path = container.partition('/')
            if path == '':
                path = None
        return container, path

    @classmethod
    def _swift_object_type(cls, data):
        if data['content_type'] == 'application/directory':
            return 'directory'
        if data['content_type'] == 'application/object':
            return 'object'
        return data['content_type']

    def _list_swift_objects(self, container, cname, path=None):
        if path is None:
            path = ''
        elif not path.endswith('/'):
            path += '/'
        container = container[1]

        if path:
            for d in container:
                if d['content_type'] == 'application/directory' and d['name'] + '/' == path:
                    print 'Directory content:'
                    break
            else:
                print "No such container/directory!"
                return
        else:
            print 'Container content:'

        def fmt_file(swift_obj):
            return [
                cname + '/' + swift_obj['name'],
                self._swift_object_type(swift_obj),
                swift_obj['bytes'],
                swift_obj['last_modified'],
            ]

        self._print_table(
            ['Full path', 'Type', 'Size in bytes', 'Last modified'],
            sorted([o for o in container if o['name'].startswith(path)], key=lambda row: row['name']),
            fmt_file)

    def _print_swift_file(self, data):
        headers, content = data
        ctype = headers['content-type']

        if ctype == 'application/directory':
            print '<DIRECTORY>'
        elif ctype == 'application/object':
            attrs = dict((key[len('x-object-meta-'):], headers[key])
                         for key in headers if key.startswith('x-object-meta-'))
            self.p.print_table([['Key', 'Value']] + [[
                key,
                attrs[key]
            ] for key in sorted(attrs.keys(), key=lambda x: x.lower())])
        else:
            print content

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
            headers, contents = self.ocs.get_container(container)
            self.p.print_hash_table(
                {
                    '1 Container name': [container],
                    '2 Objects count': [headers['x-container-object-count']],
                    '3 Size in bytes': [headers['x-container-bytes-used']],
                },
                order=True)
        else:
            self._print_swift_file(
                self.ocs.get_object(container, path))

    def OCS_List(self, args):
        """Lists content of a directory or container"""
        container, path = self._ocs_split_params(args)
        obj = self.ocs.get_container(
            container)  # TODO: perhaps we can optimize it not to download the whole container when not necessary
        self._list_swift_objects(obj, container, path)

    def OCS_CreateContainer(self, args):
        """Creates a new container"""
        self.ocs.put_container(args.name)
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
        fh = open(args.local_path, 'r')
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

        def fmt_mapping(mapping):
            ovs_id = mapping['id']
            name = mapping['name']
            if mapping['primary']:
                tags = 'primary',
            else:
                tags = ()
            if mapping['vm_status'].status == PowerStatus.PowerOn:
                tags += 'powered on',
            if tags:
                tag = ': ' + ', '.join(tags)
            else:
                tag = ''
            return u'{0} ({1}{2})'.format(ovs_id, name, tag)

        def fmt(disk):
            return [
                disk['id'],
                disk['name'],
                disk['tier'],
                '%d GB' % disk['capacity_gb'],
                '%d GB' % disk['used_gb'],
                'Yes' if disk['is_shared'] else 'No',
                '\n'.join(fmt_mapping(vm) for vm in disk['vms']) if disk['vms'] else ''
            ]

        self._print_table(
            ['ID', 'Name', 'Tier', 'Capacity', 'Used', 'Shared', 'VMs'],
            disks, fmt)

    def OVS_Delete(self, args):
        """Deletes a disk"""
        ovs_id = self._name_to_id(args.id)
        try:
            self.api.OVS_Delete(ovs_id)
        except OktawaveOVSDeleteError:
            print "ERROR: Disk cannot be deleted (is it mapped to any OCI instances?)."
        else:
            print "OK"

    def OVS_Create(self, args):
        """Adds a disk"""
        self.api.OVS_Create(args.name, args.capacity, args.tier, (args.disktype == 'shared'), args.subregion)
        print "OK"

    def OVS_Map(self, args):
        """Maps a disk into an instance"""
        ovs_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        try:
            self.api.OVS_Map(ovs_id, oci_id)
        except OktawaveOVSMappedError:
            print "ERROR: Disk is already mapped to this instance"
            return 1
        except OktawaveOVSMapError:
            print "ERROR: Disk cannot be mapped."
        else:
            print "OK"

    def OVS_Unmap(self, args):
        """Unmaps a disk from an instance"""
        ovs_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        try:
            self.api.OVS_Unmap(ovs_id, oci_id)
        except OktawaveOVSUnmappedError:
            print "ERROR: Disk is not mapped to this instance"
            return 1
        except OktawaveOVSUnmapError:
            print "ERROR: Disk cannot be unmapped."
        else:
            print "OK"

    def OVS_ChangeTier(self, args):
        """Changes OVS tier"""
        ovs_id = self._name_to_id(args.id)
        self.api.OVS_ChangeTier(ovs_id, args.tier)
        print "OK"

    def OVS_Extend(self, args):
        """Resizes OVS volume"""
        ovs_id = self._name_to_id(args.id)
        try:
            self.api.OVS_Extend(ovs_id, args.size)
        except OktawaveOVSMappedError:
            print "ERROR: Disk is mapped to an instance"
            return 1
        except OktawaveOVSTooSmallError:
            print "ERROR: Requested size smaller than current size"
            return 1
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
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_TurnOn(oci_id)

    def ORDB_TurnOff(self, args):
        """Turns a database off"""
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_TurnOff(oci_id)

    def ORDB_Restart(self, args):
        """Restarts a database"""
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_Restart(oci_id)

    def ORDB_Clone(self, args):
        """Clones a database VM"""
        self.OCI_Clone(args)

    def ORDB_Delete(self, args):
        """Deletes a database or VM"""
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_Delete(oci_id, args.db_name)

    def ORDB_Logs(self, args):
        """Shows database VM logs"""
        self.OCI_Logs(args)

    def ORDB_LogicalDatabases(self, args):
        """Shows logical databases"""
        oci_id = self._name_to_id(args.id)
        dbs = self.api.ORDB_LogicalDatabases(oci_id)

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
            self.api.ORDB_Create(args.name, args.template, oci_class=args.oci_class, subregion=args.subregion)
        except OktawaveORDBInvalidTemplateError:
            print "ERROR: Selected template is not a database template"
            return 1

    def ORDB_GlobalSettings(self, args):
        """Shows global database engine settings"""
        oci_id = self._name_to_id(args.id)
        settings = self.api.ORDB_GlobalSettings(oci_id)

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
        self.OCI_TemplateInfo(args)

    def ORDB_CreateLogicalDatabase(self, args):
        """Creates a new logical database within an instance"""
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_CreateLogicalDatabase(oci_id, args.name, args.encoding)
        print "OK"

    def ORDB_BackupLogicalDatabase(self, args):
        """Creates a backup of logical database"""
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_BackupLogicalDatabase(oci_id, args.name)
        print "OK"

    def ORDB_MoveLogicalDatabase(self, args):
        """Moves a logical database"""
        oci_id_from = self._name_to_id(args.id_from)
        oci_id_to = self._name_to_id(args.id_to)
        self.api.ORDB_MoveLogicalDatabase(oci_id_from, oci_id_to, args.name)
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
        oci_id = self._name_to_id(args.id)
        self.api.ORDB_RestoreLogicalDatabase(oci_id, args.name, args.backup_file)
        print "OK"

    def Container_List(self, args):
        """Lists client's containers"""
        containers = self.api.Container_List()

        def fmt(c):
            return [c['id'], c['name'], c['vms']]

        self._print_table(
            ['Container ID', 'Name', 'VMs'], containers, fmt)

    def Container_Get(self, args):
        """Displays a container's information"""
        container_id = self._name_to_id(args.id)
        c = self.api.Container_Get(container_id)

        base_tab = [['Key', 'Value']]
        base_tab.extend([
            ['ID', c['id']],
            ['Name', c['name']],
            ['Autoscaling', c['autoscaling']],
            ['Healthcheck', 'Yes' if c['healthcheck'] else 'No'],
            ['Load balancer', 'Yes' if c['load_balancer'] else 'No'],
            ['Schedulers', c['schedulers']],
            ['Virtual machines', c['vms']],
        ])
        if c['load_balancer']:
            base_tab.extend([
                ['IP version', c['ip_version']],
                ['Load balancer algorithm', c['load_balancer_algorithm']],
                ['Proxy cache', 'Yes' if c['proxy_cache'] else 'No'],
                ['SSL enabled', 'Yes' if c['ssl'] else 'No'],
                ['Service', c['service'] + ' (' + str(c['port']) + ')' if c['service'] == 'Port' else c['service']],
                ['Session type', c['session_type']],
            ])
            ipv4 = '\n'.join(ip['ipv4'] for ip in c['ips'])
            ipv6 = '\n'.join(ip['ipv6'] for ip in c['ips'])
            base_tab.append(['IPv4 addresses', ipv4])
            base_tab.append(['IPv6 addresses', ipv6])
        if c['master_service_id'] is not None:
            base_tab.extend(
                [['Master OCI (MySQL)', c['master_service_name'] + ' (' + str(c['master_service_id']) + ')']])
        if c['db_user'] is not None:
            base_tab.extend([['Database user', c['db_user']]])
        if c['db_password'] is not None:
            base_tab.extend([['Database password', c['db_password']]])
        self.p._print('\nBasic container settings')
        self.p.print_table(base_tab)

        oci_list = self.api.Container_OCIList(container_id)

        def fmt_oci(oci):
            return [oci['oci_id'], oci['oci_name'], oci['status']]

        self.p._print('\nAttached OCIs')
        self._print_table(
            ['ID', 'Name', 'Status'], oci_list, fmt_oci)

    def Container_RemoveOCI(self, args):
        """Removes an OCI from a container"""
        container_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        self.api.Container_RemoveOCI(container_id, oci_id)
        print "OK"

    def Container_AddOCI(self, args):
        """Adds an OCI to a container"""
        container_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        self.api.Container_AddOCI(container_id, oci_id)
        print "OK"

    def Container_Delete(self, args):
        """Deletes a container"""
        container_id = self._name_to_id(args.id)
        self.api.Container_Delete(container_id)
        print "OK"

    def Container_Create(self, args):
        """Creates a new container"""
        self.api._d(args)
        container_id = self.api.Container_Create(
            args.name, args.load_balancer, args.service, args.port, args.proxy_cache,
            args.use_ssl, args.healthcheck, args.mysql_master_id, args.session_persistence,
            args.load_balancer_algorithm, args.ip_version, args.autoscaling
        )
        print "OK, new container ID: " + str(container_id) + "."

    def Container_Edit(self, args):
        """Modifies a container."""
        self.api._d(args)
        container_id = self._name_to_id(args.id)
        self.api.Container_Edit(
            container_id, args.name, args.load_balancer, args.service, args.port, args.proxy_cache,
            args.use_ssl, args.healthcheck, args.mysql_master_id, args.session_persistence,
            args.load_balancer_algorithm, args.ip_version, args.autoscaling
        )
        print "OK"

    def OPN_List(self, args):
        """Lists client's private networks"""
        vlans = self.api.OPN_List()

        def fmt(c):
            return [c['id'], c['name'], c['address_pool'], c['payment_type']]

        self._print_table(
            ['OPN ID', 'Name', 'Address pool', 'Payment type'], vlans, fmt)

    def OPN_Get(self, args):
        """Displays an OPN"""
        opn_id = self._name_to_id(args.id)
        c = self.api.OPN_Get(opn_id)

        base_tab = [['Key', 'Value']]
        base_tab.extend([
            ['ID', c['id']],
            ['Name', c['name']],
            ['Address pool', c['address_pool']],
            ['Payment type', c['payment_type']]
        ])
        self.p._print('\nBasic OPN settings')
        self.p.print_table(base_tab)
        vm_tab = [['OCI ID', 'Name', 'MAC address', 'Private IP address']]
        vm_tab.extend([[
            vm['VirtualMachine']['VirtualMachineId'],
            vm['VirtualMachine']['VirtualMachineName'],
            vm['MacAddress'],
            vm['PrivateIpAddress']
        ] for vm in c['vms']])
        self.p._print('Virtual machines')
        self.p.print_table(vm_tab)

    def OPN_Create(self, args):
        """Creates a new OPN"""
        self.api.OPN_Create(args.name, args.address_pool)
        print "OK"

    def OPN_AddOCI(self, args):
        """Adds an OCI to an OPN"""
        opn_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        self.api.OPN_AddOCI(opn_id, oci_id, args.ip_address)
        print "OK"

    def OPN_RemoveOCI(self, args):
        """Removes an OCI from an OPN"""
        opn_id = self._name_to_id(args.id)
        oci_id = self._name_to_id(args.oci_id)
        self.api.OPN_RemoveOCI(opn_id, oci_id)
        print "OK"

    def OPN_Delete(self, args):
        """Deletes a private network."""
        opn_id = self._name_to_id(args.id)
        self.api.OPN_Delete(opn_id)
        print "OK"

    def OPN_Rename(self, args):
        """Changes an OPN's name"""
        opn_id = self._name_to_id(args.id)
        self.api.OPN_Rename(opn_id, args.name)
        print "OK"

