#!/usr/bin/perl
# cidrs.cgi
# Manage CIDR whitelists for root domain and subdomains

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header("index.cgi", $text{'cidrs_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'cidrs'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    # Determine which list to save
    my $list_type = $in{'list_type'};
    my $file = $list_type eq 'root' ? $config{'cidr_root_file'} : $config{'cidr_subdomain_file'};

    # Parse form data
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
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

        push(@entries, {
            'type' => 'cidr',
            'cidr' => $cidr,
            'action' => $action,
            'comment' => $comment
        });
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

# Display Root Domain CIDR List
print &ui_hr();
print "<h3>$text{'cidrs_root_title'}</h3>";
print "<p>$text{'cidrs_desc_root'}</p>";

print &ui_form_start("cidrs.cgi", "post");
print &ui_hidden("list_type", "root");

my @root_cidrs = &read_cidr_file($config{'cidr_root_file'});
my @root_entries = grep { $_->{'type'} eq 'cidr' && $_->{'action'} ne 'reject' } @root_cidrs;

print &ui_columns_start([
    $text{'cidrs_cidr'},
    $text{'cidrs_comment'},
    $text{'cidrs_action'},
    $text{'cidrs_delete'}
]);

my $idx = 0;
foreach my $entry (@root_entries) {
    print &ui_columns_row([
        &ui_textbox("cidr_$idx", $entry->{'cidr'}, 20),
        &ui_textbox("comment_$idx", $entry->{'comment'}, 40),
        &ui_select("action_$idx", $entry->{'action'}, [['OK', 'OK'], ['reject', 'reject']]),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row for new entry
print &ui_columns_row([
    &ui_textbox("cidr_$idx", "", 20),
    &ui_textbox("comment_$idx", "", 40),
    &ui_select("action_$idx", "OK", [['OK', 'OK'], ['reject', 'reject']]),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

# Display Subdomain CIDR List
print &ui_hr();
print "<h3>$text{'cidrs_subdomain_title'}</h3>";
print "<p>$text{'cidrs_desc_subdomain'}</p>";

print &ui_form_start("cidrs.cgi", "post");
print &ui_hidden("list_type", "subdomain");

my @subdomain_cidrs = &read_cidr_file($config{'cidr_subdomain_file'});
my @subdomain_entries = grep { $_->{'type'} eq 'cidr' && $_->{'action'} ne 'reject' } @subdomain_cidrs;

print &ui_columns_start([
    $text{'cidrs_cidr'},
    $text{'cidrs_comment'},
    $text{'cidrs_action'},
    $text{'cidrs_delete'}
]);

$idx = 0;
foreach my $entry (@subdomain_entries) {
    print &ui_columns_row([
        &ui_textbox("cidr_$idx", $entry->{'cidr'}, 20),
        &ui_textbox("comment_$idx", $entry->{'comment'}, 40),
        &ui_select("action_$idx", $entry->{'action'}, [['OK', 'OK'], ['reject', 'reject']]),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row for new entry
print &ui_columns_row([
    &ui_textbox("cidr_$idx", "", 20),
    &ui_textbox("comment_$idx", "", 40),
    &ui_select("action_$idx", "OK", [['OK', 'OK'], ['reject', 'reject']]),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("", $text{'index_return'});
