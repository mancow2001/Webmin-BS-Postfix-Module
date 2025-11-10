#!/usr/bin/perl
# brightspeed-postfix-lib.pl
# Core library functions for Brightspeed Postfix Relay module

=head1 NAME

brightspeed-postfix-lib.pl - Core library for Brightspeed Postfix Relay module

=head1 DESCRIPTION

This library provides functions for managing a Brightspeed Postfix mail relay gateway,
including CIDR whitelist management, subdomain onboarding, sender-dependent routing,
and transport rule configuration.

=cut

BEGIN { push(@INC, ".."); }
use WebminCore;
init_config();

our %access = get_module_acl();
our %config = %{get_module_config()};

# Default configuration file paths
$config{'postfix_config_dir'} ||= "/etc/postfix";
$config{'postfix_main_cf'} ||= "$config{'postfix_config_dir'}/main.cf";
$config{'postfix_master_cf'} ||= "$config{'postfix_config_dir'}/master.cf";
$config{'postfix_command'} ||= "postfix";
$config{'postmap_command'} ||= "postmap";
$config{'postconf_command'} ||= "postconf";

# Brightspeed-specific configuration files
$config{'cidr_root_file'} ||= "$config{'postfix_config_dir'}/allowed_brightspeed_root_cidrs";
$config{'cidr_subdomain_file'} ||= "$config{'postfix_config_dir'}/allowed_brightspeed_subdomain_cidrs";
$config{'allow_root_pcre'} ||= "$config{'postfix_config_dir'}/allow_brightspeed_root.pcre";
$config{'block_root_pcre'} ||= "$config{'postfix_config_dir'}/block_brightspeed_root.pcre";
$config{'allow_subdomain_pcre'} ||= "$config{'postfix_config_dir'}/allow_brightspeed_subdomains.pcre";
$config{'sender_relay_map'} ||= "$config{'postfix_config_dir'}/sender_relay_map";
$config{'transport_file'} ||= "$config{'postfix_config_dir'}/transport";
$config{'domain_transport_file'} ||= "$config{'postfix_config_dir'}/domain-transport";
$config{'header_checks_file'} ||= "$config{'postfix_config_dir'}/header_checks";
$config{'virtual_file'} ||= "$config{'postfix_config_dir'}/virtual";
$config{'v_domains_file'} ||= "$config{'postfix_config_dir'}/v-domains";
$config{'sasl_passwd_file'} ||= "$config{'postfix_config_dir'}/sasl_passwd";

=head1 FUNCTIONS

=head2 Postfix Configuration Functions

=over 4

=item get_postfix_version()

Returns the Postfix version string.

=cut

sub get_postfix_version {
    my $out = backquote_command("$config{'postconf_command'} mail_version 2>&1");
    if ($out =~ /mail_version\s*=\s*(.+)/) {
        return $1;
    }
    return undef;
}

=item get_postfix_param($parameter)

Get a Postfix configuration parameter value from main.cf.

=cut

sub get_postfix_param {
    my ($param) = @_;
    my $out = backquote_command("$config{'postconf_command'} -h $param 2>&1");
    chomp($out);
    return $out;
}

=item set_postfix_param($parameter, $value)

Set a Postfix configuration parameter in main.cf.

=cut

sub set_postfix_param {
    my ($param, $value) = @_;
    my $rv = system_logged("$config{'postconf_command'} -e \"$param=$value\" >/dev/null 2>&1");
    return $rv == 0 ? undef : $?;
}

=item check_postfix_config()

Check Postfix configuration for errors. Returns undef on success, error message on failure.

=cut

sub check_postfix_config {
    my $out = backquote_command("$config{'postfix_command'} check 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Configuration check failed";
    }
    return undef;
}

=item reload_postfix()

Reload Postfix configuration. Returns undef on success, error message on failure.

=cut

sub reload_postfix {
    my $out = backquote_command("$config{'postfix_command'} reload 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Reload failed";
    }
    webmin_log('reload', 'postfix', undef);
    return undef;
}

=item start_postfix()

Start Postfix service. Returns undef on success, error message on failure.

=cut

sub start_postfix {
    my $out = backquote_command("$config{'postfix_command'} start 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Start failed";
    }
    webmin_log('start', 'postfix', undef);
    return undef;
}

