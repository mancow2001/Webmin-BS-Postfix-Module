#!/usr/bin/perl
# headers.cgi
# Manage header validation rules

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'headers_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'headers'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $pattern = $in{"pattern_$i"};
        my $action = $in{"action_$i"};

        next if (!$pattern || $in{"delete_$i"});

        push(@entries, {
            'type' => 'pcre',
            'pattern' => $pattern,
            'action' => $action,
            'comment' => ''
        });
    }

    # Add final reject rule
    push(@entries, {
        'type' => 'pcre',
        'pattern' => '/^From:/',
        'action' => 'REJECT "From:" header must be @brightspeed.com or @brightspeedbroadband.net or onboarded sub-domain',
        'comment' => ''
    });

    # Save file
    my $err = &write_pcre_file($config{'header_checks_file'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        print &ui_alert_box($text{'headers_updated'}, 'success');
        &webmin_log('modify', 'headers', undef);
    }
}

print "<p>$text{'headers_desc'}</p>";

print &ui_form_start("headers.cgi", "post");

my @entries = &read_pcre_file($config{'header_checks_file'});
my @header_entries = grep { $_->{'type'} eq 'pcre' && $_->{'action'} ne 'REJECT "From:" header must be @brightspeed.com or @brightspeedbroadband.net or onboarded sub-domain' } @entries;

print &ui_columns_start([
    $text{'headers_pattern'},
    $text{'headers_action'},
    $text{'delete'}
]);

my $idx = 0;
foreach my $entry (@header_entries) {
    print &ui_columns_row([
        &ui_textbox("pattern_$idx", $entry->{'pattern'}, 40),
        &ui_select("action_$idx", $entry->{'action'}, [['IGNORE', 'IGNORE'], ['REJECT', 'REJECT']]),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row
print &ui_columns_row([
    &ui_textbox("pattern_$idx", "", 40),
    &ui_select("action_$idx", "IGNORE", [['IGNORE', 'IGNORE'], ['REJECT', 'REJECT']]),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("", $text{'index_return'});
