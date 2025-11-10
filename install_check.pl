#!/usr/bin/perl
# install_check.pl
# Check if Postfix is installed and the module can be used

do 'brightspeed-postfix-lib.pl';

# Check if Postfix command exists
if (!has_command($config{'postfix_command'})) {
    return 0;
}

# Check if postconf command exists
if (!has_command($config{'postconf_command'})) {
    return 0;
}

# Check if postmap command exists
if (!has_command($config{'postmap_command'})) {
    return 0;
}

# Check if Postfix config directory exists
if (!-d $config{'postfix_config_dir'}) {
    return 0;
}

# Check if main.cf exists
if (!-f $config{'postfix_main_cf'}) {
    return 0;
}

# All checks passed
return 1;
