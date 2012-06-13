#!/usr/bin/perl
use warnings;
use strict;
use Data::Dumper;

# Builds debs and rpms from the source
# Built packages are put in build/.
# Currently builds packages for:
# - debian squeeze (6)
# - debian/ubuntu with python 2.7 & python-swift
# - generic source *.tar.gz with setup.py installation script
# - centos 6
# - opensuse 12
#
# You need to have alien and python-setuptools installed to run correctly.
# This script requires root privileges and both python 2.7 and 2.6.

if($>) {
	print "You need to be root to run this script, sorry.\n";
	exit 1;
}
for my $app ('alien', 'rm', 'python', 'dpkg', 'cp', 'cat') {
	unless (`which $app`) {
		print "You need to have $app installed, sorry.\n";
		exit 1;
	}
}

my $VERSION = [`cat setup.py` =~ /version='(.*)'/]->[0];
print $VERSION;

system 'rm -rfv dist';
system 'rm -rfv build';
system 'python setup.py bdist_rpm';
system 'python setup.py sdist';

chdir 'dist';

system "alien oktawave-cli-$VERSION-1.noarch.rpm";
system "dpkg -x oktawave-cli_$VERSION-2_all.deb deb";
system "dpkg -e oktawave-cli_$VERSION-2_all.deb deb/DEBIAN";

sub load_control {
	my $res = [];
	open CONTROL, shift;
	local $/ = "\n";
	while (<CONTROL>) {
		print $_;
		if (/^ /) {
			chomp $_;
			$res->[$#$res]->[1] .= "\n$_";
		}
		elsif (/^([^:]*): (.*)$/) {
			push @$res, [$1, $2];
		}
	}
	close CONTROL;
	$res
}

sub write_control {
	my ($c, $file) = @_;
	open CONTROL, ">$file" or die $!;
	print CONTROL join "", map {"$_->[0]: $_->[1]\n"} @$c;
	close CONTROL;
}

sub delete_control {
	my $c = shift;
	my $m = {map {$_ => 1} @_};
	[grep {not $m->{$_->[0]}} @$c];
}

sub mod_control {
	my ($c, $m) = @_;
	[map {exists $m->{$_->[0]} ? [$_->[0], $m->{$_->[0]}] : $_} @$c];
}

sub add_control {
	my ($c, $k, $v, $n) = @_;
	[@$c[0..($n-1)], [$k, $v], @$c[$n..$#$c]];
}

my $c = load_control('deb/DEBIAN/control');
$c = add_control($c, 'Depends', 'python-suds (>= 0.3.9), python-argparse (>= 1.1), python-prettytable (>= 0.5), python-setproctitle (>= 1.0.1), python-setuptools (>= 0.6.14)', 4);
$c = mod_control($c, {
	'Maintainer' => 'Oktawave Development Team (by Marek Siemdaj) <support@oktawave.com, marek.siemdaj@gmail.com>',
	'Description' => q|Command line interface to Oktawave
 Oktawave CLI
 .
 Command line interface to the Oktawave cloud (see oktawave.com).|
});
write_control($c, 'deb/DEBIAN/control');

system 'cp -Rv deb deb_python2.7';
$c = load_control('deb_python2.7/DEBIAN/control');
$c = mod_control($c, {'Depends' => 'python-suds (>= 0.3.9), python-prettytable (>= 0.5), python-setproctitle (>= 1.0.1), python-setuptools (>= 0.6.14), python-swift'});
write_control($c, 'deb_python2.7/DEBIAN/control');

my $md5 = `cat deb/DEBIAN/md5sums`;
$md5 =~ s/python2\.7/python2\.6/g;
open MD5, ">deb/DEBIAN/md5sums";
print MD5 $md5;
close MD5;

rename 'deb/usr/local/lib/python2.7', 'deb/usr/local/lib/python2.6';
system 'cp ../postinst deb/DEBIAN';

mkdir 'final';
system 'dpkg --build deb';
rename 'deb.deb', "final/oktawave-cli-$VERSION-debian_squeeze.deb";
print "Created final/oktawave-cli-$VERSION-debian_squeeze.deb\n";

system 'dpkg --build deb_python2.7';
rename 'deb_python2.7.deb', "final/oktawave-cli-$VERSION-ubuntu_oneiric.deb";
print "Created final/oktawave-cli-$VERSION-ubuntu_oneiric.deb\n";

rename "oktawave-cli-$VERSION.tar.gz", "final/oktawave-cli-$VERSION-src.tar.gz";
print "Created final/oktawave-cli-$VERSION-src.tar.gz\n";
print "Cleaning up...\n";
chdir "..";
# CentOS 6
system 'python setup.py bdist_rpm --pre-install postinst --requires gcc,wget,python-setuptools,python-devel,python-suds --python python2.6';
rename "dist/oktawave-cli-$VERSION-1.noarch.rpm", "dist/final/oktawave-cli-$VERSION-centos-6.rpm";
# openSUSE 12
system 'python setup.py bdist_rpm --pre-install postinst --requires wget,python-setuptools,python-setproctitle,python-xml,python-argparse';
rename "dist/oktawave-cli-$VERSION-1.noarch.rpm", "dist/final/oktawave-cli-$VERSION-opensuse-12.rpm";
system "rm -Rf build";
system 'mv dist/final build';
system "rm -Rf dist";
unlink "MANIFEST";

print "Done, packages generated:\n" . join '', map {"* build/$_\n"} split /\s+/, `ls build`;
