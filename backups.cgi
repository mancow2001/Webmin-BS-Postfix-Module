#!/usr/bin/perl
# backups.cgi
# Configuration backup history, change viewer, and restore

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();

# Check ACL
if (!$access{'backups'}) {
    &ui_print_header(undef, $text{'backup_title'}, "", undef, 1, 1);
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Action label mapping
my %action_labels = (
    'onboard_domain'  => $text{'backup_action_onboard_domain'},
    'offboard_domain' => $text{'backup_action_offboard_domain'},
    'modify_cidr'     => $text{'backup_action_modify_cidr'},
    'pre_restore'     => $text{'backup_action_pre_restore'},
    'modify_sender_relay' => $text{'backup_action_modify_sender_relay'},
    'modify_transport'    => $text{'backup_action_modify_transport'},
);

# Handle restore confirmation
if ($in{'do_restore'} && $in{'backup_name'}) {
    &ui_print_header(undef, $text{'backup_title'}, "", undef, 1, 1);

    my $backup_name = $in{'backup_name'};
    # Validate backup name format
    if ($backup_name !~ /^\d{8}-\d{6}$/) {
        print &ui_alert_box(&text('backup_error', 'Invalid backup name'), 'danger');
        &ui_print_footer("backups.cgi", $text{'backup_back'});
        exit;
    }

    my $err = &restore_backup($backup_name);
    if ($err) {
        print &ui_alert_box(&text('backup_error', $err), 'danger');
    } else {
        print &ui_alert_box(&text('backup_restored', $backup_name), 'success');
    }

    &ui_print_footer("backups.cgi", $text{'backup_back'});
    exit;
}

# Handle restore confirmation page
if ($in{'restore'}) {
    &ui_print_header(undef, $text{'backup_confirm_title'}, "", undef, 1, 1);

    my $backup_name = $in{'restore'};
    if ($backup_name !~ /^\d{8}-\d{6}$/) {
        print &ui_alert_box(&text('backup_error', 'Invalid backup name'), 'danger');
        &ui_print_footer("backups.cgi", $text{'backup_back'});
        exit;
    }

    print "<p>" . &text('backup_confirm_desc', $backup_name) . "</p>";

    # Show what will be restored
    my @managed = &get_managed_files();
    my $backup_dir = &get_backup_dir() . "/$backup_name";

    print &ui_columns_start([$text{'backup_files'}, $text{'control_status'}]);
    foreach my $entry (@managed) {
        my ($config_key, $basename) = @$entry;
        my $exists = -f "$backup_dir/$basename" ? "OK" : "Not in backup";
        print &ui_columns_row(["<code>$basename</code>", $exists]);
    }
    print &ui_columns_end();

    print "<br>";
    print &ui_form_start("backups.cgi", "post");
    print &ui_hidden("backup_name", $backup_name);
    print &ui_form_end([["do_restore", $text{'backup_confirm_button'}]]);

    &ui_print_footer("backups.cgi", $text{'backup_back'});
    exit;
}

# Handle view changes page
if ($in{'view'}) {
    &ui_print_header(undef, $text{'backup_view_title'}, "", undef, 1, 1);

    my $backup_name = $in{'view'};
    if ($backup_name !~ /^\d{8}-\d{6}$/) {
        print &ui_alert_box(&text('backup_error', 'Invalid backup name'), 'danger');
        &ui_print_footer("backups.cgi", $text{'backup_back'});
        exit;
    }

    print "<p>" . &text('backup_view_desc', $backup_name) . "</p>";

    my $result = &get_backup_changes($backup_name);
    my @changes = @{$result->{'changes'}};

    if (!$result->{'has_changes'}) {
        print &ui_alert_box($text{'backup_no_diff'}, 'info');
    } else {
        foreach my $file (@changes) {
            my $status_label = $file->{'changed'} ?
                "<span style='color:red; font-weight:bold'>$text{'backup_file_changed'}</span>" :
                "<span style='color:green'>$text{'backup_file_unchanged'}</span>";

            print "<h4><code>" . &html_escape($file->{'basename'}) . "</code> &mdash; $status_label</h4>";

            if ($file->{'changed'} && $file->{'diff'}) {
                print "<pre style='background:#f5f5f5; padding:10px; border:1px solid #ddd; overflow-x:auto; font-size:12px'>";
                print &html_escape($file->{'diff'});
                print "</pre>";
            }
        }
    }

    &ui_print_footer("backups.cgi", $text{'backup_back'});
    exit;
}

# Default: show backup listing
&ui_print_header(undef, $text{'backup_title'}, "", undef, 1, 1);

print "<p>$text{'backup_desc'}</p>";

my @backups = &list_backups();

if (!@backups) {
    print &ui_alert_box($text{'backup_none'}, 'info');
} else {
    print &ui_columns_start([
        $text{'backup_date'},
        $text{'backup_action'},
        $text{'backup_description'},
        $text{'backup_user'},
        $text{'backup_files'},
        $text{'backup_actions'}
    ]);

    foreach my $backup (@backups) {
        my $action_label = $action_labels{$backup->{'action'}} || $backup->{'action'};
        my $actions = &ui_link("backups.cgi?view=" . &urlize($backup->{'dir_name'}), $text{'backup_view'}) .
                      " | " .
                      &ui_link("backups.cgi?restore=" . &urlize($backup->{'dir_name'}), $text{'backup_restore'});

        print &ui_columns_row([
            &html_escape($backup->{'date'}),
            &html_escape($action_label),
            &html_escape($backup->{'description'}),
            &html_escape($backup->{'user'}),
            $backup->{'files_backed_up'} || '0',
            $actions
        ]);
    }

    print &ui_columns_end();
}

&ui_print_footer("index.cgi", $text{'index_return'});
