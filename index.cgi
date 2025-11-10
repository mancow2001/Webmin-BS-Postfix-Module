#!/usr/bin/perl
# index.cgi
# Display main dashboard for Brightspeed Postfix Relay module

require './brightspeed-postfix-lib.pl';

# Check if Postfix is installed
if (!&has_command($config{'postfix_command'})) {
    &ui_print_header(undef, $text{'index_title'}, "", undef, 1, 1);
    print &ui_alert_box($text{'index_epostfix'}, 'warn');
    &ui_print_footer("/", $text{'index'});
    exit;
}

# Check if config directory exists
if (!-d $config{'postfix_config_dir'}) {
    &ui_print_header(undef, $text{'index_title'}, "", undef, 1, 1);
    print &ui_alert_box(&text('index_edir', $config{'postfix_config_dir'}), 'warn');
    &ui_print_footer("/", $text{'index'});
    exit;
}

&ui_print_header(undef, $text{'index_title'}, "", undef, 1, 1);

# Get Postfix version
my $version = &get_postfix_version();
if ($version) {
    print &ui_alert_box(&text('index_version', $version), 'info');
}

# Service Status Section
print &ui_table_start($text{'index_status'}, "width=100%", 2);

my $status = &get_postfix_status();
my $status_msg = $status ?
    &ui_text_color($text{'index_running'}, 'success') :
    &ui_text_color($text{'index_stopped'}, 'danger');

print &ui_table_row($text{'index_status'}, $status_msg);

print &ui_table_end();

# Statistics Section
print "<br>";
print &ui_table_start($text{'index_stats'}, "width=100%", 2);

# Count root CIDRs
my @root_cidrs = &read_cidr_file($config{'cidr_root_file'});
my $root_count = scalar(grep { $_->{'type'} eq 'cidr' } @root_cidrs);
print &ui_table_row($text{'index_cidr_root'}, $root_count);

# Count subdomain CIDRs
my @subdomain_cidrs = &read_cidr_file($config{'cidr_subdomain_file'});
my $subdomain_count = scalar(grep { $_->{'type'} eq 'cidr' } @subdomain_cidrs);
print &ui_table_row($text{'index_cidr_subdomain'}, $subdomain_count);

# Count onboarded subdomains
my @sender_relay = &read_hash_map($config{'sender_relay_map'});
my $subdomain_total = scalar(grep { $_->{'type'} eq 'mapping' && $_->{'key'} =~ /^@.*\.brightspeed/ } @sender_relay);
print &ui_table_row($text{'index_subdomains'}, $subdomain_total);

# Get queue size
my @queue = &get_mail_queue();
my $queue_size = scalar(@queue);
print &ui_table_row($text{'index_queue_size'}, $queue_size);

print &ui_table_end();

# Quick Actions Section
print "<br>";
print &ui_table_start($text{'index_actions'}, "width=100%", 2);

# Service control buttons
my @control_buttons;
if ($status) {
    push(@control_buttons,
        &ui_link("control.cgi?action=stop", $text{'index_stop'}),
        &ui_link("control.cgi?action=reload", $text{'index_reload'})
    );
} else {
    push(@control_buttons,
        &ui_link("control.cgi?action=start", $text{'index_start'})
    );
}
push(@control_buttons, &ui_link("control.cgi?action=check", $text{'index_check'}));

print &ui_table_row($text{'control_title'}, join(" | ", @control_buttons));

# Navigation links
my @nav_links = (
    &ui_link("cidrs.cgi", "CIDR Whitelists"),
    &ui_link("subdomains.cgi", "Subdomain Onboarding"),
    &ui_link("sender_relay.cgi", "Sender Relay Maps"),
    &ui_link("domain_transport.cgi", "Transport Rules"),
    &ui_link("virtual.cgi", "Virtual Aliases"),
    &ui_link("headers.cgi", "Header Checks"),
    &ui_link("sasl.cgi", "SASL Authentication"),
    &ui_link("queue.cgi", $text{'index_view_queue'}),
    &ui_link("logs.cgi", $text{'index_view_logs'})
);

print &ui_table_row("Management", join(" | ", @nav_links));

print &ui_table_end();

# Display info about the module
print "<br>";
print &ui_alert_box(
    "This module manages the Brightspeed Postfix mail relay gateway. " .
    "Use the links above to configure CIDR whitelists, onboard subdomains, " .
    "manage sender-dependent routing, and control the Postfix service.",
    'info'
);

&ui_print_footer("/", $text{'index'});
