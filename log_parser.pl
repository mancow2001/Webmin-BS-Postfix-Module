#!/usr/bin/perl
# log_parser.pl
# Parse module actions into human-readable descriptions for Webmin action log

do 'brightspeed-postfix-lib.pl';

=head1 NAME

log_parser.pl - Parse Brightspeed Postfix Relay module action log

=head1 DESCRIPTION

This script parses the action log entries for the Brightspeed Postfix Relay module
and converts them into human-readable descriptions.

=head1 FUNCTIONS

=over 4

=item parse_webmin_log($user, $script, $action, $type, $object, \%params)

Parse a log entry and return a human-readable description.

=cut

sub parse_webmin_log {
    my ($user, $script, $action, $type, $object, $p) = @_;

    if ($action eq 'reload' && $type eq 'postfix') {
        return "Reloaded Postfix configuration";
    }
    elsif ($action eq 'start' && $type eq 'postfix') {
        return "Started Postfix service";
    }
    elsif ($action eq 'stop' && $type eq 'postfix') {
        return "Stopped Postfix service";
    }
    elsif ($action eq 'onboard' && $type eq 'subdomain') {
        return "Onboarded subdomain $object";
    }
    elsif ($action eq 'remove' && $type eq 'subdomain') {
        return "Removed subdomain $object";
    }
    elsif ($action eq 'modify' && $type eq 'cidr_root') {
        return "Modified root domain CIDR whitelist";
    }
    elsif ($action eq 'modify' && $type eq 'cidr_subdomain') {
        return "Modified subdomain CIDR whitelist";
    }
    elsif ($action eq 'modify' && $type eq 'sender_relay') {
        return "Modified sender relay map";
    }
    elsif ($action eq 'modify' && $type eq 'transport') {
        return "Modified transport rules";
    }
    elsif ($action eq 'modify' && $type eq 'headers') {
        return "Modified header validation rules";
    }
    elsif ($action eq 'modify' && $type eq 'virtual') {
        return "Modified virtual domain aliases";
    }
    elsif ($action eq 'modify' && $type eq 'sasl') {
        return "Modified SASL credentials";
    }
    elsif ($action eq 'flush' && $type eq 'queue') {
        return "Flushed mail queue";
    }
    elsif ($action eq 'delete' && $type eq 'queue') {
        return "Deleted queue message $object";
    }
    else {
        return "Unknown action: $action $type $object";
    }
}

=back

=cut

1;
