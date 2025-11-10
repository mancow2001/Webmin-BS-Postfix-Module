#!/usr/bin/perl
# queue.cgi
# View and manage mail queue

require './brightspeed-postfix-lib.pl';

&ReadParse();
&ui_print_header(undef, $text{'queue_title'}, "", undef, 1, 1);

# Check ACL
if (!$access{'queue'}) {
    print &ui_alert_box($text{'error_permission_denied'}, 'danger');
    &ui_print_footer("", $text{'index_return'});
    exit;
}

# Handle flush action
if ($in{'flush'}) {
    my $err = &flush_mail_queue();
    if ($err) {
        print &ui_alert_box($err, 'danger');
    } else {
        print &ui_alert_box($text{'queue_flushed'}, 'success');
    }
}

# Handle delete action
if ($in{'delete'}) {
    my $queue_id = $in{'queue_id'};
    my $err = &delete_queue_message($queue_id);
    if ($err) {
        print &ui_alert_box($err, 'danger');
    } else {
        print &ui_alert_box($text{'queue_deleted'}, 'success');
    }
}

print "<p>$text{'queue_desc'}</p>";

# Get queue contents
my @queue = &get_mail_queue();

if (@queue) {
    print &ui_form_start("queue.cgi", "post");
    print &ui_submit($text{'queue_flush'}, "flush");
    print &ui_form_end();

    print "<br>";
    print &ui_table_start($text{'queue_title'}, "width=100%", 4);
    print &ui_table_row(undef, [
        "<b>$text{'queue_id'}</b>",
        "<b>$text{'queue_size'}</b>",
        "<b>$text{'queue_sender'}</b>",
        "<b>$text{'queue_action'}</b>"
    ], 4, ["align=left"]);

    foreach my $msg (@queue) {
        print &ui_table_row(undef, [
            $msg->{'id'},
            $msg->{'size'},
            $msg->{'sender'},
            &ui_form_start("queue.cgi", "post") .
            &ui_hidden("queue_id", $msg->{'id'}) .
            &ui_submit($text{'queue_delete'}, "delete") .
            &ui_form_end()
        ], 4);
    }

    print &ui_table_end();
} else {
    print &ui_alert_box($text{'queue_empty'}, 'info');
}

&ui_print_footer("", $text{'index_return'});
