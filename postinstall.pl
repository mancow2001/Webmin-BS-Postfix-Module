#!/usr/bin/perl
# postinstall.pl
# Called by Webmin after module installation.
# Creates a compatibility symlink for the module library if the install
# directory name does not match the expected module name, so that Webmin's
# internal require("<dirname>-lib.pl") succeeds.

use strict;
use warnings;
use File::Basename;
use Cwd 'abs_path';

my $module_dir = dirname(abs_path(__FILE__));
my $dirname = basename($module_dir);
my $expected_name = 'brightspeed-postfix';
my $lib_file = 'brightspeed-postfix-lib.pl';

if ($dirname ne $expected_name) {
    my $symlink_name = "$module_dir/${dirname}-lib.pl";
    if (!-e $symlink_name) {
        symlink($lib_file, $symlink_name) or
            warn "postinstall: Could not create symlink $symlink_name -> $lib_file: $!\n";
    }
}

1;
