#!/usr/bin/perl
# subdomains.cgi
# Manage subdomain onboarding

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'subdomains_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'subdomains'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle onboard action
if ($in{'onboard'}) {
    my $subdomain = $in{'subdomain'};
    my $relay_host = $in{'relay_host'} || '[smtp.mailgun.org]:587';

    # Validate subdomain
    if (!$subdomain) {
        print &ui_alert_box("Subdomain name is required", 'danger');
    } elsif (!&validate_domain($subdomain)) {
        print &ui_alert_box(&text('subdomains_edomain', $subdomain), 'danger');
    } else {
        my $err = &onboard_subdomain($subdomain, 'mailgun', $relay_host);
        if ($err) {
            print &ui_alert_box($err, 'danger');
        } else {
            print &ui_alert_box("Subdomain $subdomain onboarded successfully", 'success');
        }
    }
}

# Handle remove action
if ($in{'remove'}) {
    my $subdomain = $in{'remove_subdomain'};
    if ($subdomain) {
        my $err = &remove_subdomain($subdomain);
        if ($err) {
            print &ui_alert_box($err, 'danger');
        } else {
            print &ui_alert_box("Subdomain $subdomain removed successfully", 'success');
        }
    }
}

print "<p>$text{'subdomains_desc'}</p>";

# Display onboarding form
print &ui_hr();
print "<h3>$text{'subdomains_onboard'}</h3>";
print "<p>$text{'subdomains_onboard_desc'}</p>";

print &ui_form_start("subdomains.cgi", "post");

print &ui_table_start($text{'subdomains_onboard'}, "width=100%", 2);

print &ui_table_row($text{'subdomains_onboard_name'},
    &ui_textbox("subdomain", "", 40) . "<br><small>e.g., mynewapp.brightspeed.com</small>");

print &ui_table_row($text{'subdomains_onboard_relay_type'},
    &ui_textbox("relay_host", "[smtp.mailgun.org]:587", 40) .
    "<br><small>Default: [smtp.mailgun.org]:587</small>");

print &ui_table_end();

print &ui_form_end([ ["onboard", $text{'subdomains_onboard_button'}] ]);

# List onboarded subdomains
print &ui_hr();
print "<h3>$text{'subdomains_list'}</h3>";

my @sender_relay = &read_hash_map($config{'sender_relay_map'});
my @subdomains = grep { $_->{'type'} eq 'mapping' && $_->{'key'} =~ /^@.*\.brightspeed/ } @sender_relay;

if (@subdomains) {
    print &ui_table_start($text{'subdomains_list'}, "width=100%", 3);
    print &ui_table_row(undef, [
        "<b>$text{'subdomains_subdomain'}</b>",
        "<b>$text{'subdomains_relay'}</b>",
        "<b>$text{'subdomains_action'}</b>"
    ], 3, ["align=left"]);

    foreach my $entry (@subdomains) {
        my $subdomain = $entry->{'key'};
        $subdomain =~ s/^@//;
        my $relay = $entry->{'value'};

        print &ui_table_row(undef, [
            $subdomain,
            $relay,
            &ui_form_start("subdomains.cgi", "post") .
            &ui_hidden("remove_subdomain", $subdomain) .
            &ui_submit($text{'subdomains_remove'}, "remove") .
            &ui_form_end()
        ], 3);
    }

    print &ui_table_end();
} else {
    print &ui_alert_box("No subdomains onboarded yet", 'info');
}

&ui_print_footer("", $text{'index_return'});
