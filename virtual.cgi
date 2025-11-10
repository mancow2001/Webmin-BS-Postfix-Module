#!/usr/bin/perl
# virtual.cgi
# Manage virtual domain aliases

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'virtual_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'virtual'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $source = $in{"source_$i"};
        my $dest = $in{"dest_$i"};

        next if (!$source || $in{"delete_$i"});

        push(@entries, {
            'type' => 'mapping',
            'key' => $source,
            'value' => $dest,
            'comment' => ''
        });
    }

    # Save file
    my $err = &write_hash_map($config{'v_domains_file'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_hash_map($config{'v_domains_file'});
        if ($err) {
            print &ui_alert_box(&text('error_postmap', $err), 'danger');
        } else {
            print &ui_alert_box($text{'virtual_updated'}, 'success');
            &webmin_log('modify', 'virtual', undef);
        }
    }
}

print "<p>$text{'virtual_desc'}</p>";

print &ui_form_start("virtual.cgi", "post");

my @entries = &read_hash_map($config{'v_domains_file'});
my @virtual_entries = grep { $_->{'type'} eq 'mapping' } @entries;

print &ui_table_start($text{'virtual_title'}, "width=100%", 3);
print &ui_table_row(undef, [
    "<b>$text{'virtual_source'}</b>",
    "<b>$text{'virtual_destination'}</b>",
    "<b>$text{'delete'}</b>"
], 3, ["align=left"]);

my $idx = 0;
foreach my $entry (@virtual_entries) {
    print &ui_table_row(undef, [
        &ui_textbox("source_$idx", $entry->{'key'}, 30),
        &ui_textbox("dest_$idx", $entry->{'value'}, 30),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ], 3);
    $idx++;
}

# Add empty row
print &ui_table_row(undef, [
    &ui_textbox("source_$idx", "", 30),
    &ui_textbox("dest_$idx", "", 30),
    ""
], 3);
$idx++;

print &ui_hidden("count", $idx);
print &ui_table_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("", $text{'index_return'});
