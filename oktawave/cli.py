from ConfigParser import RawConfigParser, NoSectionError
import os

import click

from oktawave.commands.account import Account
from oktawave.commands.container import Container
from oktawave.commands.context import OktawaveCliContext, pass_context
from oktawave.commands.oci import OCI
from oktawave.commands.ocs import OCS
from oktawave.commands.opn import OPN
from oktawave.commands.ordb import ORDB
from oktawave.commands.ovs import OVS

VERSION = '0.9.0'


@click.group()
@click.option('-c', '--config', help='Specify configuration file', type=click.Path(dir_okay=False),
              default=os.path.expanduser('~/.oktawave-cli/config'))
@click.option('-d', '--debug/--no-debug', help='Debug output')
@click.option('-u', '--username', help='Oktawave username', required=False)
@click.option('-p', '--password', help='Oktawave password', required=False)
@click.option('-ocsu', '--ocs-username', help='OCS username', required=False)
@click.option('-ocsp', '--ocs-password', help='OCS password', required=False)
@click.version_option(VERSION)
@pass_context
def cli(ctx, config=None, username=None, password=None, ocs_username=None, ocs_password=None, debug=False):
    cp = {}

    def get_config_value(section, key, override):
        if override:
            return override
        if 'cp' not in cp:
            cp['cp'] = RawConfigParser()
            cp['cp'].read(config)
        return cp['cp'].get(section, key)

    assert isinstance(ctx, OktawaveCliContext)
    api_username = get_config_value('Auth', 'username', username)
    api_password = get_config_value('Auth', 'password', password)
    if os.path.exists(config):
        try:
            ocs_username = get_config_value('OCS', 'username', ocs_username)
            ocs_password = get_config_value('OCS', 'password', ocs_password)
        except NoSectionError:
            pass
    ctx.init_output()
    ctx.init_api(api_username, api_password, debug)
    ctx.init_ocs(ocs_username, ocs_password)


cli.add_command(Account)
cli.add_command(OCI)
cli.add_command(OCS)
cli.add_command(OVS)
cli.add_command(ORDB)
cli.add_command(Container)
cli.add_command(OPN)

if __name__ == '__main__':
    cli()
