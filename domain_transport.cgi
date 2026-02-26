#!/usr/bin/perl
# domain_transport.cgi
# Manage domain transport rules (hash transport map and regexp transport map)

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'domain_transport_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'transport'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle save action for hash transport map
if ($in{'save_hash'}) {
    &create_backup('modify_transport', "Modified hash transport map");

    my $file = $config{'transport_file'};
    my @entries;
    my $count = $in{'hash_count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $entry_type = $in{"hash_entry_type_$i"} || 'mapping';

        if ($entry_type eq 'comment') {
            push(@entries, {
                'type' => 'comment',
                'comment' => $in{"hash_comment_text_$i"},
                'key' => '',
                'value' => ''
            });
        } elsif ($entry_type eq 'blank') {
            push(@entries, { 'type' => 'blank' });
        } elsif ($entry_type eq 'mapping') {
            my $domain = $in{"hash_domain_$i"};
            my $transport = $in{"hash_transport_$i"};
            my $comment = $in{"hash_comment_$i"};

            next if (!$domain || $in{"hash_delete_$i"});

            push(@entries, {
                'type' => 'mapping',
                'key' => $domain,
                'value' => $transport,
                'comment' => $comment
            });
        }
    }

    my $err = &write_hash_map($file, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        $err = &update_hash_map($file);
        if ($err) {
            print &ui_alert_box(&text('domain_transport_postmap_failed', $err), 'danger');
        } else {
            print &ui_alert_box($text{'domain_transport_updated'}, 'success');
            &webmin_log('modify', 'transport_hash', undef);
        }
    }
}

# Handle save action for regexp transport map
if ($in{'save_regexp'}) {
    &create_backup('modify_transport', "Modified regexp transport map");

    my $file = $config{'domain_transport_file'};
    my @entries;
    my $count = $in{'regexp_count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $entry_type = $in{"regexp_entry_type_$i"} || 'pcre';

        if ($entry_type eq 'comment') {
            push(@entries, {
                'type' => 'comment',
                'comment' => $in{"regexp_comment_text_$i"},
                'pattern' => '',
                'action' => ''
            });
        } elsif ($entry_type eq 'blank') {
            push(@entries, { 'type' => 'blank' });
        } elsif ($entry_type eq 'pcre') {
            my $pattern = $in{"regexp_pattern_$i"};
            my $transport = $in{"regexp_transport_$i"};
            my $comment = $in{"regexp_comment_$i"};

            next if (!$pattern || $in{"regexp_delete_$i"});

            push(@entries, {
                'type' => 'pcre',
                'pattern' => $pattern,
                'action' => $transport,
                'comment' => $comment
            });
        }
    }

    my $err = &write_pcre_file($file, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # PCRE files are read directly by Postfix — no postmap needed
        print &ui_alert_box($text{'domain_transport_updated'}, 'success');
        &webmin_log('modify', 'transport_regexp', undef);
    }
}

# Display description
print "<p>$text{'domain_transport_desc'}</p>";

# --- Section 1: Hash Transport Map ---
print &ui_hr();
print "<h3>$text{'domain_transport_hash_title'}</h3>";

print &ui_form_start("domain_transport.cgi", "post");

my @hash_entries = &read_hash_map($config{'transport_file'});

print &ui_columns_start([
    $text{'domain_transport_pattern'},
    $text{'domain_transport_transport'},
    $text{'domain_transport_comment'},
    $text{'domain_transport_delete'}
]);

my $idx = 0;
foreach my $entry (@hash_entries) {
    if ($entry->{'type'} eq 'comment') {
        print &ui_hidden("hash_entry_type_$idx", "comment");
        print &ui_hidden("hash_comment_text_$idx", $entry->{'comment'});
        print &ui_columns_row([
            "<b style='color:#555'>#" . &html_escape($entry->{'comment'}) . "</b>",
            "", "", ""
        ]);
        $idx++;
    } elsif ($entry->{'type'} eq 'blank') {
        print &ui_hidden("hash_entry_type_$idx", "blank");
        $idx++;
    } elsif ($entry->{'type'} eq 'mapping') {
        print &ui_hidden("hash_entry_type_$idx", "mapping");
        print &ui_columns_row([
            &ui_textbox("hash_domain_$idx", $entry->{'key'}, 35),
            &ui_textbox("hash_transport_$idx", $entry->{'value'}, 30),
            &ui_textbox("hash_comment_$idx", $entry->{'comment'}, 25),
            &ui_checkbox("hash_delete_$idx", "1", "", 0)
        ]);
        $idx++;
    }
}