=item stop_postfix()

Stop Postfix service. Returns undef on success, error message on failure.

=cut

sub stop_postfix {
    my $out = backquote_command("$config{'postfix_command'} stop 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Stop failed";
    }
    webmin_log('stop', 'postfix', undef);
    return undef;
}

=item get_postfix_status()

Check if Postfix is running. Returns 1 if running, 0 if stopped.

=cut

sub get_postfix_status {
    my $out = backquote_command("$config{'postfix_command'} status 2>&1");
    return $? == 0 ? 1 : 0;
}

=head2 CIDR Management Functions

=item read_cidr_file($filename)

Read a CIDR file and return array of hashrefs with keys: cidr, comment, action.

=cut

sub read_cidr_file {
    my ($filename) = @_;
    my @entries;

    if (!-f $filename) {
        return @entries;
    }

    open(my $fh, '<', $filename) or return @entries;
    while (my $line = <$fh>) {
        chomp($line);

        # Skip empty lines
        next if $line =~ /^\s*$/;

        # Extract comment if present
        my $comment = '';
        if ($line =~ /^([^#]+)#(.+)$/) {
            $line = $1;
            $comment = $2;
            $comment =~ s/^\s+|\s+$//g;
        } elsif ($line =~ /^#(.+)$/) {
            # Full-line comment
            push(@entries, {
                'type' => 'comment',
                'comment' => $1,
                'cidr' => '',
                'action' => ''
            });
            next;
        }

        # Parse CIDR and action
        if ($line =~ /^\s*(\S+)\s+(\S+)\s*$/) {
            push(@entries, {
                'type' => 'cidr',
                'cidr' => $1,
                'action' => $2,
                'comment' => $comment
            });
        }
    }
    close($fh);

    return @entries;
}

=item write_cidr_file($filename, \@entries)

Write CIDR entries to file. Entries should be hashrefs with keys: type, cidr, action, comment.

=cut

sub write_cidr_file {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'comment') {
            print $fh "#" . $entry->{'comment'} . "\n";
        } elsif ($entry->{'type'} eq 'cidr') {
            my $line = sprintf("%-20s\t%s", $entry->{'cidr'}, $entry->{'action'});
            if ($entry->{'comment'}) {
                $line .= "\t#" . $entry->{'comment'};
            }
            print $fh $line . "\n";
        }
    }

    close($fh);
    return undef;
}

=item validate_cidr($cidr)

Validate CIDR format. Returns 1 if valid, 0 if invalid.

=cut

sub validate_cidr {
    my ($cidr) = @_;

    # IPv4 CIDR format
    if ($cidr =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\/(\d{1,2})$/) {
        my ($a, $b, $c, $d, $mask) = ($1, $2, $3, $4, $5);
        return 0 if ($a > 255 || $b > 255 || $c > 255 || $d > 255 || $mask > 32);
        return 1;
    }

    # IPv6 CIDR format (simplified check)
    if ($cidr =~ /^[0-9a-fA-F:]+\/\d{1,3}$/) {
        return 1;
    }

    # Single IP (IPv4)
    if ($cidr =~ /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/) {
        my ($a, $b, $c, $d) = ($1, $2, $3, $4);
        return 0 if ($a > 255 || $b > 255 || $c > 255 || $d > 255);
        return 1;
    }

    return 0;
}

=item update_cidr_hash($filename)

Run postmap to update hash database for CIDR file. Returns undef on success, error message on failure.

=cut

sub update_cidr_hash {
    my ($filename) = @_;
    my $out = backquote_command("$config{'postmap_command'} cidr:$filename 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "postmap failed";
    }
    return undef;
}

=head2 PCRE Map Functions

=item read_pcre_file($filename)

Read a PCRE file and return array of hashrefs with keys: pattern, action, comment.

=cut

sub read_pcre_file {
    my ($filename) = @_;
    my @entries;

    if (!-f $filename) {
        return @entries;
    }

    open(my $fh, '<', $filename) or return @entries;
    while (my $line = <$fh>) {
        chomp($line);

        # Skip empty lines
        next if $line =~ /^\s*$/;

        # Full-line comment
        if ($line =~ /^#(.+)$/) {
            push(@entries, {
                'type' => 'comment',
                'comment' => $1,
                'pattern' => '',
                'action' => ''
            });
            next;
        }

        # Parse pattern and action
        if ($line =~ /^\s*(\S+)\s+(.+?)\s*$/) {
            push(@entries, {
                'type' => 'pcre',
                'pattern' => $1,
                'action' => $2,
                'comment' => ''
            });
        }
    }
    close($fh);

    return @entries;
}

