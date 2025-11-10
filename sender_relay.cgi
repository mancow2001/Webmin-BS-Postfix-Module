#!/usr/bin/perl
# sender_relay.cgi
# Manage sender-dependent relay routing

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'sender_relay_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'sender_relay'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $sender = $in{"sender_$i"};
        my $nexthop = $in{"nexthop_$i"};

        next if (!$sender || $in{"delete_$i"});

        # Validate sender format
        if ($sender !~ /^@?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/) {
            print &ui_alert_box(&text('sender_relay_esender', $sender), 'danger');
            &ui_print_footer("sender_relay.cgi", $text{'index_return'});
            exit;
        }

        # Validate nexthop format
        if (!&validate_relay_host($nexthop)) {
            print &ui_alert_box(&text('sender_relay_enexthop', $nexthop), 'danger');
            &ui_print_footer("sender_relay.cgi", $text{'index_return'});
            exit;
        }

        push(@entries, {
            'type' => 'mapping',
            'key' => $sender,
            'value' => $nexthop,
            'comment' => ''
        });
    }

    # Save file
    my $err = &write_hash_map($config{'sender_relay_map'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_hash_map($config{'sender_relay_map'});
        if ($err) {
            print &ui_alert_box(&text('error_postmap', $err), 'danger');
        } else {
            print &ui_alert_box($text{'sender_relay_updated'}, 'success');
            &webmin_log('modify', 'sender_relay', undef);
        }
    }
}

print "<p>$text{'sender_relay_desc'}</p>";
print "<p><b>$text{'sender_relay_default'}</b></p>";

print &ui_form_start("sender_relay.cgi", "post");

my @entries = &read_hash_map($config{'sender_relay_map'});
my @relay_entries = grep { $_->{'type'} eq 'mapping' } @entries;

print &ui_columns_start([
    $text{'sender_relay_sender'},
    $text{'sender_relay_nexthop'},
    $text{'delete'}
]);

my $idx = 0;
foreach my $entry (@relay_entries) {
    print &ui_columns_row([
        &ui_textbox("sender_$idx", $entry->{'key'}, 30),
        &ui_textbox("nexthop_$idx", $entry->{'value'}, 40),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row for new entry
print &ui_columns_row([
    &ui_textbox("sender_$idx", "", 30),
    &ui_textbox("nexthop_$idx", "[smtp.mailgun.org]:587", 40),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("", $text{'index_return'});
