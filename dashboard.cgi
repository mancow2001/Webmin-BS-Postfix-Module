#!/usr/bin/perl
# dashboard.cgi
# Mail flow operational dashboard with multi-server support

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, "Mail Flow Dashboard", "", undef, 1, 1);

# Check ACL
if (!$access{'dashboard'}) {
    print &ui_alert_box("Access denied", 'danger');
    &ui_print_footer("index.cgi", "Return to Dashboard");
    exit;
}

# Get configured servers
my @servers = &get_configured_servers();

# Determine time range
my $time_range = $in{'time_range'} || '1h';
my $max_lines = 10000;

if ($time_range eq '6h') {
    $max_lines = 30000;
} elsif ($time_range eq '24h') {
    $max_lines = 50000;
} elsif ($time_range eq '7d') {
    $max_lines = 100000;
}

# Time range selector form
print &ui_form_start("dashboard.cgi", "get");
print &ui_table_start("Time Range", "width=100%", 2);

my @time_options = (
    ['1h', 'Last 1 Hour'],
    ['6h', 'Last 6 Hours'],
    ['24h', 'Last 24 Hours'],
    ['7d', 'Last 7 Days']
);

print &ui_table_row("Select Time Range",
    &ui_select("time_range", $time_range, \@time_options) . " " .
    &ui_submit("Refresh")
);
print &ui_table_end();
print &ui_form_end();

print "<br>";

# Determine selected tab
my $selected_tab = $in{'tab'} || 'all';

# Generate tabs
my @tabs;
push(@tabs, ['all', 'All Servers', "dashboard.cgi?time_range=$time_range&tab=all"]);

foreach my $server (@servers) {
    my $tab_id = "server" . $server->{'server_num'};
    my $tab_label = $server->{'name'};
    push(@tabs, [$tab_id, $tab_label, "dashboard.cgi?time_range=$time_range&tab=$tab_id"]);
}

print &ui_tabs_start(\@tabs, "tab", $selected_tab, 1);

# Process each tab
if ($selected_tab eq 'all') {
    # All Servers Tab - Aggregate View
    print &ui_tabs_start_tab("tab", "all");
    print "<h3>All Servers - Aggregated View</h3>";

    # Get logs from all servers
    my $multi_results = &get_mail_logs_multi(\@servers, undef, undef, $max_lines);

    # Check for unavailable servers
    my @unavailable;
    foreach my $server (@servers) {
        if (!$multi_results->{$server->{'name'}}->{'available'}) {
            push(@unavailable, $server->{'name'});
        }
    }

    if (@unavailable) {
        print &ui_alert_box("Warning: The following servers are unavailable: <b>" . join(', ', @unavailable) . "</b>. Data shown is from available servers only.", 'warn');
    }

    # Combine all entries
    my @all_entries;
    foreach my $server_name (keys %$multi_results) {
        if ($multi_results->{$server_name}->{'available'}) {
            push(@all_entries, @{$multi_results->{$server_name}->{'entries'}});
        }
    }

    &display_metrics(\@all_entries, $time_range);

    print &ui_tabs_end_tab("tab", "all");

} else {
    # Individual Server Tab
    my $server_num = $selected_tab;
    $server_num =~ s/^server//;

    my ($server) = grep { $_->{'server_num'} == $server_num } @servers;

    if ($server) {
        print &ui_tabs_start_tab("tab", $selected_tab);
        print "<h3>" . $server->{'name'} . "</h3>";

        my $available = &check_server_availability($server->{'path'});

        if (!$available) {
            print &ui_alert_box("Server unavailable: Cannot access log file at <code>" . $server->{'path'} . "</code>", 'danger');
        } else {
            my @entries = &get_mail_logs($server->{'path'}, undef, undef, $max_lines);
            &display_metrics(\@entries, $time_range);
        }

        print &ui_tabs_end_tab("tab", $selected_tab);
    }
}

print &ui_tabs_end(1);

&ui_print_footer("index.cgi", "Return to Main Dashboard");


