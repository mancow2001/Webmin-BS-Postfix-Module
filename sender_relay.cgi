#!/usr/bin/perl
# sender_relay.cgi
# Manage sender-dependent relay routing (sender_relay_map)

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'sender_relay_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'sender_relay'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    # Create automatic backup before modifying config
    &create_backup('modify_sender_relay', "Modified sender relay map");

    my $file = $config{'sender_relay_map'};

    # Parse form data - reconstruct entries including comments and blanks
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $entry_type = $in{"entry_type_$i"} || 'mapping';

        if ($entry_type eq 'comment') {
            my $comment_text = $in{"comment_text_$i"};
            push(@entries, {
                'type' => 'comment',
                'comment' => $comment_text,
                'key' => '',
                'value' => ''
            });
        } elsif ($entry_type eq 'blank') {
            push(@entries, { 'type' => 'blank' });
        } elsif ($entry_type eq 'mapping') {
            my $sender = $in{"sender_$i"};
            my $nexthop = $in{"nexthop_$i"};
            my $comment = $in{"comment_$i"};

            next if (!$sender || $in{"delete_$i"});

            # Validate sender format: @domain or *
            if ($sender ne '*' && $sender !~ /^@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/) {
                print &ui_alert_box(&text('sender_relay_esender', &html_escape($sender)), 'danger');
                &ui_print_footer("sender_relay.cgi", $text{'index_return'});
                exit;
            }

            # Validate relay host format
            if (!&validate_relay_host($nexthop)) {
                print &ui_alert_box(&text('sender_relay_enexthop', &html_escape($nexthop)), 'danger');
                &ui_print_footer("sender_relay.cgi", $text{'index_return'});
                exit;
            }

            push(@entries, {
                'type' => 'mapping',
                'key' => $sender,
                'value' => $nexthop,
                'comment' => $comment
            });
        }
    }

    # Save file
    my $err = &write_hash_map($file, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_hash_map($file);
        if ($err) {
            print &ui_alert_box(&text('sender_relay_postmap_failed', $err), 'danger');
        } else {
            # Reload Postfix to apply changes
            $err = &reload_postfix();
            if ($err) {
                print &ui_alert_box(&text('sender_relay_reload_failed', $err), 'danger');
            } else {
                print &ui_alert_box($text{'sender_relay_updated'}, 'success');
                &webmin_log('modify', 'sender_relay', undef);
            }
        }
    }
}

# Display sender relay map
print "<p>$text{'sender_relay_desc'}</p>";

print &ui_form_start("sender_relay.cgi", "post");

my @all_entries = &read_hash_map($config{'sender_relay_map'});

print &ui_columns_start([
    $text{'sender_relay_sender'},
    $text{'sender_relay_nexthop'},
    $text{'sender_relay_comment'},
    $text{'sender_relay_delete'}
]);

my $idx = 0;
foreach my $entry (@all_entries) {
    if ($entry->{'type'} eq 'comment') {
        # Render comment as a visible section header row with hidden fields
        print &ui_hidden("entry_type_$idx", "comment");
        print &ui_hidden("comment_text_$idx", $entry->{'comment'});
        print &ui_columns_row([
            "<b style='color:#555'>#" . &html_escape($entry->{'comment'}) . "</b>",
            "", "", ""
        ]);
        $idx++;
    } elsif ($entry->{'type'} eq 'blank') {
        # Preserve blank line as hidden field only
        print &ui_hidden("entry_type_$idx", "blank");
        $idx++;
    } elsif ($entry->{'type'} eq 'mapping') {
        # Render editable mapping row
        print &ui_hidden("entry_type_$idx", "mapping");
        print &ui_columns_row([
            &ui_textbox("sender_$idx", $entry->{'key'}, 35),
            &ui_textbox("nexthop_$idx", $entry->{'value'}, 30),
            &ui_textbox("comment_$idx", $entry->{'comment'}, 30),
            &ui_checkbox("delete_$idx", "1", "", 0)
        ]);
        $idx++;
    }
}

# Add one empty row for new entry
print &ui_hidden("entry_type_$idx", "mapping");
print &ui_columns_row([
    &ui_textbox("sender_$idx", "", 35),
    &ui_textbox("nexthop_$idx", "", 30),
    &ui_textbox("comment_$idx", "", 30),
    ""
]);
$idx++;

print "<input type='hidden' name='count' id='count_sender_relay' value='$idx'>";
print &ui_columns_end();

# Add Row button
print "<button type='button' onclick=\"addSenderRelayRow()\" " .
      "class='btn btn-default ui_button' " .
      "style='margin-top:5px; padding:4px 12px; cursor:pointer'>" .
      "+ " . &html_escape($text{'sender_relay_add'}) . "</button><br><br>";

# JavaScript to dynamically add rows
print <<EOF;
<script>
function addSenderRelayRow() {
    var countField = document.getElementById('count_sender_relay');
    var idx = parseInt(countField.value);
    var table = countField.closest('form').querySelector('table');
    var tbody = table.querySelector('tbody') || table;
    var row = document.createElement('tr');
    row.innerHTML =
        '<td><input type="hidden" name="entry_type_' + idx + '" value="mapping">' +
        '<input type="text" name="sender_' + idx + '" size="35"></td>' +
        '<td><input type="text" name="nexthop_' + idx + '" size="30"></td>' +
        '<td><input type="text" name="comment_' + idx + '" size="30"></td>' +
        '<td></td>';
    tbody.appendChild(row);
    countField.value = idx + 1;
}
</script>
EOF

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("index.cgi", $text{'index_return'});
