def show_template_category(ctx, category_id, name_filter=''):
    templates = ctx.api.OCI_Templates(category_id, name_filter)
    if templates:
        res = dict((k, [v]) for k, v in templates.items())
        ctx.p.print_hash_table(res, ['Template ID', 'Template name'])
    else:
        print "No templates in this category.\n"


def show_oci_logs(ctx, id):
    logs = ctx.api.OCI_Logs(id)

    def fmt(op):
        return [
            op['time'],
            op['type'],
            op['user_name'],
            op['status'],
            ' '.join(op['parameters'])
        ]

    ctx.print_table(
        ['Time', 'Operation type', 'User', 'Status', 'Parameters'],
        logs, fmt)


def show_oci_settings(ctx, id):
    settings = ctx.api.OCI_Settings(id)
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
    ctx.p.print_str('Basic VM settings and statistics')
    ctx.p.print_table(base_tab)

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

    ctx.p.print_str("Hard disks")
    ctx.print_table(
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

    ctx.p.print_str("IP addresses")
    ctx.print_table([
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
        ctx.p.print_str("Private vlans")

        def fmt_vlan(vlan):
            return [
                vlan['ipv4'],
                vlan['creation_date'],
                vlan['macaddr'],
            ]

        ctx.print_table(
            ['IPv4 address', 'Created at', 'MAC address'],
            settings['vlans'], fmt_vlan)


def show_template_info(ctx, id):
    ti = ctx.api.OCI_TemplateInfo(id)

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
    ctx.p.print_table(tab)