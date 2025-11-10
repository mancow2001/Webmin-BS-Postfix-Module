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

print &ui_columns_start([
    $text{'virtual_source'},
    $text{'virtual_destination'},
    $text{'delete'}
]);

my $idx = 0;
foreach my $entry (@virtual_entries) {
    print &ui_columns_row([
        &ui_textbox("source_$idx", $entry->{'key'}, 30),
        &ui_textbox("dest_$idx", $entry->{'value'}, 30),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row
print &ui_columns_row([
    &ui_textbox("source_$idx", "", 30),
    &ui_textbox("dest_$idx", "", 30),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("", $text{'index_return'});