# Add one empty row
print &ui_hidden("hash_entry_type_$idx", "mapping");
print &ui_columns_row([
    &ui_textbox("hash_domain_$idx", "", 35),
    &ui_textbox("hash_transport_$idx", "", 30),
    &ui_textbox("hash_comment_$idx", "", 25),
    ""
]);
$idx++;

print "<input type='hidden' name='hash_count' id='count_hash' value='$idx'>";
print &ui_columns_end();

print "<button type='button' onclick=\"addHashRow()\" " .
      "class='btn btn-default ui_button' " .
      "style='margin-top:5px; padding:4px 12px; cursor:pointer'>" .
      "+ " . &html_escape($text{'domain_transport_add'}) . "</button><br><br>";

print <<EOF;
<script>
function addHashRow() {
    var countField = document.getElementById('count_hash');
    var idx = parseInt(countField.value);
    var table = countField.closest('form').querySelector('table');
    var tbody = table.querySelector('tbody') || table;
    var row = document.createElement('tr');
    row.innerHTML =
        '<td><input type="hidden" name="hash_entry_type_' + idx + '" value="mapping">' +
        '<input type="text" name="hash_domain_' + idx + '" size="35"></td>' +
        '<td><input type="text" name="hash_transport_' + idx + '" size="30"></td>' +
        '<td><input type="text" name="hash_comment_' + idx + '" size="25"></td>' +
        '<td></td>';
    tbody.appendChild(row);
    countField.value = idx + 1;
}
</script>
EOF

print &ui_form_end([ ["save_hash", $text{'save'}] ]);

# --- Section 2: Regexp Transport Map ---
print &ui_hr();
print "<h3>$text{'domain_transport_regexp_title'}</h3>";

print &ui_form_start("domain_transport.cgi", "post");

my @regexp_entries = &read_pcre_file($config{'domain_transport_file'});

print &ui_columns_start([
    $text{'domain_transport_pattern'},
    $text{'domain_transport_transport'},
    $text{'domain_transport_comment'},
    $text{'domain_transport_delete'}
]);

$idx = 0;
foreach my $entry (@regexp_entries) {
    if ($entry->{'type'} eq 'comment') {
        print &ui_hidden("regexp_entry_type_$idx", "comment");
        print &ui_hidden("regexp_comment_text_$idx", $entry->{'comment'});
        print &ui_columns_row([
            "<b style='color:#555'>#" . &html_escape($entry->{'comment'}) . "</b>",
            "", "", ""
        ]);
        $idx++;
    } elsif ($entry->{'type'} eq 'blank') {
        print &ui_hidden("regexp_entry_type_$idx", "blank");
        $idx++;
    } elsif ($entry->{'type'} eq 'pcre') {
        print &ui_hidden("regexp_entry_type_$idx", "pcre");
        print &ui_columns_row([
            &ui_textbox("regexp_pattern_$idx", $entry->{'pattern'}, 45),
            &ui_textbox("regexp_transport_$idx", $entry->{'action'}, 25),
            &ui_textbox("regexp_comment_$idx", $entry->{'comment'}, 20),
            &ui_checkbox("regexp_delete_$idx", "1", "", 0)
        ]);
        $idx++;
    }
}

# Add one empty row
print &ui_hidden("regexp_entry_type_$idx", "pcre");
print &ui_columns_row([
    &ui_textbox("regexp_pattern_$idx", "", 45),
    &ui_textbox("regexp_transport_$idx", "", 25),
    &ui_textbox("regexp_comment_$idx", "", 20),
    ""
]);
$idx++;

print "<input type='hidden' name='regexp_count' id='count_regexp' value='$idx'>";
print &ui_columns_end();

print "<button type='button' onclick=\"addRegexpRow()\" " .
      "class='btn btn-default ui_button' " .
      "style='margin-top:5px; padding:4px 12px; cursor:pointer'>" .
      "+ " . &html_escape($text{'domain_transport_add'}) . "</button><br><br>";

print <<EOF;
<script>
function addRegexpRow() {
    var countField = document.getElementById('count_regexp');
    var idx = parseInt(countField.value);
    var table = countField.closest('form').querySelector('table');
    var tbody = table.querySelector('tbody') || table;
    var row = document.createElement('tr');
    row.innerHTML =
        '<td><input type="hidden" name="regexp_entry_type_' + idx + '" value="pcre">' +
        '<input type="text" name="regexp_pattern_' + idx + '" size="45"></td>' +
        '<td><input type="text" name="regexp_transport_' + idx + '" size="25"></td>' +
        '<td><input type="text" name="regexp_comment_' + idx + '" size="20"></td>' +
        '<td></td>';
    tbody.appendChild(row);
    countField.value = idx + 1;
}
</script>
EOF

print &ui_form_end([ ["save_regexp", $text{'save'}] ]);

&ui_print_footer("index.cgi", $text{'index_return'});