# Helper function to display metrics for a set of log entries
sub display_metrics {
    my ($entries, $time_range) = @_;

    my $entry_count = scalar(@$entries);

    if ($entry_count == 0) {
        print &ui_alert_box("No mail log entries found for the selected time range.", 'info');
        return;
    }

    # Calculate aggregate statistics
    my $stats = &aggregate_mail_stats($entries);

    # Display summary metrics
    print "<br>";
    print "<h4>Summary Statistics (Last $time_range)</h4>";
    print &ui_table_start("", "width=100%", 5);

    print &ui_table_row(undef,
        "<div style='text-align:center'><b>Total Messages</b><br><span style='font-size:24px'>" . $stats->{'total'} . "</span></div>",
        "<div style='text-align:center'><b>Sent</b><br><span style='font-size:24px;color:green'>" . $stats->{'sent'} . "</span><br><small>" . ($stats->{'sent_pct'} || 0) . "%</small></div>",
        "<div style='text-align:center'><b>Rejected</b><br><span style='font-size:24px;color:red'>" . $stats->{'reject'} . "</span><br><small>" . ($stats->{'reject_pct'} || 0) . "%</small></div>",
        "<div style='text-align:center'><b>Deferred</b><br><span style='font-size:24px;color:orange'>" . $stats->{'deferred'} . "</span><br><small>" . ($stats->{'deferred_pct'} || 0) . "%</small></div>",
        "<div style='text-align:center'><b>Bounced</b><br><span style='font-size:24px;color:darkred'>" . $stats->{'bounced'} . "</span><br><small>" . ($stats->{'bounced_pct'} || 0) . "%</small></div>"
    );

    print &ui_table_end();

    # Hourly trend chart
    print "<br>";
    print "<h4>Hourly Message Volume</h4>";
    my $hourly = &group_by_hour($entries);
    &display_hourly_chart($hourly);

    # Two-column layout for top lists
    print "<br>";
    print "<table width='100%'><tr><td width='50%' valign='top'>";

    # Top senders
    print "<h4>Top 10 Senders</h4>";
    my @top_senders = &get_top_senders($entries, 10);
    if (@top_senders) {
        print &ui_columns_start(["Sender", "Count"]);
        foreach my $sender (@top_senders) {
            print &ui_columns_row([
                "<code>" . $sender->{'email'} . "</code>",
                $sender->{'count'}
            ]);
        }
        print &ui_columns_end();
    } else {
        print "<p><i>No sender data available</i></p>";
    }

    print "</td><td width='50%' valign='top'>";

    # Top recipients
    print "<h4>Top 10 Recipients</h4>";
    my @top_recipients = &get_top_recipients($entries, 10);
    if (@top_recipients) {
        print &ui_columns_start(["Recipient", "Count"]);
        foreach my $recipient (@top_recipients) {
            print &ui_columns_row([
                "<code>" . $recipient->{'email'} . "</code>",
                $recipient->{'count'}
            ]);
        }
        print &ui_columns_end();
    } else {
        print "<p><i>No recipient data available</i></p>";
    }

    print "</td></tr></table>";

    # Top domains
    print "<br>";
    print "<h4>Top 10 Sender Domains</h4>";
    my @top_domains = &get_top_domains($entries, 10);
    if (@top_domains) {
        print &ui_columns_start(["Domain", "Count"]);
        foreach my $domain (@top_domains) {
            print &ui_columns_row([
                "<code>" . $domain->{'domain'} . "</code>",
                $domain->{'count'}
            ]);
        }
        print &ui_columns_end();
    } else {
        print "<p><i>No domain data available</i></p>";
    }

    # Rejection analysis
    if ($stats->{'reject'} > 0) {
        print "<br>";
        print "<h4>Rejection Analysis</h4>";
        my @rejection_reasons = &get_rejection_reasons($entries);

        if (@rejection_reasons) {
            print &ui_columns_start(["Reason", "Count", "Percentage", "Top IPs / Senders"]);
            foreach my $reason (@rejection_reasons) {
                # Build IP/Sender list
                my @details;

                # Add top IPs with counts
                if ($reason->{'ips'} && @{$reason->{'ips'}}) {
                    my @ip_list;
                    foreach my $ip (@{$reason->{'ips'}}) {
                        my $count = $reason->{'ip_counts'}->{$ip} || 0;
                        push(@ip_list, "<code>$ip</code> ($count)");
                    }
                    push(@details, "<b>IPs:</b> " . join(", ", @ip_list));
                }

                # Add top senders with counts
                if ($reason->{'senders'} && @{$reason->{'senders'}}) {
                    my @sender_list;
                    foreach my $sender (@{$reason->{'senders'}}) {
                        my $count = $reason->{'sender_counts'}->{$sender} || 0;
                        my $display_sender = $sender || '(empty)';
                        push(@sender_list, "<code>$display_sender</code> ($count)");
                    }
                    push(@details, "<b>Senders:</b> " . join(", ", @sender_list));
                }

                my $details_html = @details ? join("<br>", @details) : "<i>No details</i>";

                print &ui_columns_row([
                    $reason->{'reason'},
                    $reason->{'count'},
                    $reason->{'percentage'} . "%",
                    $details_html
                ]);
            }
            print &ui_columns_end();
        }
    }

    # Data freshness note
    print "<br>";
    print "<p><small><i>Data based on last " . $entry_count . " log entries (max " . $max_lines . " per server). Last updated: " . localtime() . "</i></small></p>";
}

