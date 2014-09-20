import click
from oktawave.api import PowerStatus
from oktawave.commands.context import pass_context, NamedItemParam, OktawaveCliGroup, positional_option
from oktawave.commands.oci import subregion_param, oci_id_param
from oktawave.exceptions import OktawaveOVSDeleteError, OktawaveOVSMappedError, OktawaveOVSMapError, \
    OktawaveOVSUnmappedError, OktawaveOVSUnmapError, OktawaveOVSTooSmallError


class OVSParam(NamedItemParam):
    name = 'OVS name/id'
    label = 'OVS'

    @classmethod
    def list_items(cls, api):
        for item in api.OVS_List():
            yield item['id'], item['name']


def ovs_name_param(*args, **kwargs):
    kwargs.setdefault('help', 'OVS volume name')
    return positional_option(*args, **kwargs)


def ovs_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'OVS name or id (as returned by OVS List)')
    kwargs.setdefault('type', OVSParam())
    return positional_option(*args, **kwargs)


def capacity_param(*args, **kwargs):
    kwargs.setdefault('help', 'OVS volume size in GB')
    kwargs.setdefault('type', click.INT)
    return positional_option(*args, **kwargs)


def tier_param(*args, **kwargs):
    kwargs.setdefault('help', 'OVS volume tier (1...5, default 1)')
    kwargs.setdefault('type', click.IntRange(min=1, max=5))
    kwargs.setdefault('default', 1)
    return positional_option(*args, **kwargs)


def disk_shared_param(*args, **kwargs):
    kwargs.setdefault('help', 'allow sharing volume between instances')
    kwargs.setdefault('type', click.Choice(['shared', 'unshared']))
    return positional_option(*args, **kwargs)


@click.group(cls=OktawaveCliGroup, name='OVS')
def OVS():
    """Manage OVS volumes"""
    pass


@OVS.command()
@pass_context
def OVS_List(ctx):
    """Lists disks"""
    disks = ctx.api.OVS_List()

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

    ctx.print_table(
        ['ID', 'Name', 'Tier', 'Capacity', 'Used', 'Shared', 'VMs'],
        disks, fmt)


@OVS.command()
@ovs_name_param('name')
@capacity_param('capacity')
@tier_param('tier')
@disk_shared_param('disktype')
@subregion_param('subregion')
@pass_context
def OVS_Create(ctx, name, capacity, tier, disktype, subregion):
    """Add a disk"""
    ctx.api.OVS_Create(name, capacity, tier, (disktype == 'shared'), subregion)
    print "OK"


@OVS.command()
@ovs_id_param('ovs_id')
@pass_context
def OVS_Delete(ctx, ovs_id):
    """Delete a disk"""
    try:
        ctx.api.OVS_Delete(ovs_id)
    except OktawaveOVSDeleteError:
        print "ERROR: Disk cannot be deleted (is it mapped to any OCI instances?)."
    else:
        print "OK"


@OVS.command()
@ovs_id_param('ovs_id')
@oci_id_param('oci_id')
@pass_context
def OVS_Map(ctx, ovs_id, oci_id):
    """Connect a disk to an instance"""
    try:
        ctx.api.OVS_Map(ovs_id, oci_id)
    except OktawaveOVSMappedError:
        print "ERROR: Disk is already mapped to this instance"
        return 1
    except OktawaveOVSMapError:
        print "ERROR: Disk cannot be mapped."
    else:
        print "OK"


@OVS.command()
@ovs_id_param('ovs_id')
@oci_id_param('oci_id')
@pass_context
def OVS_Unmap(ctx, ovs_id, oci_id):
    """Disconnect a disk from an instance"""
    try:
        ctx.api.OVS_Unmap(ovs_id, oci_id)
    except OktawaveOVSUnmappedError:
        print "ERROR: Disk is not mapped to this instance"
        return 1
    except OktawaveOVSUnmapError:
        print "ERROR: Disk cannot be unmapped."
    else:
        print "OK"


@OVS.command()
@ovs_id_param('ovs_id')
@tier_param('tier')
@pass_context
def OVS_ChangeTier(ctx, ovs_id, tier):
    """Change OVS tier"""
    ctx.api.OVS_ChangeTier(ovs_id, tier)
    print "OK"


@OVS.command()
@ovs_id_param('ovs_id')
@capacity_param('size', help='new size in GB (must be larger than current size)')
@pass_context
def OVS_Extend(ctx, ovs_id, size):
    """Resize OVS volume"""
    try:
        ctx.api.OVS_Extend(ovs_id, size)
    except OktawaveOVSMappedError:
        print "ERROR: Disk is mapped to an instance"
        return 1
    except OktawaveOVSTooSmallError:
        print "ERROR: Requested size smaller than current size"
        return 1
    else:
        print "OK"

