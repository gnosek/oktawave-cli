import click

from oktawave.commands.context import NamedItemParam, OktawaveCliGroup, pass_context, positional_option
from oktawave.commands.oci import oci_id_param, OCIParam


class ContainerParam(NamedItemParam):
    name = 'container name/id'
    label = 'container'

    @classmethod
    def list_items(cls, api):
        for item in api.Container_List():
            yield item['id'], item['name']


def container_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'container name or ID (as returned by Container List)')
    kwargs.setdefault('type', ContainerParam())
    return positional_option(*args, **kwargs)


def container_options(f):
    options = [
        click.option('--load-balancer/--no-load-balancer', help='enable load-balancer'),
        click.option('--service', help='load balancer service',
                     type=click.Choice(['HTTP', 'HTTPS', 'SMTP', 'MySQL', 'Port']),
                     default='Port', show_default=True),
        click.option('--port', help='load balancer port (ignored unless --service=Port)',
                     type=click.INT),
        click.option('--proxy-cache/--no-proxy-cache', help='enable proxy cache'),
        click.option('--use-ssl/--no-ssl', help='enable SSL'),
        click.option('--healthcheck/--no-healthcheck', help='enable healthcheck'),
        click.option('--mysql-master-id', type=OCIParam(), help='MySQL master OCI ID (will be added to container)'),
        click.option('--session-persistence', help='session persistence type',
                     type=click.Choice(['none', 'source_ip', 'by_cookie']),
                     default='none', show_default=True),
        click.option('--load-balancer-algorithm', help='load balancer algorithm',
                     type=click.Choice(['least_response_time', 'least_connections', 'source_ip_hash', 'round_robin']),
                     default='least_response_time', show_default=True),
        click.option('--ip-version', help='IP version',
                     type=click.Choice(['4', '6', 'both']),
                     default='4', show_default=True),
        click.option('--autoscaling/--no-autoscaling', help='autoscaling'),
    ]
    for option in options:
        f = option(f)
    return f


@click.command(cls=OktawaveCliGroup, name='Container')
def Container():
    """Manage instance containers"""
    pass


@Container.command()
@pass_context
def Container_List(ctx):
    """List containers"""
    containers = ctx.api.Container_List()

    def fmt(c):
        return [c['id'], c['name'], c['vms']]

    ctx.print_table(
        ['Container ID', 'Name', 'VMs'], containers, fmt)


@Container.command()
@container_id_param('container_id')
@pass_context
def Container_Get(ctx, container_id):
    """Display container information"""
    c = ctx.api.Container_Get(container_id)

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
    ctx.p.print_str('\nBasic container settings')
    ctx.p.print_table(base_tab)

    oci_list = ctx.api.Container_OCIList(container_id)

    def fmt_oci(oci):
        return [oci['oci_id'], oci['oci_name'], oci['status']]

    ctx.p.print_str('\nAttached OCIs')
    ctx.print_table(
        ['ID', 'Name', 'Status'], oci_list, fmt_oci)


@Container.command()
@container_id_param('container_id')
@oci_id_param('oci_id')
@pass_context
def Container_RemoveOCI(ctx, container_id, oci_id):
    """Remove an OCI from a container"""
    ctx.api.Container_RemoveOCI(container_id, oci_id)
    print "OK"


@Container.command()
@container_id_param('container_id')
@oci_id_param('oci_id')
@pass_context
def Container_AddOCI(ctx, container_id, oci_id):
    """Add an OCI to a container"""
    ctx.api.Container_AddOCI(container_id, oci_id)
    print "OK"


@Container.command()
@container_id_param('container_id')
@pass_context
def Container_Delete(ctx, container_id):
    """Delete a container"""
    ctx.api.Container_Delete(container_id)
    print "OK"


@Container.command()
@positional_option('name', help='container name')
@container_options
@pass_context
def Container_Create(ctx, name, load_balancer, service, port, proxy_cache, use_ssl,
                     healthcheck, mysql_master_id, session_persistence,
                     load_balancer_algorithm, ip_version, autoscaling):
    """Create a new container"""
    if autoscaling:
        autoscaling = 'on'
    else:
        autoscaling = 'off'
    container_id = ctx.api.Container_Create(
        name, load_balancer, service, port, proxy_cache,
        use_ssl, healthcheck, mysql_master_id, session_persistence,
        load_balancer_algorithm, ip_version, autoscaling
    )
    print "OK, new container ID: " + str(container_id) + "."


@Container.command()
@container_id_param('container_id')
@positional_option('name', help='container name')
@container_options
@pass_context
def Container_Edit(ctx, container_id, name, load_balancer, service, port, proxy_cache, use_ssl,
                   healthcheck, mysql_master_id, session_persistence,
                   load_balancer_algorithm, ip_version, autoscaling):
    """Modify a container"""
    if autoscaling:
        autoscaling = 'on'
    else:
        autoscaling = 'off'
    ctx.api.Container_Edit(
        container_id, name, load_balancer, service, port, proxy_cache,
        use_ssl, healthcheck, mysql_master_id, session_persistence,
        load_balancer_algorithm, ip_version, autoscaling
    )
    print "OK"

