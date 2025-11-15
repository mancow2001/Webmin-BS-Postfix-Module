#!/usr/bin/perl
# view_config.cgi
# Read-only configuration file viewer

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'view_config_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'view_config'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

print "<p>$text{'view_config_desc'}</p>";

# Header Checks Section
print "<h3>$text{'view_config_header_checks'}</h3>";
print "<p>$text{'view_config_header_checks_desc'}</p>";

my @header_entries = &read_pcre_file($config{'header_checks_file'});
if (@header_entries) {
    print &ui_columns_start([
        $text{'view_config_pattern'},
        $text{'view_config_action'}
    ]);

    foreach my $entry (@header_entries) {
        if ($entry->{'type'} eq 'pcre') {
            print &ui_columns_row([
                "<code>" . &html_escape($entry->{'pattern'}) . "</code>",
                "<code>" . &html_escape($entry->{'action'}) . "</code>"
            ]);
        } elsif ($entry->{'type'} eq 'comment') {
            print &ui_columns_row([
                "<em># " . &html_escape($entry->{'comment'}) . "</em>",
                ""
            ], undef, ['colspan=2', '']);
        }
    }

    print &ui_columns_end();
} else {
    print &ui_alert_box($text{'view_config_no_entries'}, 'info');
}

# SASL Password Section
print "<br><h3>$text{'view_config_sasl_passwd'}</h3>";
print "<p>$text{'view_config_sasl_passwd_desc'}</p>";
print &ui_alert_box($text{'view_config_sasl_warning'}, 'warn');

my @sasl_entries = &read_hash_map($config{'sasl_passwd_file'});
my @sasl_mappings = grep { $_->{'type'} eq 'mapping' } @sasl_entries;

if (@sasl_mappings) {
    print &ui_columns_start([
        $text{'view_config_relay_host'},
        $text{'view_config_username'}
    ]);

    foreach my $entry (@sasl_mappings) {
        my ($username, $password) = split(/:/, $entry->{'value'}, 2);
        print &ui_columns_row([
            "<code>" . &html_escape($entry->{'key'}) . "</code>",
            "<code>" . &html_escape($username) . "</code>"
        ]);
    }

    print &ui_columns_end();
} else {
    print &ui_alert_box($text{'view_config_no_entries'}, 'info');
}

# Sender Relay Map Section
print "<br><h3>$text{'view_config_sender_relay'}</h3>";
print "<p>$text{'view_config_sender_relay_desc'}</p>";

my @relay_entries = &read_hash_map($config{'sender_relay_map'});
my @relay_mappings = grep { $_->{'type'} eq 'mapping' } @relay_entries;

if (@relay_mappings) {
    print &ui_columns_start([
        $text{'view_config_sender'},
        $text{'view_config_nexthop'}
    ]);

    foreach my $entry (@relay_mappings) {
        print &ui_columns_row([
            "<code>" . &html_escape($entry->{'key'}) . "</code>",
            "<code>" . &html_escape($entry->{'value'}) . "</code>"
        ]);
    }

    print &ui_columns_end();
} else {
    print &ui_alert_box($text{'view_config_no_entries'}, 'info');
}

# Transport Rules Section
print "<br><h3>$text{'view_config_transport'}</h3>";
print "<p>$text{'view_config_transport_desc'}</p>";

# Hash transport map
print "<h4>$text{'view_config_transport_hash'}</h4>";
my @transport_entries = &read_hash_map($config{'transport_file'});
my @transport_mappings = grep { $_->{'type'} eq 'mapping' } @transport_entries;

if (@transport_mappings) {
    print &ui_columns_start([
        $text{'view_config_domain'},
        $text{'view_config_transport_rule'}
    ]);

    foreach my $entry (@transport_mappings) {
        print &ui_columns_row([
            "<code>" . &html_escape($entry->{'key'}) . "</code>",
            "<code>" . &html_escape($entry->{'value'}) . "</code>"
        ]);
    }

    print &ui_columns_end();
} else {
    print &ui_alert_box($text{'view_config_no_entries'}, 'info');
}

# Regexp transport map
print "<br><h4>$text{'view_config_transport_regexp'}</h4>";
my @domain_transport_entries = &read_pcre_file($config{'domain_transport_file'});
my @domain_transport_mappings = grep { $_->{'type'} eq 'pcre' } @domain_transport_entries;

if (@domain_transport_mappings) {
    print &ui_columns_start([
        $text{'view_config_pattern'},
        $text{'view_config_transport_rule'}
    ]);

    foreach my $entry (@domain_transport_mappings) {
        print &ui_columns_row([
            "<code>" . &html_escape($entry->{'pattern'}) . "</code>",
            "<code>" . &html_escape($entry->{'action'}) . "</code>"
        ]);
    }

    print &ui_columns_end();
} else {
    print &ui_alert_box($text{'view_config_no_entries'}, 'info');
}

&ui_print_footer("index.cgi", $text{'index_return'});
