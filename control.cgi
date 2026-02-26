#!/usr/bin/perl
# control.cgi
# Control Postfix service (start, stop, reload, check)

require './brightspeed-postfix-lib.pl';
%access = &get_module_acl();

&ReadParse();
&ui_print_header(undef, $text{'control_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'control'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("index.cgi", $text{'index_return'});
    exit;
}

my $action = $in{'action'};
my $result;
my $error;

if ($action eq 'start') {
    $error = &start_postfix();
    if ($error) {
        print &ui_alert_box(&text('control_ecommand', $error), 'danger');
    } else {
        print &ui_alert_box($text{'control_started'}, 'success');
    }
}
elsif ($action eq 'stop') {
    $error = &stop_postfix();
    if ($error) {
        print &ui_alert_box(&text('control_ecommand', $error), 'danger');
    } else {
        print &ui_alert_box($text{'control_stopped'}, 'success');
    }
}
elsif ($action eq 'reload') {
    $error = &reload_postfix();
    if ($error) {
        print &ui_alert_box(&text('control_ecommand', $error), 'danger');
    } else {
        print &ui_alert_box($text{'control_reloaded'}, 'success');
    }
}
elsif ($action eq 'check') {
    $error = &check_postfix_config();
    if ($error) {
        print &ui_alert_box(&text('control_check_failed', $error), 'danger');
    } else {
        print &ui_alert_box($text{'control_check_ok'}, 'success');
    }
}

print "<p>$text{'control_desc'}</p>";

# Display current status
print &ui_table_start($text{'control_status'}, "width=100%", 2);

my $status = &get_postfix_status();
my $status_msg = $status ?
    &ui_text_color($text{'index_running'}, 'success') :
    &ui_text_color($text{'index_stopped'}, 'danger');

print &ui_table_row($text{'control_status'}, $status_msg);

print &ui_table_end();

# Display control buttons
print "<br>";
print &ui_table_start("Actions", "width=100%", 1);

my @buttons;

if ($status) {
    push(@buttons,
        &ui_link("control.cgi?action=stop", $text{'control_stop'}),
        &ui_link("control.cgi?action=reload", $text{'control_reload'})
    );
} else {
    push(@buttons,
        &ui_link("control.cgi?action=start", $text{'control_start'})
    );
}

push(@buttons, &ui_link("control.cgi?action=check", $text{'control_check'}));

print &ui_table_row(undef, join(" | ", @buttons));

print &ui_table_end();

&ui_print_footer("index.cgi", $text{'index_return'});
