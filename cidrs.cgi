#!/usr/bin/perl
# cidrs.cgi
# Manage CIDR whitelists for root domain and subdomains

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'cidrs_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'cidrs'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    # Create automatic backup before modifying config
    my $list_type = $in{'list_type'};
    my $list_label = $list_type eq 'root' ? 'root domain' : 'subdomain';
    &create_backup('modify_cidr', "Modified $list_label CIDR whitelist");

    # Determine which list to save
    my $file = $list_type eq 'root' ? $config{'cidr_root_file'} : $config{'cidr_subdomain_file'};

    # Parse form data - reconstruct entries including comments and blanks
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $entry_type = $in{"entry_type_$i"} || 'cidr';

        if ($entry_type eq 'comment') {
            my $comment_text = $in{"comment_text_$i"};
            push(@entries, {
                'type' => 'comment',
                'comment' => $comment_text,
                'cidr' => '',
                'action' => ''
            });
        } elsif ($entry_type eq 'blank') {
            push(@entries, { 'type' => 'blank' });
        } elsif ($entry_type eq 'cidr' || $entry_type eq 'disabled') {
            my $cidr = $in{"cidr_$i"};
            my $comment = $in{"comment_$i"};
            my $action = $in{"action_$i"} || 'OK';

            next if (!$cidr || $in{"delete_$i"});

            # Validate CIDR
            if (!&validate_cidr($cidr)) {
                print &ui_alert_box(&text('cidrs_ecidr', $cidr), 'danger');
                &ui_print_footer("cidrs.cgi", $text{'index_return'});
                exit;
            }

            my $enabled = $in{"enabled_$i"} ? 1 : 0;
            push(@entries, {
                'type' => $enabled ? 'cidr' : 'disabled',
                'cidr' => $cidr,
                'action' => $action,
                'comment' => $comment
            });
        }
    }

    # Add final reject rules
    push(@entries, {
        'type' => 'cidr',
        'cidr' => '0.0.0.0/0',
        'action' => 'reject',
        'comment' => 'everything else gets rejected'
    });
    push(@entries, {
        'type' => 'cidr',
        'cidr' => '::/0',
        'action' => 'reject',
        'comment' => ''
    });

    # Save file
    my $err = &write_cidr_file($file, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_cidr_hash($file);
        if ($err) {
            print &ui_alert_box(&text('cidrs_postmap_failed', $err), 'danger');
        } else {
            print &ui_alert_box($text{'cidrs_updated'}, 'success');
            &webmin_log('modify', $list_type eq 'root' ? 'cidr_root' : 'cidr_subdomain', undef);
        }
    }
}

# Helper function to render a CIDR list with full comment/blank preservation
sub render_cidr_list {
    my ($list_type, $title, $desc, $file) = @_;

    print &ui_hr();
    print "<h3>$title</h3>";
    print "<p>$desc</p>";

    print &ui_form_start("cidrs.cgi", "post");
    print &ui_hidden("list_type", $list_type);

    my @all_entries = &read_cidr_file($file);

    print &ui_columns_start([
        $text{'cidrs_cidr'},
        $text{'cidrs_comment'},
        $text{'cidrs_enabled'},
        $text{'cidrs_delete'}
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
        } elsif ($entry->{'type'} eq 'disabled') {
            # Render disabled CIDR row (dimmed)
            print &ui_hidden("entry_type_$idx", "disabled");
            print &ui_hidden("action_$idx", $entry->{'action'});
            print "<tr style='opacity:0.5'><td>" .
                &ui_textbox("cidr_$idx", $entry->{'cidr'}, 20) . "</td><td>" .
                &ui_textbox("comment_$idx", $entry->{'comment'}, 40) . "</td><td>" .
                &ui_checkbox("enabled_$idx", "1", "", 0) . "</td><td>" .
                &ui_checkbox("delete_$idx", "1", "", 0) . "</td></tr>\n";
            $idx++;
        } elsif ($entry->{'type'} eq 'cidr' && $entry->{'action'} ne 'reject') {
            # Render editable CIDR row
            print &ui_hidden("entry_type_$idx", "cidr");
            print &ui_hidden("action_$idx", "OK");
            print &ui_columns_row([
                &ui_textbox("cidr_$idx", $entry->{'cidr'}, 20),
                &ui_textbox("comment_$idx", $entry->{'comment'}, 40),
                &ui_checkbox("enabled_$idx", "1", "", 1),
                &ui_checkbox("delete_$idx", "1", "", 0)
            ]);
            $idx++;
        }
        # Skip reject entries - they are auto-appended on save
    }

    # Add one empty row for new entry
    print &ui_hidden("entry_type_$idx", "cidr");
    print &ui_hidden("action_$idx", "OK");
    print &ui_columns_row([
        &ui_textbox("cidr_$idx", "", 20),
        &ui_textbox("comment_$idx", "", 40),
        &ui_checkbox("enabled_$idx", "1", "", 1),
        ""
    ]);
    $idx++;

    print "<input type='hidden' name='count' id='count_$list_type' value='$idx'>";
    print &ui_columns_end();

    # Add Row button - styled to match Webmin theme buttons
    print "<button type='button' onclick=\"addCidrRow_$list_type()\" " .
          "class='btn btn-default ui_button' " .
          "style='margin-top:5px; padding:4px 12px; cursor:pointer'>" .
          "+ " . &html_escape($text{'cidrs_add'}) . "</button><br><br>";

    # JavaScript to dynamically add rows
    print <<EOF;
<script>
function addCidrRow_$list_type() {
    var countField = document.getElementById('count_$list_type');
    var idx = parseInt(countField.value);
    var table = countField.closest('form').querySelector('table');
    var tbody = table.querySelector('tbody') || table;
    var row = document.createElement('tr');
    row.innerHTML =
        '<td><input type="hidden" name="entry_type_' + idx + '" value="cidr">' +
        '<input type="hidden" name="action_' + idx + '" value="OK">' +
        '<input type="text" name="cidr_' + idx + '" size="20"></td>' +
        '<td><input type="text" name="comment_' + idx + '" size="40"></td>' +
        '<td><input type="checkbox" name="enabled_' + idx + '" value="1" checked></td>' +
        '<td></td>';
    tbody.appendChild(row);
    countField.value = idx + 1;
}
</script>
EOF

    print &ui_form_end([ ["save", $text{'save'}] ]);
}

# Display Root Domain CIDR List
render_cidr_list("root", $text{'cidrs_root_title'}, $text{'cidrs_desc_root'}, $config{'cidr_root_file'});

# Display Subdomain CIDR List
render_cidr_list("subdomain", $text{'cidrs_subdomain_title'}, $text{'cidrs_desc_subdomain'}, $config{'cidr_subdomain_file'});

&ui_print_footer("index.cgi", $text{'index_return'});
