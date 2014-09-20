import click
from oktawave.api import CloneType, DICT as OktawaveConstants
from oktawave.commands.context import NamedItemParam, pass_context, OktawaveCliGroup, positional_option
from oktawave.commands.oci import clone_type_param, template_id_param, oci_class_param, subregion_param
from oktawave.commands.util import show_template_category, show_oci_logs, show_oci_settings, show_template_info
from oktawave.exceptions import OktawaveORDBInvalidTemplateError


class ORDBParam(NamedItemParam):
    name = 'ORDB instance name/id'
    label = 'ORDB'

    @classmethod
    def list_items(cls, api):
        for item in api.ORDB_List():
            yield item['id'], item['name']


def ordb_id_param(*args, **kwargs):
    kwargs.setdefault('help', 'ORDB instance name or ID (as returned by ORDB List)')
    kwargs.setdefault('type', ORDBParam())
    return positional_option(*args, **kwargs)


def db_name_param(*args, **kwargs):
    kwargs.setdefault('help', 'logical database name')
    return positional_option(*args, **kwargs)


@click.group(cls=OktawaveCliGroup, name='ORDB')
def ORDB():
    """Manage database instances and logical databases"""
    pass


@ORDB.command()
@pass_context
def ORDB_List(ctx):
    """List database instances"""
    dbs = ctx.api.ORDB_List()

    def fmt(db):
        return [
            db['id'],
            db['name'],
            db['type'],
            db['size'],
            db['available_space']
        ]

    ctx.print_table(
        ['Virtual machine ID', 'Name', 'Type', 'Size', 'Available space'],
        dbs, fmt)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_TurnOn(ctx, id):
    """Turn a database instance on"""
    ctx.api.ORDB_TurnOn(id)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_TurnOff(ctx, id):
    """Turn a database instance off"""
    ctx.api.ORDB_TurnOff(id)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_Restart(ctx, id):
    """Restart a database instance"""
    ctx.api.ORDB_Restart(id)


@ORDB.command(epilog="If db_name is not specified, delete whole instance")
@ordb_id_param('id')
@db_name_param('db_name', required=False)
@pass_context
def ORDB_Delete(ctx, id, db_name):
    """Delete a logical database or database instance"""
    ctx.api.ORDB_Delete(id, db_name)


@ORDB.command()
@pass_context
def ORDB_Templates(ctx):
    """List database VM templates"""
    print "\nCategory: MySQL"
    show_template_category(ctx, OktawaveConstants['MYSQL_TEMPLATE_CATEGORY'], 'ORDB')
    print "Category: PostgreSQL"
    show_template_category(ctx, OktawaveConstants['POSTGRESQL_TEMPLATE_CATEGORY'], 'ORDB')


@ORDB.command(
    epilog="""
    Runtime: new root/administrator password will be generated, new host name
    set etc. (Unmodified tech-support account required on OCI)

    AbsoluteCopy: initialization process will be skipped only new IP address
    and domain name will be assigned.
    """
)
@ordb_id_param('id')
@positional_option('name', help='new ORDB instance name')
@clone_type_param('clone_type')
@pass_context
def ORDB_Clone(ctx, id, name, clone_type):
    """Clone an ORDB instance"""
    clone_type = getattr(CloneType, clone_type)
    ctx.api.OCI_Clone(id, name, clone_type)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_Logs(ctx, id):
    """Show ORDB virtual machine logs"""
    show_oci_logs(ctx, id)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_LogicalDatabases(ctx, id):
    """Shows logical databases"""
    dbs = ctx.api.ORDB_LogicalDatabases(id)

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

    ctx.print_table(
        ['Virtual machine ID', 'Name', 'Type', 'Encoding', 'Running', 'QPS', 'Size'],
        dbs, fmt)


@ORDB.command()
@ordb_id_param('id')
@pass_context
def ORDB_Settings(ctx, id):
    """Show ORDB settings"""
    show_oci_settings(ctx, id)


@ORDB.command(name='Create', short_help='Create a new ORDB')
@positional_option('name', help='new ORDB instance name')
@template_id_param('template', help='template ID (as returned by ORDB Templates)')
@oci_class_param('oci_class', required=False)
@subregion_param('subregion')
@pass_context
def ORDB_Create(ctx, name, template, oci_class, subregion):
    """Create a database VM"""
    try:
        ctx.api.ORDB_Create(name, template, oci_class=oci_class, subregion=subregion)
    except OktawaveORDBInvalidTemplateError:
        print "ERROR: Selected template is not a database template"
        return 1


@ORDB.command()
@ordb_id_param('id')
def ORDB_GlobalSettings(ctx, id):
    """Show global database engine settings"""
    settings = ctx.api.ORDB_GlobalSettings(id)

    def fmt(item):
        return [item['name'], item['value']]

    ctx.print_table(['Name', 'Value'], settings, fmt)


@ORDB.command()
@template_id_param('id')
@pass_context
def ORDB_TemplateInfo(ctx, id):
    """Show more detailed info about a particular template"""
    show_template_info(ctx, id)


@ORDB.command()
@ordb_id_param('id')
@db_name_param('name')
@positional_option('encoding', help='database character encoding',
                   type=click.Choice(['utf8', 'latin2']), default='utf8')
@pass_context
def ORDB_CreateLogicalDatabase(ctx, id, name, encoding):
    """Create a new logical database within an instance"""
    ctx.api.ORDB_CreateLogicalDatabase(id, name, encoding)
    print "OK"


@ORDB.command()
@ordb_id_param('id')
@db_name_param('name')
@pass_context
def ORDB_BackupLogicalDatabase(ctx, id, name):
    """Create a backup of logical database"""
    ctx.api.ORDB_BackupLogicalDatabase(id, name)
    print "OK"


@ORDB.command()
@ordb_id_param('id_from', help='source ORDB name or ID (as returned by ORDB List)')
@ordb_id_param('id_to', help='destination ORDB name or ID (as returned by ORDB List)')
@db_name_param('name')
@pass_context
def ORDB_MoveLogicalDatabase(ctx, id_from, id_to, name):
    """Move a backup of logical database between ORDB instances"""
    ctx.api.ORDB_MoveLogicalDatabase(id_from, id_to, name)
    print "OK"


@ORDB.command()
@pass_context
def ORDB_Backups(ctx):
    """List logical database backups"""
    backups = ctx.api.ORDB_Backups()

    def fmt(b):
        return [b['file_name'], b['type'], b['path']]

    ctx.print_table(
        ['File name', 'Database type', 'Full path'],
        backups, fmt)


@ORDB.command()
@ordb_id_param('id')
@positional_option('backup_file', help='backup file name (as returned by ORDB Backups)')
@db_name_param('name')
@pass_context
def ORDB_RestoreLogicalDatabase(ctx, id, name, backup_file):
    """Restore a backup of logical database"""
    ctx.api.ORDB_RestoreLogicalDatabase(id, name, backup_file)
    print "OK"

