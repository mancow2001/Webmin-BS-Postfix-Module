#!/usr/bin/perl
# sasl.cgi
# Manage SASL authentication credentials

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'sasl_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'sasl'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Handle save action
if ($in{'save'}) {
    my @entries;
    my $count = $in{'count'} || 0;

    for (my $i = 0; $i < $count; $i++) {
        my $host = $in{"host_$i"};
        my $username = $in{"username_$i"};
        my $password = $in{"password_$i"};

        next if (!$host || $in{"delete_$i"});

        my $value = "$username:$password";
        push(@entries, {
            'type' => 'mapping',
            'key' => $host,
            'value' => $value,
            'comment' => ''
        });
    }

    # Save file
    my $err = &write_hash_map($config{'sasl_passwd_file'}, \@entries);
    if ($err) {
        print &ui_alert_box(&text('error_file_write', $err), 'danger');
    } else {
        # Run postmap
        $err = &update_hash_map($config{'sasl_passwd_file'});
        if ($err) {
            print &ui_alert_box(&text('error_postmap', $err), 'danger');
        } else {
            # Set secure permissions
            chmod(0600, $config{'sasl_passwd_file'});
            chmod(0600, $config{'sasl_passwd_file'} . '.db');

            print &ui_alert_box($text{'sasl_updated'}, 'success');
            &webmin_log('modify', 'sasl', undef);
        }
    }
}

print "<p>$text{'sasl_desc'}</p>";
print &ui_alert_box($text{'sasl_warning'}, 'warn');

print &ui_form_start("sasl.cgi", "post");

my @entries = &read_hash_map($config{'sasl_passwd_file'});
my @sasl_entries = grep { $_->{'type'} eq 'mapping' } @entries;

print &ui_columns_start([
    $text{'sasl_host'},
    $text{'sasl_username'},
    $text{'sasl_password'},
    $text{'delete'}
]);

my $idx = 0;
foreach my $entry (@sasl_entries) {
    my ($username, $password) = split(/:/, $entry->{'value'}, 2);

    print &ui_columns_row([
        &ui_textbox("host_$idx", $entry->{'key'}, 30),
        &ui_textbox("username_$idx", $username, 20),
        &ui_password("password_$idx", $password, 20),
        &ui_checkbox("delete_$idx", "1", "", 0)
    ]);
    $idx++;
}

# Add empty row
print &ui_columns_row([
    &ui_textbox("host_$idx", "[smtp.mailgun.org]:587", 30),
    &ui_textbox("username_$idx", "", 20),
    &ui_password("password_$idx", "", 20),
    ""
]);
$idx++;

print &ui_hidden("count", $idx);
print &ui_columns_end();

print &ui_form_end([ ["save", $text{'save'}] ]);

&ui_print_footer("index.cgi", $text{'index_return'});