=item write_pcre_file($filename, \@entries)

Write PCRE entries to file.

=cut

sub write_pcre_file {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'comment') {
            print $fh "#" . $entry->{'comment'} . "\n";
        } elsif ($entry->{'type'} eq 'pcre') {
            print $fh $entry->{'pattern'} . " " . $entry->{'action'} . "\n";
        }
    }

    close($fh);
    return undef;
}

=head2 Hash Map Functions

=item read_hash_map($filename)

Read a hash map file (e.g., transport, sender_relay_map) and return array of hashrefs.

=cut

sub read_hash_map {
    my ($filename) = @_;
    my @entries;

    if (!-f $filename) {
        return @entries;
    }

    open(my $fh, '<', $filename) or return @entries;
    while (my $line = <$fh>) {
        chomp($line);

        # Skip empty lines
        next if $line =~ /^\s*$/;

        # Extract comment
        my $comment = '';
        if ($line =~ /^([^#]+)#(.+)$/) {
            $line = $1;
            $comment = $2;
            $comment =~ s/^\s+|\s+$//g;
        } elsif ($line =~ /^#(.+)$/) {
            # Full-line comment
            push(@entries, {
                'type' => 'comment',
                'comment' => $1,
                'key' => '',
                'value' => ''
            });
            next;
        }

        # Parse key and value
        if ($line =~ /^\s*(\S+)\s+(.+?)\s*$/) {
            push(@entries, {
                'type' => 'mapping',
                'key' => $1,
                'value' => $2,
                'comment' => $comment
            });
        }
    }
    close($fh);

    return @entries;
}

=item write_hash_map($filename, \@entries)

Write hash map entries to file.

=cut

sub write_hash_map {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'comment') {
            print $fh "#" . $entry->{'comment'} . "\n";
        } elsif ($entry->{'type'} eq 'mapping') {
            my $line = $entry->{'key'} . "\t" . $entry->{'value'};
            if ($entry->{'comment'}) {
                $line .= " #" . $entry->{'comment'};
            }
            print $fh $line . "\n";
        }
    }

    close($fh);
    return undef;
}

=item update_hash_map($filename)

Run postmap to update hash database. Returns undef on success, error message on failure.

=cut

sub update_hash_map {
    my ($filename) = @_;
    my $out = backquote_command("$config{'postmap_command'} hash:$filename 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "postmap failed";
    }
    return undef;
}

=head2 Subdomain Management Functions

=item onboard_subdomain($subdomain, $relay_type, $relay_host)

Onboard a new subdomain by adding it to all required configuration files.
Returns undef on success, error message on failure.

=cut

sub onboard_subdomain {
    my ($subdomain, $relay_type, $relay_host) = @_;

    # Validate subdomain format
    if ($subdomain !~ /^[a-z0-9-]+\.brightspeed(broadband)?\.com$/) {
        return "Invalid subdomain format";
    }

    # Default relay host
    $relay_host ||= '[smtp.mailgun.org]:587';

    # Add to allow_brightspeed_subdomains.pcre
    my @pcre_entries = read_pcre_file($config{'allow_subdomain_pcre'});
    my $pattern = '/\.' . quotemeta($subdomain) . '$/';
    push(@pcre_entries, {
        'type' => 'pcre',
        'pattern' => $pattern,
        'action' => 'allow_brightspeed_subdomains',
        'comment' => ''
    });
    my $err = write_pcre_file($config{'allow_subdomain_pcre'}, \@pcre_entries);
    return $err if $err;

    # Add to header_checks
    my @header_entries = read_pcre_file($config{'header_checks_file'});
    my $header_pattern = '/^From: .*@' . quotemeta($subdomain) . '/';
    push(@header_entries, {
        'type' => 'pcre',
        'pattern' => $header_pattern,
        'action' => 'IGNORE',
        'comment' => ''
    });
    $err = write_pcre_file($config{'header_checks_file'}, \@header_entries);
    return $err if $err;

    # Add to sender_relay_map
    my @relay_entries = read_hash_map($config{'sender_relay_map'});
    push(@relay_entries, {
        'type' => 'mapping',
        'key' => '@' . $subdomain,
        'value' => $relay_host,
        'comment' => ''
    });
    $err = write_hash_map($config{'sender_relay_map'}, \@relay_entries);
    return $err if $err;
    $err = update_hash_map($config{'sender_relay_map'});
    return $err if $err;

    webmin_log('onboard', 'subdomain', $subdomain, { 'relay' => $relay_host });
    return undef;
}

