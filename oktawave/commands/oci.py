import os

import click

from oktawave.api import TemplateType, CloneType
from oktawave.commands.context import pass_context, NamedItemParam, positional_option, OktawaveCliGroup
from oktawave.commands.util import show_template_category, show_oci_logs, show_oci_settings, show_template_info
from oktawave.exceptions import OktawaveOCIClassNotFound


class OCIParam(NamedItemParam):
    name = 'OCI name/id'
    label = 'OCI'

    @classmethod
    def list_items(cls, api):
        for item in api.OCI_List():
            yield item['id'], item['name']


class SubregionParam(NamedItemParam):
    name = 'Subregion name/ID'
    label = 'Subregion'

    @classmethod
    def list_items(cls, api):
        for item in api.OCI_Subregions():
            yield item['id'], item['name']

    def convert(self, value, param, ctx):
        if value == 'Auto':
            return value

        return super(SubregionParam, self).convert(value, param, ctx)


def template_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'template ID (as returned by OCI Templates)')
    kwargs.setdefault('type', click.INT)
    return positional_option(*args, **kwargs)


def oci_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'OCI name or ID (as returned by OCI List)')
    kwargs.setdefault('type', OCIParam())
    return positional_option(*args, **kwargs)


def oci_class_param(*args, **kwargs):
    kwargs.setdefault('help', 'OCI class (as returned by OCI Classes), e.g. v1.standard-1.09')
    return positional_option(*args, **kwargs)


def subregion_param(*args, **kwargs):
    kwargs.setdefault('help', 'subregion ID (as returned by OCI Subregions) or Auto')
    kwargs.setdefault('type', SubregionParam())
    kwargs.setdefault('default', 'Auto')
    kwargs.setdefault('show_default', True)
    return click.option(*args, **kwargs)


def clone_type_param(*args, **kwargs):
    kwargs.setdefault('help', 'clone type')
    kwargs.setdefault('type', click.Choice(['Runtime', 'AbsoluteCopy']))
    return positional_option(*args, **kwargs)


def remote_user_option(*args, **kwargs):
    kwargs.setdefault('help', 'remote user name')
    kwargs.setdefault('metavar', 'LOGIN')
    kwargs.setdefault('default', 'root')
    kwargs.setdefault('show_default', True)
    return click.option(*args, **kwargs)


def oci_ip(ctx, oci_id):
    settings = ctx.api.OCI_Settings(oci_id)
    return settings['ips'][0]['ipv4']


@click.command(cls=OktawaveCliGroup, name='OCI')
def OCI():
    """Manage OCI instances"""
    pass


@OCI.command()
@pass_context
def OCI_TemplateCategories(ctx):
    """List available template categories"""
    cats = ctx.api.OCI_TemplateCategories()

    def fmt(cat):
        tc_id = cat.id
        if cat.parent_id is not None:
            tc_id = '  ' + str(tc_id)
        return [tc_id, cat.name, cat.description]

    ctx.print_table(
        ['Template category ID', 'Name', 'Description'],
        cats, fmt)


@OCI.command()
@positional_option('category_id', type=click.INT, help='template category (as returned by OCI TemplateCategories)')
@pass_context
def OCI_Templates(ctx, category_id):
    """List templates in a category"""
    show_template_category(ctx, category_id)


@OCI.command()
@template_id_param('template_id')
@pass_context
def OCI_TemplateInfo(ctx, template_id):
    """Show more detailed info about a particular template"""
    show_template_info(ctx, template_id)


@OCI.command()
@pass_context
def OCI_List(ctx):
    """List virtual machines"""
    vms = ctx.api.OCI_List()

    def fmt(vm):
        return [vm['id'], vm['name'], vm['status']]

    ctx.print_table(
        ['Virtual machine ID', 'Name', 'Status'], vms, fmt)


@OCI.command()
@pass_context
def OCI_ListDetails(ctx):
    """List virtual machines with more detail"""
    vms = ctx.api.OCI_ListDetails()

    def fmt(vm):
        return [vm['id'], vm['name'], vm['status'], vm['class_name'],
                '%d/%d MHz' % (vm['cpu_usage_mhz'], vm['cpu_mhz']),
                '%d/%d MB' % (vm['memory_usage_mb'], vm['memory_mb'])]

    ctx.print_table(
        ['Virtual machine ID', 'Name', 'Status', 'Class', 'CPU', 'Memory'], vms, fmt)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_Restart(ctx, oci_id):
    """Restart a VM"""
    ctx.api.OCI_Restart(oci_id)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_TurnOff(ctx, oci_id):
    """Turn off a VM"""
    ctx.api.OCI_TurnOff(oci_id)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_TurnOn(ctx, oci_id):
    """Turn on a VM"""
    ctx.api.OCI_TurnOn(oci_id)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_Delete(ctx, oci_id):
    """Delete a VM"""
    ctx.api.OCI_Delete(oci_id)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_Logs(ctx, oci_id):
    """Show virtual machine logs"""
    show_oci_logs(ctx, oci_id)


