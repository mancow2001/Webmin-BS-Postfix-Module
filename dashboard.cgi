#!/usr/bin/perl
# dashboard.cgi
# Mail flow operational dashboard with multi-server support

require './brightspeed-postfix-lib.pl';

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
        print &ui_table_start("", "width=100%", 2);
        print &ui_table_row(undef, "<b>Sender</b>", "<b>Count</b>");
        foreach my $sender (@top_senders) {
            print &ui_table_row(undef, "<code>" . $sender->{'email'} . "</code>", $sender->{'count'});
        }
        print &ui_table_end();
    } else {
        print "<p><i>No sender data available</i></p>";
    }

    print "</td><td width='50%' valign='top'>";

    # Top recipients
    print "<h4>Top 10 Recipients</h4>";
    my @top_recipients = &get_top_recipients($entries, 10);
    if (@top_recipients) {
        print &ui_table_start("", "width=100%", 2);
        print &ui_table_row(undef, "<b>Recipient</b>", "<b>Count</b>");
        foreach my $recipient (@top_recipients) {
            print &ui_table_row(undef, "<code>" . $recipient->{'email'} . "</code>", $recipient->{'count'});
        }
        print &ui_table_end();
    } else {
        print "<p><i>No recipient data available</i></p>";
    }

    print "</td></tr></table>";

    # Top domains
    print "<br>";
    print "<h4>Top 10 Sender Domains</h4>";
    my @top_domains = &get_top_domains($entries, 10);
    if (@top_domains) {
        print &ui_table_start("", "width=100%", 2);
        print &ui_table_row(undef, "<b>Domain</b>", "<b>Count</b>");
        foreach my $domain (@top_domains) {
            print &ui_table_row(undef, "<code>" . $domain->{'domain'} . "</code>", $domain->{'count'});
        }
        print &ui_table_end();
    } else {
        print "<p><i>No domain data available</i></p>";
    }

    # Rejection analysis
    if ($stats->{'reject'} > 0) {
        print "<br>";
        print "<h4>Rejection Analysis</h4>";
        my @rejection_reasons = &get_rejection_reasons($entries);

        if (@rejection_reasons) {
            print &ui_table_start("", "width=100%", 3);
            print &ui_table_row(undef, "<b>Reason</b>", "<b>Count</b>", "<b>Percentage</b>");
            foreach my $reason (@rejection_reasons) {
                print &ui_table_row(undef,
                    $reason->{'reason'},
                    $reason->{'count'},
                    $reason->{'percentage'} . "%"
                );
            }
            print &ui_table_end();
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

    # Display ASCII/HTML bar chart
    print "<pre style='font-family:monospace; background:#f5f5f5; padding:10px; border:1px solid #ddd; overflow-x:auto;'>";

    foreach my $hour (@hours) {
        my $count = $hourly->{$hour};
        my $bar_width = $max_count > 0 ? int(($count / $max_count) * 60) : 0;
        my $bar = "█" x $bar_width;

        printf "%02d:00 | %-60s %d\n", $hour, $bar, $count;
    }

    print "</pre>";
}