# Helper function to display hourly chart
sub display_hourly_chart {
    my ($hourly) = @_;

    my @hours = sort { $a <=> $b } keys %$hourly;

    if (!@hours) {
        print "<p><i>No hourly data available</i></p>";
        return;
    }

    # Find max value for scaling
    my $max_count = 0;
    foreach my $hour (@hours) {
        $max_count = $hourly->{$hour} if $hourly->{$hour} > $max_count;
    }

    # Avoid division by zero
    $max_count = 1 if $max_count == 0;

    # SVG dimensions
    my $width = 800;
    my $height = 300;
    my $padding = 50;
    my $graph_width = $width - (2 * $padding);
    my $graph_height = $height - (2 * $padding);

    # Start SVG
    print "<svg width='$width' height='$height' style='background:#fff; border:1px solid #ddd;'>\n";

    # Draw axes
    print "<line x1='$padding' y1='$padding' x2='$padding' y2='" . ($height - $padding) . "' stroke='#333' stroke-width='2'/>\n";
    print "<line x1='$padding' y1='" . ($height - $padding) . "' x2='" . ($width - $padding) . "' y2='" . ($height - $padding) . "' stroke='#333' stroke-width='2'/>\n";

    # Draw grid lines and y-axis labels
    for (my $i = 0; $i <= 5; $i++) {
        my $y = $padding + ($graph_height * $i / 5);
        my $value = int($max_count * (5 - $i) / 5);

        # Grid line
        print "<line x1='$padding' y1='$y' x2='" . ($width - $padding) . "' y2='$y' stroke='#ddd' stroke-width='1'/>\n";

        # Y-axis label
        print "<text x='" . ($padding - 10) . "' y='" . ($y + 5) . "' text-anchor='end' font-size='12' fill='#666'>$value</text>\n";
    }

    # Calculate points for line graph
    my @points;
    my $num_hours = scalar(@hours);

    for (my $i = 0; $i < $num_hours; $i++) {
        my $hour = $hours[$i];
        my $count = $hourly->{$hour};

        my $x = $padding + ($graph_width * $i / ($num_hours - 1 || 1));
        my $y = ($height - $padding) - ($graph_height * $count / $max_count);

        push(@points, "$x,$y");

        # Draw point
        print "<circle cx='$x' cy='$y' r='4' fill='#4CAF50'/>\n";

        # X-axis label (every few hours to avoid crowding)
        if ($num_hours <= 12 || $i % 2 == 0) {
            my $label = sprintf("%02d:00", $hour);
            print "<text x='$x' y='" . ($height - $padding + 20) . "' text-anchor='middle' font-size='11' fill='#666'>$label</text>\n";
        }
    }

    # Draw line connecting points
    if (@points > 1) {
        my $polyline = join(" ", @points);
        print "<polyline points='$polyline' fill='none' stroke='#2196F3' stroke-width='2'/>\n";
    }

    # Draw axis labels
    print "<text x='" . ($width / 2) . "' y='" . ($height - 10) . "' text-anchor='middle' font-size='14' font-weight='bold' fill='#333'>Hour</text>\n";
    print "<text x='15' y='" . ($height / 2) . "' text-anchor='middle' font-size='14' font-weight='bold' fill='#333' transform='rotate(-90 15 " . ($height / 2) . ")'>Message Count</text>\n";

    # Draw title
    print "<text x='" . ($width / 2) . "' y='25' text-anchor='middle' font-size='16' font-weight='bold' fill='#333'>Message Volume by Hour</text>\n";

    print "</svg>\n";
}
