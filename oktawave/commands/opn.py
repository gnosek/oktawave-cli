import click
from oktawave.commands.context import NamedItemParam, positional_option, OktawaveCliGroup, pass_context
from oktawave.commands.oci import oci_id_param


class OPNParam(NamedItemParam):
    name = 'OPN name/id'
    label = 'OPN'

    @classmethod
    def list_items(cls, api):
        for item in api.OPN_List():
            yield item['id'], item['name']


def opn_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'OPN name or ID (as returned by OPN List)')
    kwargs.setdefault('type', OPNParam())
    return positional_option(*args, **kwargs)


def address_pool_param(*args, **kwargs):
    kwargs.setdefault('help', 'address class (default: 10.0.0.0/24)')
    kwargs.setdefault('type', click.Choice(['10.0.0.0/24', '192.168.0.0/24']))
    kwargs.setdefault('default', '10.0.0.0/24')
    return positional_option(*args, **kwargs)


@click.command(cls=OktawaveCliGroup, name='OPN')
def OPN():
    """Manage private networks"""
    pass


@OPN.command()
@pass_context
def OPN_List(ctx):
    """List private networks"""
    vlans = ctx.api.OPN_List()

    def fmt(c):
        return [c['id'], c['name'], c['address_pool'], c['payment_type']]

    ctx.print_table(
        ['OPN ID', 'Name', 'Address pool', 'Payment type'], vlans, fmt)


@OPN.command()
@opn_id_param('opn_id')
@pass_context
def OPN_Get(ctx, opn_id):
    """Display OPN info"""
    c = ctx.api.OPN_Get(opn_id)

    base_tab = [['Key', 'Value']]
    base_tab.extend([
        ['ID', c['id']],
        ['Name', c['name']],
        ['Address pool', c['address_pool']],
        ['Payment type', c['payment_type']]
    ])
    ctx.p.print_str('\nBasic OPN settings')
    ctx.p.print_table(base_tab)
    vm_tab = [['OCI ID', 'Name', 'MAC address', 'Private IP address']]
    vm_tab.extend([[
        vm['VirtualMachine']['VirtualMachineId'],
        vm['VirtualMachine']['VirtualMachineName'],
        vm['MacAddress'],
        vm['PrivateIpAddress']
    ] for vm in c['vms']])
    ctx.p.print_str('Virtual machines')
    ctx.p.print_table(vm_tab)


@OPN.command()
@positional_option('name', help='OPN name')
@address_pool_param('address_pool')
@pass_context
def OPN_Create(ctx, name, address_pool):
    """Create a new OPN"""
    ctx.api.OPN_Create(name, address_pool)
    print "OK"


@OPN.command()
@opn_id_param('opn_id')
@oci_id_param('oci_id')
@positional_option('ip_address', help='OCI IP address')
@pass_context
def OPN_AddOCI(ctx, opn_id, oci_id, ip_address):
    """Add an OCI to an OPN"""
    ctx.api.OPN_AddOCI(opn_id, oci_id, ip_address)
    print "OK"


@OPN.command()
@opn_id_param('opn_id')
@oci_id_param('oci_id')
@pass_context
def OPN_RemoveOCI(ctx, opn_id, oci_id):
    """Remove an OCI from an OPN"""
    ctx.api.OPN_RemoveOCI(opn_id, oci_id)
    print "OK"


@OPN.command()
@opn_id_param('opn_id')
@pass_context
def OPN_Delete(ctx, opn_id):
    """Delete a private network"""
    ctx.api.OPN_Delete(opn_id)
    print "OK"


@OPN.command()
@opn_id_param('opn_id')
@positional_option('name', help='OPN name')
@pass_context
def OPN_Rename(ctx, opn_id, name):
    """Change OPN name"""
    ctx.api.OPN_Rename(opn_id, name)
    print "OK"
