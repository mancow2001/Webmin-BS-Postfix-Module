#!/usr/bin/perl
# servers.cgi
# View and test configured mail log servers

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, "Mail Log Servers", "", undef, 1, 1);

# Check ACL
if (!$access{'servers'}) {
    print &ui_alert_box("Access denied", 'danger');
    &ui_print_footer("index.cgi", "Return to Dashboard");
    exit;
}

# Get configured servers
my @servers = &get_configured_servers();

# Display info box
print &ui_alert_box("Configure remote servers via <b>Webmin Configuration → Modules → Brightspeed Postfix Relay → Module Config</b>. This page shows the current configuration and allows you to test server connectivity.", 'info');

# Display servers table
print "<br>";
print &ui_table_start("Configured Mail Log Servers", "width=100%", 4);
print &ui_table_row(undef,
    "<b>Server Name</b>",
    "<b>Log Path</b>",
    "<b>Status</b>",
    "<b>Actions</b>"
);

foreach my $server (@servers) {
    my $name = $server->{'name'};
    my $path = $server->{'path'};
    my $is_local = $server->{'is_local'} ? 'Yes' : 'No';

    # Check availability
    my $available = &check_server_availability($path);
    my $status_html;

    if ($available) {
        $status_html = &ui_text_color("✓ Available", 'success');
    } else {
        $status_html = &ui_text_color("✗ Unavailable", 'danger');
    }

    # Add type indicator
    my $name_display = $name;
    if ($server->{'is_local'}) {
        $name_display .= " (Local)";
    } else {
        $name_display .= " (Remote NFS)";
    }

    # Action button
    my $action_html = &ui_link("servers.cgi?test=" . $server->{'server_num'}, "Test Connection");

    print &ui_table_row(undef,
        $name_display,
        "<code>$path</code>",
        $status_html,
        $action_html
    );
}

print &ui_table_end();

# If test parameter is present, show test results
if (defined($in{'test'})) {
    my $server_num = $in{'test'};
    my ($server) = grep { $_->{'server_num'} == $server_num } @servers;

    if ($server) {
        print "<br>";
        print "<h3>Testing Connection: " . $server->{'name'} . "</h3>";

        my $path = $server->{'path'};
        my $available = &check_server_availability($path);

        if ($available) {
            # Try to read a few lines
            my @entries = &get_mail_logs($path, undef, undef, 10);

            print &ui_alert_box("Connection successful! Found " . scalar(@entries) . " recent log entries.", 'success');

            if (@entries > 0) {
                print &ui_table_start("Recent Log Entries (up to 10)", "width=100%", 1);
                foreach my $entry (@entries) {
                    my $line = $entry->{'timestamp'} . " " . $entry->{'hostname'} . " postfix/" .
                               $entry->{'process'} . "[" . $entry->{'pid'} . "]: " . $entry->{'message'};
                    print &ui_table_row(undef, "<small><code>$line</code></small>");
                }
                print &ui_table_end();
            }
        } else {
            my $error_msg = "Connection failed! ";

            if (!-e $path) {
                $error_msg .= "Path does not exist: <code>$path</code>";
            } elsif (!-f $path) {
                $error_msg .= "Path exists but is not a file: <code>$path</code>";
            } elsif (!-r $path) {
                $error_msg .= "Path exists but is not readable (check permissions): <code>$path</code>";
            } else {
                $error_msg .= "Unknown error accessing: <code>$path</code>";
            }

            print &ui_alert_box($error_msg, 'danger');

            # Show troubleshooting tips
            print "<h4>Troubleshooting Tips:</h4>";
            print "<ul>";
            print "<li>Verify the NFS share is mounted: <code>mount | grep " . quotemeta($path) . "</code></li>";
            print "<li>Check file exists: <code>ls -l " . quotemeta($path) . "</code></li>";
            print "<li>Verify permissions: File must be readable by the web server user</li>";
            print "<li>Test NFS connectivity: <code>df -h " . quotemeta($path) . "</code></li>";
            print "</ul>";
        }
    }
}

# Summary statistics
print "<br>";
my $total = scalar(@servers);
my $available_count = grep { &check_server_availability($_->{'path'}) } @servers;
my $unavailable_count = $total - $available_count;

print &ui_table_start("Summary", "width=100%", 2);
print &ui_table_row("Total Servers", $total);
print &ui_table_row("Available", &ui_text_color($available_count, 'success'));
print &ui_table_row("Unavailable", $unavailable_count > 0 ? &ui_text_color($unavailable_count, 'danger') : 0);
print &ui_table_end();

&ui_print_footer("index.cgi", "Return to Dashboard");
