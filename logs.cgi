#!/usr/bin/perl
# logs.cgi
# View Postfix mail logs

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'logs_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'logs'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

print "<p>$text{'logs_desc'}</p>";

# Determine log file
my $log_file = $config{'mail_log_file'};
if (!-f $log_file && -f $config{'alt_mail_log_file'}) {
    $log_file = $config{'alt_mail_log_file'};
}

if (!-f $log_file) {
    print &ui_alert_box("Mail log file not found at $log_file", 'warn');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

# Filter option
my $filter = $in{'filter'} || '';

print &ui_form_start("logs.cgi", "get");
print "Filter: ";
print &ui_textbox("filter", $filter, 40);
print &ui_submit($text{'logs_filter'});
if ($filter) {
    print " | ";
    print &ui_link("logs.cgi", $text{'logs_clear_filter'});
}
print &ui_form_end();

print "<br>";

# Read last 100 lines
my @lines;
if ($filter) {
    @lines = split(/\n/, `grep -i '$filter' '$log_file' | tail -100`);
} else {
    @lines = split(/\n/, `tail -100 '$log_file'`);
}

# Display logs
print "<div style='background: #f5f5f5; border: 1px solid #ddd; padding: 10px; font-family: monospace; font-size: 12px; overflow-x: auto; max-height: 600px; overflow-y: auto;'>";

foreach my $line (@lines) {
    # Color code important keywords
    $line =~ s/(error|Error|ERROR)/<span style='color: red; font-weight: bold;'>$1<\/span>/gi;
    $line =~ s/(warning|Warning|WARNING)/<span style='color: orange; font-weight: bold;'>$1<\/span>/gi;
    $line =~ s/(reject|Reject|REJECT)/<span style='color: red;'>$1<\/span>/gi;
    $line =~ s/(accept|Accept|ACCEPT)/<span style='color: green;'>$1<\/span>/gi;
    $line =~ s/(relay)/<span style='color: blue;'>$1<\/span>/gi;

    print &html_escape($line) . "<br>";
}

print "</div>";

# Refresh button
print "<br>";
print &ui_link("logs.cgi" . ($filter ? "?filter=$filter" : ""), $text{'logs_refresh'});

&ui_print_footer("index.cgi", $text{'index_return'});
