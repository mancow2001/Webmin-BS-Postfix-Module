#!/usr/bin/perl
# offboard_domain.cgi
# Domain offboarding interface

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'offboard_domain_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'offboard_domain'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle confirm action (after preview)
if ($in{'confirm'}) {
    my @domains_to_remove;

    # Collect selected domains
    foreach my $key (keys %in) {
        if ($key =~ /^delete_(.+)$/ && $in{$key}) {
            push(@domains_to_remove, $1);
        }
    }

    if (!@domains_to_remove) {
        print &ui_alert_box($text{'offboard_domain_enone_selected'}, 'danger');
    } else {
        # Call the offboard_domain_full function
        my $err = &offboard_domain_full(\@domains_to_remove);

        if ($err) {
            print &ui_alert_box(&text('offboard_domain_error', $err), 'danger');
        } else {
            my $count = scalar(@domains_to_remove);
            print &ui_alert_box(&text('offboard_domain_success', $count), 'success');

            # Show offboarded domains
            print "<p><strong>$text{'offboard_domain_removed_list'}</strong></p>";
            print "<ul>";
            foreach my $domain (@domains_to_remove) {
                print "<li><code>$domain</code></li>";
            }
            print "</ul>";
        }
    }

    print "<p><a href='offboard_domain.cgi'>$text{'offboard_domain_back'}</a></p>";
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle preview action
if ($in{'preview'}) {
    my @domains_to_remove;

    # Collect selected domains
    foreach my $key (keys %in) {
        if ($key =~ /^delete_(.+)$/ && $in{$key}) {
            push(@domains_to_remove, $1);
        }
    }

    if (!@domains_to_remove) {
        print &ui_alert_box($text{'offboard_domain_enone_selected'}, 'danger');
        # Show form again
        goto SHOW_FORM;
    } else {
        # Show confirmation
        print &ui_alert_box($text{'offboard_domain_warning'}, 'warn');

        print "<h3>$text{'offboard_domain_confirm_title'}</h3>";
        print "<p>" . &text('offboard_domain_confirm_desc', scalar(@domains_to_remove)) . "</p>";

        print "<ul>";
        foreach my $domain (@domains_to_remove) {
            print "<li><code>$domain</code></li>";
        }
        print "</ul>";

        print "<p>$text{'offboard_domain_files_affected'}</p>";
        print "<ul>";
        print "<li>$text{'offboard_domain_file_header_checks'}</li>";
        print "<li>$text{'offboard_domain_file_sasl_passwd'}</li>";
        print "<li>$text{'offboard_domain_file_sender_relay'}</li>";
        print "</ul>";

        # Confirmation form
        print &ui_form_start("offboard_domain.cgi", "post");
        foreach my $domain (@domains_to_remove) {
            print &ui_hidden("delete_$domain", "1");
        }
        print &ui_form_end([
            ["confirm", $text{'offboard_domain_confirm_button'}],
            ["cancel", $text{'cancel'}]
        ]);

        &ui_print_footer("offboard_domain.cgi", $text{'offboard_domain_back_to_list'}, "index.cgi", $text{'index_return'});
        exit;
    }
}

SHOW_FORM:

# Get list of onboarded domains from sender_relay_map
my @relay_entries = &read_hash_map($config{'sender_relay_map'});
my @onboarded_domains;

foreach my $entry (@relay_entries) {
    if ($entry->{'type'} eq 'mapping' && $entry->{'key'} =~ /^@(.+)$/) {
        my $domain = $1;
        my $relay_host = $entry->{'value'};
        push(@onboarded_domains, {
            'domain' => $domain,
            'relay' => $relay_host
        });
    }
}

# Show the offboarding form
print "<p>$text{'offboard_domain_desc'}</p>";

if (!@onboarded_domains) {
    print &ui_alert_box($text{'offboard_domain_none_found'}, 'info');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

print &ui_form_start("offboard_domain.cgi", "post");

print &ui_columns_start([
    $text{'offboard_domain_select'},
    $text{'offboard_domain_domain'},
    $text{'offboard_domain_relay_host'}
]);

foreach my $domain_info (@onboarded_domains) {
    my $domain = $domain_info->{'domain'};
    my $relay = $domain_info->{'relay'};

    print &ui_columns_row([
        &ui_checkbox("delete_$domain", "1", "", 0),
        "<code>$domain</code>",
        "<code>$relay</code>"
    ]);
}

print &ui_columns_end();

print "<br>";
print &ui_form_end([["preview", $text{'offboard_domain_preview'}]]);

&ui_print_footer("index.cgi", $text{'index_return'});
