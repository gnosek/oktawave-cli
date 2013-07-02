from oktawave.api import (
    OktawaveApi,
    OktawaveLoginError,
    OktawaveOCIClassNotFound,
    )
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
