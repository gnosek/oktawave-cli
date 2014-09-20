import inspect
import sys
import click
# noinspection PyProtectedMember
from click.decorators import _param_memo
from oktawave.api import OktawaveApi, OCSConnection
from oktawave.exceptions import OktawaveLoginError
from oktawave.printer import Printer


class OktawaveCliContext(object):
    p = None
    api = None
    ocs = None
    config = None

    def init_output(self, output=sys.stdout):
        self.p = Printer(output)

    def init_api(self, api_username, api_password, debug=False):
        self.api = OktawaveApi(
            username=api_username, password=api_password,
            debug=debug)
        try:
            self.api.logon(only_common=False)
        except OktawaveLoginError:
            print "ERROR: Couldn't login to Oktawave."
            sys.exit(1)

    def init_ocs(self, ocs_username, ocs_password):
        self.ocs = OCSConnection(username=ocs_username, password=ocs_password)

    def print_table(self, head, results, mapper_func):
        items = map(mapper_func, results)
        if items:
            self.p.print_table([head] + items)
            return True
        return False


pass_context = click.make_pass_decorator(OktawaveCliContext, ensure=True)


class NamedItemParam(click.ParamType):
    name = 'generic name/id parameter'
    label = 'item'

    @classmethod
    def list_items(cls, api):
        raise NotImplementedError()

    def convert(self, value, param, ctx):
        try:
            return int(value)
        except ValueError:
            pass

        assert isinstance(ctx.obj, OktawaveCliContext)
        found_item_id = None
        for item_id, item_name in self.list_items(ctx.obj.api):
            if item_name == value:
                if found_item_id is not None:
                    self.fail('Duplicate {0} "{1}" found'.format(self.label, value))
                found_item_id = item_id

        if found_item_id is None:
            self.fail('{0} "{1}" not found'.format(self.label, value))

        return found_item_id


# noinspection PyShadowingBuiltins
class PositionalOption(click.Argument):

    def __init__(self, param_decls, required=None, help=None, **attrs):
        self.help = help
        click.Argument.__init__(self, param_decls, required, **attrs)

    def get_arg_help_record(self):
        type_metavar = self.type.get_metavar(None)
        help = self.help
        if help and type_metavar:
            msg = help + ' ' + type_metavar
        elif help:
            msg = help
        elif type_metavar:
            msg = type_metavar
        else:
            msg = '(no help available)'
        return self.make_metavar(), msg


def positional_option(*param_decls, **attrs):
    def decorator(f):
        if 'help' in attrs:
            attrs['help'] = inspect.cleandoc(attrs['help'])
        _param_memo(f, PositionalOption(param_decls, **attrs))
        return f
    return decorator


class OktawaveCliCommand(click.Command):

    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        self.format_options(ctx, formatter)
        self.format_positional_options(ctx, formatter)
        self.format_epilog(ctx, formatter)

    def format_positional_options(self, ctx, formatter):
        """Writes all the positional options into the formatter if they exist."""
        opts = []
        for param in self.get_params(ctx):
            try:
                rv = param.get_arg_help_record()
                if rv is not None:
                    opts.append(rv)
            except AttributeError:
                continue

        if opts:
            with formatter.section('Positional arguments'):
                formatter.write_dl(opts)


class OktawaveCliGroup(click.Group):
    def command(self, *args, **kwargs):
        group_name = self.name + '_'
        kwargs.setdefault('cls', OktawaveCliCommand)

        def decorator(f):
            if 'name' not in kwargs and f.__name__.startswith(group_name):
                kw = kwargs.copy()
                kw.setdefault('name', f.__name__[len(group_name):])
            else:
                kw = kwargs
            cmd = click.command(*args, **kw)(f)
            self.add_command(cmd)
            return cmd
        return decorator
    pass