=item remove_subdomain($subdomain)

Remove a subdomain from all configuration files.
Returns undef on success, error message on failure.

=cut

sub remove_subdomain {
    my ($subdomain) = @_;

    # Remove from allow_brightspeed_subdomains.pcre
    my @pcre_entries = read_pcre_file($config{'allow_subdomain_pcre'});
    @pcre_entries = grep { $_->{'pattern'} !~ /\Q$subdomain\E/ } @pcre_entries;
    my $err = write_pcre_file($config{'allow_subdomain_pcre'}, \@pcre_entries);
    return $err if $err;

    # Remove from header_checks
    my @header_entries = read_pcre_file($config{'header_checks_file'});
    @header_entries = grep { $_->{'pattern'} !~ /\Q$subdomain\E/ } @header_entries;
    $err = write_pcre_file($config{'header_checks_file'}, \@header_entries);
    return $err if $err;

    # Remove from sender_relay_map
    my @relay_entries = read_hash_map($config{'sender_relay_map'});
    @relay_entries = grep { $_->{'key'} !~ /\Q$subdomain\E/ } @relay_entries;
    $err = write_hash_map($config{'sender_relay_map'}, \@relay_entries);
    return $err if $err;
    $err = update_hash_map($config{'sender_relay_map'});
    return $err if $err;

    webmin_log('remove', 'subdomain', $subdomain);
    return undef;
}

=head2 Validation Functions

=item validate_domain($domain)

Validate domain format. Returns 1 if valid, 0 if invalid.

=cut

sub validate_domain {
    my ($domain) = @_;
    return $domain =~ /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
}

=item validate_email($email)

Validate email address format. Returns 1 if valid, 0 if invalid.

=cut

sub validate_email {
    my ($email) = @_;
    return $email =~ /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
}

=item validate_relay_host($host)

Validate relay host format. Returns 1 if valid, 0 if invalid.

=cut

sub validate_relay_host {
    my ($host) = @_;
    # Allow [host]:port or host:port format
    return $host =~ /^(\[?[a-zA-Z0-9.-]+\]?)(:\d+)?$/;
}

=head2 Queue Management Functions

=item get_mail_queue()

Get mail queue contents. Returns array of hashrefs with message details.

=cut

sub get_mail_queue {
    my @queue;
    my $out = backquote_command("postqueue -p 2>&1");

    foreach my $line (split(/\n/, $out)) {
        if ($line =~ /^([A-F0-9]+)[\s*!]+(\d+)\s+\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+(.+)$/) {
            my ($id, $size, $sender) = ($1, $2, $3);
            push(@queue, {
                'id' => $id,
                'size' => $size,
                'sender' => $sender
            });
        }
    }

    return @queue;
}

=item flush_mail_queue()

Flush the mail queue (retry all messages). Returns undef on success, error message on failure.

=cut

sub flush_mail_queue {
    my $out = backquote_command("postqueue -f 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Queue flush failed";
    }
    webmin_log('flush', 'queue', undef);
    return undef;
}

=item delete_queue_message($queue_id)

Delete a specific message from the queue. Returns undef on success, error message on failure.

=cut

sub delete_queue_message {
    my ($queue_id) = @_;
    my $out = backquote_command("postsuper -d $queue_id 2>&1");
    my $rv = $?;
    if ($rv != 0) {
        return $out || "Delete failed";
    }
    webmin_log('delete', 'queue', $queue_id);
    return undef;
}

=back

=head1 AUTHOR

Brightspeed Postfix Relay Module

=head1 LICENSE

This module is licensed under the same terms as Webmin.

=cut

1;
