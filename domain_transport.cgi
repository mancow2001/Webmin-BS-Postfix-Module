#!/usr/bin/perl
# domain_transport.cgi
# Manage domain transport rules (hash and regexp)

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'domain_transport_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'transport'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle save hash transport
if ($in{'save_hash'}) {
    my @entries;
    my $count = $in{'count_hash'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $domain = $in{"domain_$i"};
        my $transport = $in{"transport_$i"};

        next if (!$domain || $in{"delete_$i"});

        push(@entries, {
            'type' => 'mapping',
            'key' => $domain,
            'value' => $transport,
            'comment' => ''
        });
    }

    # Save file
    my $err = &write_hash_map($config{'transport_file'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_hash_map($config{'transport_file'});
        if ($err) {
            print &ui_alert_box(&text('error_postmap', $err), 'danger');
        } else {
            print &ui_alert_box($text{'domain_transport_updated'}, 'success');
            &webmin_log('modify', 'transport', undef);
        }
    }
}

# Handle save regexp transport
if ($in{'save_regexp'}) {
    my @entries;
    my $count = $in{'count_regexp'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $pattern = $in{"pattern_$i"};
        my $transport = $in{"transport_r_$i"};

        next if (!$pattern || $in{"delete_r_$i"});

        push(@entries, {
            'type' => 'pcre',
            'pattern' => $pattern,
            'action' => $transport,
            'comment' => ''
        });
    }

    # Save file
    my $err = &write_pcre_file($config{'domain_transport_file'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        print &ui_alert_box($text{'domain_transport_updated'}, 'success');
        &webmin_log('modify', 'domain_transport', undef);
    }
}

print "<p>$text{'domain_transport_desc'}</p>";

# Display Hash Transport Map
print &ui_hr();
print "<h3>$text{'domain_transport_hash_title'}</h3>";

print &ui_form_start("domain_transport.cgi", "post");

my @hash_entries = &read_hash_map($config{'transport_file'});
my @transport_entries = grep { $_->{'type'} eq 'mapping' } @hash_entries;

print &ui_columns_start([
    $text{'domain_transport_pattern'},
    $text{'domain_transport_transport'},
    $text{'delete'}
]);

my $idx = 0;
foreach my $entry (@transport_entries) {
    print &ui_columns_row([
        &ui_textbox("domain_$idx", $entry->{'key'}, 30),
        &ui_textbox("transport_$idx", $entry->{'value'}, 40),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row
print &ui_columns_row([
    &ui_textbox("domain_$idx", "", 30),
    &ui_textbox("transport_$idx", "relay:[smtp.mailgun.org]:587", 40),
    ""
]);
$idx++;

print &ui_hidden("count_hash", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save_hash", $text{'save'}] ]);

# Display Regexp Transport Map
print &ui_hr();
print "<h3>$text{'domain_transport_regexp_title'}</h3>";

print &ui_form_start("domain_transport.cgi", "post");

my @regexp_entries = &read_pcre_file($config{'domain_transport_file'});
my @regexp_maps = grep { $_->{'type'} eq 'pcre' } @regexp_entries;

print &ui_columns_start([
    $text{'domain_transport_pattern'},
    $text{'domain_transport_transport'},
    $text{'delete'}
]);

$idx = 0;
foreach my $entry (@regexp_maps) {
    print &ui_columns_row([
        &ui_textbox("pattern_$idx", $entry->{'pattern'}, 30),
        &ui_textbox("transport_r_$idx", $entry->{'action'}, 40),
        &ui_checkbox("delete_r_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row
print &ui_columns_row([
    &ui_textbox("pattern_$idx", "", 30),
    &ui_textbox("transport_r_$idx", "smtp:[host]:25", 40),
    ""
]);
$idx++;

print &ui_hidden("count_regexp", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save_regexp", $text{'save'}] ]);

&ui_print_footer("index.cgi", $text{'index_return'});
