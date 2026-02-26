#!/usr/bin/perl
# onboard_domain.cgi
# Unified domain onboarding interface

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'onboard_domain_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'onboard_domain'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle confirm action (after preview)
if ($in{'confirm'}) {
    my $fqdn = $in{'fqdn'};
    my $relay_username = $in{'relay_username'};
    my $relay_password = $in{'relay_password'};
    my $relay_host = $in{'relay_host'};
    my $relay_port = $in{'relay_port'};

    # Call the onboard_domain_full function
    my $err = &onboard_domain_full($fqdn, $relay_username, $relay_password, $relay_host, $relay_port);

    if ($err) {
        print &ui_alert_box(&text('onboard_domain_error', $err), 'danger');
    } else {
        print &ui_alert_box(&text('onboard_domain_success', $fqdn), 'success');
    }

    print "<p><a href='onboard_domain.cgi'>$text{'onboard_domain_another'}</a></p>";
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle preview action
if ($in{'preview'}) {
    my $fqdn = $in{'fqdn'};
    my $relay_username = $in{'relay_username'};
    my $relay_password = $in{'relay_password'};
    my $relay_host = $in{'relay_host'};
    my $relay_port = $in{'relay_port'};

    # Validate all inputs
    my @errors;

    if (!$fqdn) {
        push(@errors, $text{'onboard_domain_efqdn_required'});
    } elsif (!&validate_domain($fqdn)) {
        push(@errors, &text('onboard_domain_efqdn_invalid', $fqdn));
    }

    if (!$relay_username) {
        push(@errors, $text{'onboard_domain_eusername_required'});
    }

    if (!$relay_password) {
        push(@errors, $text{'onboard_domain_epassword_required'});
    }

    if (!$relay_host) {
        push(@errors, $text{'onboard_domain_ehost_required'});
    } elsif (!&validate_domain($relay_host)) {
        push(@errors, &text('onboard_domain_ehost_invalid', $relay_host));
    }

    if (!$relay_port) {
        push(@errors, $text{'onboard_domain_eport_required'});
    } elsif ($relay_port !~ /^\d+$/) {
        push(@errors, &text('onboard_domain_eport_invalid', $relay_port));
    } elsif ($relay_port != 25 && $relay_port != 2525 && $relay_port != 587 && $relay_port != 465) {
        push(@errors, &text('onboard_domain_eport_not_allowed', $relay_port));
    }

    # Check for duplicates
    if (!@errors) {
        my @header_entries = &read_pcre_file($config{'header_checks_file'});
        foreach my $entry (@header_entries) {
            if ($entry->{'pattern'} =~ /\Q$fqdn\E/) {
                push(@errors, &text('onboard_domain_eduplicate', $fqdn, 'header_checks'));
                last;
            }
        }

        my @sasl_entries = &read_hash_map($config{'sasl_passwd_file'});
        foreach my $entry (@sasl_entries) {
            if ($entry->{'key'} eq '@' . $fqdn) {
                push(@errors, &text('onboard_domain_eduplicate', $fqdn, 'sasl_passwd'));
                last;
            }
        }

        my @relay_entries = &read_hash_map($config{'sender_relay_map'});
        foreach my $entry (@relay_entries) {
            if ($entry->{'key'} eq '@' . $fqdn) {
                push(@errors, &text('onboard_domain_eduplicate', $fqdn, 'sender_relay_map'));
                last;
            }
        }
    }

    # Show errors or preview
    if (@errors) {
        print &ui_alert_box(join("<br>", @errors), 'danger');
        # Show form again with filled values
        goto SHOW_FORM;
    } else {
        # Show preview
        print "<h3>$text{'onboard_domain_preview_title'}</h3>";
        print "<p>$text{'onboard_domain_preview_desc'}</p>";

        print &ui_table_start($text{'onboard_domain_preview_changes'}, "width=100%", 2);

        # header_checks change
        my $header_pattern = '/^From: .*@' . quotemeta($fqdn) . '/';
        print &ui_table_row($text{'onboard_domain_file_header_checks'},
            "<code>$header_pattern    IGNORE</code><br><em>$text{'onboard_domain_insert_before_last'}</em>");

        # sasl_passwd change
        print &ui_table_row($text{'onboard_domain_file_sasl_passwd'},
            "<code>\@$fqdn    $relay_username:********</code>");

        # sender_relay_map change
        print &ui_table_row($text{'onboard_domain_file_sender_relay'},
            "<code>\@$fqdn    $relay_nexthop</code>");

        print &ui_table_end();

        # Confirmation form
        print &ui_form_start("onboard_domain.cgi", "post");
        print &ui_hidden("fqdn", $fqdn);
        print &ui_hidden("relay_username", $relay_username);
        print &ui_hidden("relay_password", $relay_password);
        print &ui_hidden("relay_host", $relay_host);
        print &ui_hidden("relay_port", $relay_port);
        print &ui_form_end([
            ["confirm", $text{'onboard_domain_confirm'}],
            ["cancel", $text{'cancel'}]
        ]);

        &ui_print_footer("index.cgi", $text{'index_return'});
        exit;
    }
}

SHOW_FORM:

# Show the onboarding form
print "<p>$text{'onboard_domain_desc'}</p>";

print &ui_form_start("onboard_domain.cgi", "post");

print &ui_table_start($text{'onboard_domain_form_title'}, "width=100%", 2);

print &ui_table_row($text{'onboard_domain_fqdn'},
    &ui_textbox("fqdn", $in{'fqdn'} || "", 50) . "<br><small>$text{'onboard_domain_fqdn_hint'}</small>");

print &ui_table_row($text{'onboard_domain_relay_username'},
    &ui_textbox("relay_username", $in{'relay_username'} || "", 40));

print &ui_table_row($text{'onboard_domain_relay_password'},
    &ui_password("relay_password", $in{'relay_password'} || "", 40));

print &ui_table_row($text{'onboard_domain_relay_host'},
    &ui_textbox("relay_host", $in{'relay_host'} || "smtp.mailgun.org", 40) . "<br><small>$text{'onboard_domain_relay_host_hint'}</small>");

print &ui_table_row($text{'onboard_domain_relay_port'},
    &ui_textbox("relay_port", $in{'relay_port'} || "587", 10) . "<br><small>$text{'onboard_domain_relay_port_hint'}</small>");

print &ui_table_end();

print &ui_form_end([["preview", $text{'onboard_domain_preview'}]]);

&ui_print_footer("index.cgi", $text{'index_return'});
