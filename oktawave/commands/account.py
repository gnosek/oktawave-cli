import click
from oktawave.commands.context import pass_context


@click.group(name='Account')
def Account():
    """Show account information"""
    pass


@Account.command(name='Settings')
@pass_context
def Account_Settings(ctx):
    """Show basic account settings"""
    res = ctx.api.Account_Settings()
    tab = [
        ['Key', 'Value'],
        ['Time zone', res['time_zone']],
        ['Currency', res['currency']],
        ['Date format', res['date_format']],
        ['Availability zone', res['availability_zone']],
        ['24h clock', 'Yes' if res['24h_clock'] else 'No']
    ]
    ctx.p.print_str("Account settings:")
    ctx.p.print_table(tab)


@Account.command(name='RunningJobs')
@pass_context
def Account_RunningJobs(ctx):
    """Show active operations"""
    ops = ctx.api.Account_RunningJobs()

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

    if not ctx.print_table(
            ['Operation ID', 'Started at', 'Started by', 'Operation type', 'Object', 'Progress', 'Status'],
            ops, fmt):
        print "No running operations"


@Account.command(name='Users')
@pass_context
def Account_Users(ctx):
    """Show users"""
    users = ctx.api.Account_Users()

    def fmt(user):
        return [
            ctx.api.client_id,
            user['email'],
            user['name']
        ]

    ctx.print_table(
        ['Client ID', 'E-mail', 'Name'],
        users, fmt)