@OCI.command()
@oci_id_param('oci_id')
@pass_context
def OCI_Settings(ctx, oci_id):
    """Show basic VM settings (IP addresses, OS, names, autoscaling etc.)"""
    show_oci_settings(ctx, oci_id)


@OCI.command()
@pass_context
def OCI_Subregions(ctx):
    """List subregions"""

    def fmt(cluster):
        return [cluster['id'], cluster['name'], cluster['active']]

    clusters = ctx.api.OCI_Subregions()
    ctx.print_table(['ID', 'Name', 'Active'], clusters, fmt)


@OCI.command()
@positional_option('name', help='new OCI name')
@template_id_param('template')
@oci_class_param('oci_class', required=False,
                 help='OCI class, e.g. v1.standard-1.09, defaults to minimal class of template')
@subregion_param('--subregion')
@click.option('--disk-size', required=False, type=click.INT, metavar='SIZE',
              help='Disk size in GB (optional, defaults to template minimum)')
@pass_context
def OCI_Create(ctx, name, template, oci_class=None, subregion='Auto', forced_type='Machine', db_type=None, disk_size=None):
    """Creates a new instance from template"""
    forced_type = getattr(TemplateType, forced_type)
    try:
        ctx.api.OCI_Create(name, template, oci_class, forced_type, db_type, subregion, disk_size, ip_address_id=None)
    except OktawaveOCIClassNotFound:
        print "OCI class not found"


@OCI.command()
@pass_context
def OCI_Classes(ctx):
    """List OCI classes"""

    def fmt(oci_class):
        return [oci_class['category'], oci_class['name'], oci_class['cpu_count'], oci_class['memory_mb']]

    def sort_key(oci_class):
        return str(oci_class['category']), oci_class['cpu_count'], oci_class['memory_mb']

    classes = ctx.api.OCI_Classes()
    ctx.print_table(['Category', 'Name', 'CPU count', 'Memory (MB)'], sorted(classes, key=sort_key), fmt)


@OCI.command()
@oci_id_param('oci_id')
@oci_class_param('oci_class')
@click.option('--restart', help='when to restart OCI if needed',
              type=click.Choice(['never', 'now', 'midnight']),
              default='never', show_default=True)
@pass_context
def OCI_ChangeClass(ctx, oci_id, oci_class, restart):
    """Change running instance class"""
    needs_restart = ctx.api.OCI_ClassChangeNeedsRestart(oci_id, oci_class)
    if needs_restart and restart == 'never':
        ctx.p.print_str('Restart needed for OCI class change, use --restart=[now|midnight]')
        return
    ctx.api.OCI_ChangeClass(oci_id, oci_class, at_midnight=(restart == 'midnight'))


@OCI.command(
    epilog="""
    Runtime: new root/administrator password will be generated, new host name
    set etc. (Unmodified tech-support account required on OCI)

    AbsoluteCopy: initialization process will be skipped only new IP address
    and domain name will be assigned.
    """
)
@oci_id_param('oci_id')
@positional_option('name', help='new OCI name')
@positional_option('clone_type', type=click.Choice(['Runtime', 'AbsoluteCopy']))
@pass_context
def OCI_Clone(ctx, oci_id, name, clone_type):
    """Clone a VM"""
    clone_type = getattr(CloneType, clone_type)
    ctx.api.OCI_Clone(oci_id, name, clone_type)


@OCI.command()
@oci_id_param('oci_id')
@click.argument('ping_args', nargs=-1, required=False)
@pass_context
def OCI_ping(ctx, oci_id, ping_args):
    """Ping VM"""
    ip = oci_ip(ctx, oci_id)
    os.execvp('ping', ('ping', ip) + ping_args)


@OCI.command()
@oci_id_param('oci_id')
@remote_user_option('--user')
@click.argument('ssh_args', nargs=-1, required=False)
@pass_context
def OCI_ssh(ctx, oci_id, user, ssh_args):
    """Connect to VM using ssh"""
    ip = oci_ip(ctx, oci_id)
    print 'Default OCI password: %s' % ctx.api.OCI_DefaultPassword(oci_id)
    remote = '%s@%s' % (user, ip)
    os.execvp('ssh', ('ssh', remote) + ssh_args)


@OCI.command(name='ssh_copy_id', short_help='Copy ssh public key to VM')
@oci_id_param('oci_id')
@remote_user_option('--user')
@click.argument('ssh_args', nargs=-1, required=False)
@pass_context
def OCI_ssh_copy_id(ctx, oci_id, user, ssh_args):
    """Copy ssh public key to VM"""
    ip = oci_ip(ctx, oci_id)
    print 'Default OCI password: %s' % ctx.api.OCI_DefaultPassword(oci_id)
    remote = '%s@%s' % (user, ip)
    os.execvp('ssh-copy-id', ('ssh-copy-id', remote) + ssh_args)

