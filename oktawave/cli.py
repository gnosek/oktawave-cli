from oktawave.api import OktawaveApi, OktawaveLoginError
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

