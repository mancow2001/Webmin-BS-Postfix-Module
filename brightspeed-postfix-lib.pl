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
use POSIX qw(strftime);
use File::Path qw(make_path rmtree);
use File::Basename;
init_config();

# Module variables - %access will be populated by each CGI script
use vars qw(%access);

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

        # Preserve blank lines
        if ($line =~ /^\s*$/) {
            push(@entries, { 'type' => 'blank' });
            next;
        }

        # Extract comment if present
        my $comment = '';
        if ($line =~ /^([^#]+)#(.+)$/) {
            $line = $1;
            $comment = $2;
            $comment =~ s/^\s+|\s+$//g;
        } elsif ($line =~ /^#(.+)$/) {
            my $comment_text = $1;
            # Check if this is a disabled CIDR entry (e.g., #10.143.14.251/32	OK	#comment)
            if ($comment_text =~ /^\s*(\S+)\s+(OK|reject)\s*(?:#\s*(.*))?$/i) {
                push(@entries, {
                    'type' => 'disabled',
                    'cidr' => $1,
                    'action' => $2,
                    'comment' => defined($3) ? $3 : ''
                });
            } else {
                push(@entries, {
                    'type' => 'comment',
                    'comment' => $comment_text,
                    'cidr' => '',
                    'action' => ''
                });
            }
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
Also preserves blank lines (type=blank) and full-line comments (type=comment).

=cut

sub write_cidr_file {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'blank') {
            print $fh "\n";
        } elsif ($entry->{'type'} eq 'comment') {
            print $fh "#" . $entry->{'comment'} . "\n";
        } elsif ($entry->{'type'} eq 'disabled') {
            my $line = "#" . sprintf("%-20s\t%s", $entry->{'cidr'}, $entry->{'action'});
            if ($entry->{'comment'}) {
                $line .= "\t#" . $entry->{'comment'};
            }
            print $fh $line . "\n";
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

No-op for CIDR files. Postfix reads cidr: maps directly as text files on each
lookup — they do not support postmap compilation. This function exists to
maintain a consistent API alongside update_hash_map().

=cut

sub update_cidr_hash {
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

        # Preserve blank lines
        if ($line =~ /^\s*$/) {
            push(@entries, { 'type' => 'blank' });
            next;
        }

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
        # Strategy: Split on whitespace, but the pattern should end with / or similar
        # Most PCRE patterns end with / so look for that as a boundary
        if ($line =~ m{^\s*(/[^/]*/)(.*)$}) {
            # Pattern starts and ends with / (standard PCRE format)
            my $pattern = $1;
            my $rest = $2;
            # Remove leading whitespace from rest to get action
            $rest =~ s/^\s+//;
            if ($rest) {
                push(@entries, {
                    'type' => 'pcre',
                    'pattern' => $pattern,
                    'action' => $rest,
                    'comment' => ''
                });
            }
        } elsif ($line =~ /^\s*(\S+)\s+(.+?)\s*$/) {
            # Fallback: first non-whitespace token is pattern, rest is action
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

Write PCRE entries to file. Also preserves blank lines (type=blank) and full-line comments (type=comment).

=cut

sub write_pcre_file {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'blank') {
            print $fh "\n";
        } elsif ($entry->{'type'} eq 'comment') {
            print $fh "#" . $entry->{'comment'} . "\n";
        } elsif ($entry->{'type'} eq 'pcre') {
            # Use tab for consistent formatting with Postfix files
            print $fh $entry->{'pattern'} . "\t" . $entry->{'action'} . "\n";
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

        # Preserve blank lines
        if ($line =~ /^\s*$/) {
            push(@entries, { 'type' => 'blank' });
            next;
        }

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

Write hash map entries to file. Also preserves blank lines (type=blank) and full-line comments (type=comment).

=cut

sub write_hash_map {
    my ($filename, $entries) = @_;

    open(my $fh, '>', $filename) or return "Failed to open $filename: $!";

    foreach my $entry (@$entries) {
        if ($entry->{'type'} eq 'blank') {
            print $fh "\n";
        } elsif ($entry->{'type'} eq 'comment') {
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

=head2 Domain Management Functions

=item onboard_domain_full($fqdn, $relay_username, $relay_password, $relay_host, $relay_port)

Onboard a new domain with full configuration including SASL authentication.
This function modifies header_checks, sasl_passwd, and sender_relay_map files.
Includes transaction rollback on failure.

Returns undef on success, error message on failure.

=cut

sub onboard_domain_full {
    my ($fqdn, $relay_username, $relay_password, $relay_host, $relay_port) = @_;
    my %backups;
    my @modified_files;

    # Validate inputs
    if (!validate_domain($fqdn)) {
        return "Invalid domain format: $fqdn";
    }

    my $relay_nexthop = "[$relay_host]:$relay_port";
    if (!validate_relay_host($relay_nexthop)) {
        return "Invalid relay host format: $relay_nexthop";
    }

    # Check for duplicates in all files
    my @header_entries = read_pcre_file($config{'header_checks_file'});
    foreach my $entry (@header_entries) {
        if ($entry->{'pattern'} =~ /\Q$fqdn\E/) {
            return "Domain $fqdn already exists in header_checks";
        }
    }

    my @sasl_entries = read_hash_map($config{'sasl_passwd_file'});
    foreach my $entry (@sasl_entries) {
        if ($entry->{'key'} eq '@' . $fqdn) {
            return "Domain $fqdn already exists in sasl_passwd";
        }
    }

    my @relay_entries = read_hash_map($config{'sender_relay_map'});
    foreach my $entry (@relay_entries) {
        if ($entry->{'key'} eq '@' . $fqdn) {
            return "Domain $fqdn already exists in sender_relay_map";
        }
    }

    # Create automatic backup before modifying config
    create_backup('onboard_domain', "Onboarding domain $fqdn");

    # Create transactional backups
    foreach my $file ($config{'header_checks_file'}, $config{'sasl_passwd_file'}, $config{'sender_relay_map'}) {
        my $backup = $file . '.backup.' . time();
        if (!copy_source_dest($file, $backup)) {
            # Clean up any backups already created
            foreach my $bak (values %backups) {
                unlink($bak);
            }
            return "Failed to create backup of $file";
        }
        $backups{$file} = $backup;
    }

    # Modify header_checks - insert before last entry
    my $date_comment = "Onboarded " . strftime("%Y-%m-%d", localtime());
    my $header_pattern = '/^From: .*@' . quotemeta($fqdn) . '/';
    my $comment_entry = {
        'type' => 'comment',
        'comment' => " $fqdn - $date_comment",
        'pattern' => '',
        'action' => ''
    };
    my $new_entry = {
        'type' => 'pcre',
        'pattern' => $header_pattern,
        'action' => 'IGNORE',
        'comment' => ''
    };

    # Insert comment and rule before the last entry (which should be the REJECT rule)
    if (@header_entries > 0) {
        splice(@header_entries, -1, 0, $comment_entry, $new_entry);
    } else {
        push(@header_entries, $new_entry);
    }

    my $err = write_pcre_file($config{'header_checks_file'}, \@header_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update header_checks: $err";
    }
    push(@modified_files, $config{'header_checks_file'});

    # Modify sasl_passwd - append to end (no inline comments for sasl_passwd)
    push(@sasl_entries, {
        'type' => 'mapping',
        'key' => '@' . $fqdn,
        'value' => $relay_username . ':' . $relay_password,
        'comment' => ''
    });

    $err = write_hash_map($config{'sasl_passwd_file'}, \@sasl_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update sasl_passwd: $err";
    }
    push(@modified_files, $config{'sasl_passwd_file'});

    # Set permissions on sasl_passwd
    chmod(0600, $config{'sasl_passwd_file'});

    # Run postmap on sasl_passwd
    $err = update_hash_map($config{'sasl_passwd_file'});
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to run postmap on sasl_passwd: $err";
    }

    # Set permissions on sasl_passwd.db
    chmod(0600, $config{'sasl_passwd_file'} . '.db');

    # Modify sender_relay_map - append to end
    push(@relay_entries, {
        'type' => 'mapping',
        'key' => '@' . $fqdn,
        'value' => $relay_nexthop,
        'comment' => $date_comment
    });

    $err = write_hash_map($config{'sender_relay_map'}, \@relay_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update sender_relay_map: $err";
    }
    push(@modified_files, $config{'sender_relay_map'});

    # Run postmap on sender_relay_map
    $err = update_hash_map($config{'sender_relay_map'});
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to run postmap on sender_relay_map: $err";
    }

    # Apply changes with postfix reload
    $err = reload_postfix();
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        # Re-run postmap after rollback
        update_hash_map($config{'sasl_passwd_file'});
        update_hash_map($config{'sender_relay_map'});
        return "Failed to reload Postfix: $err";
    }

    # Success - remove backups
    foreach my $backup (values %backups) {
        unlink($backup);
    }

    webmin_log('onboard', 'domain', $fqdn, { 'relay' => $relay_nexthop });
    return undef;
}

=item offboard_domain_full(\@fqdns)

Offboard one or more domains by removing them from all configuration files.
This function modifies header_checks, sasl_passwd, and sender_relay_map files.
Includes transaction rollback on failure.

Parameters:
- \@fqdns: Array reference of fully qualified domain names to offboard

Returns undef on success, error message on failure.

=cut

sub offboard_domain_full {
    my ($fqdns_ref) = @_;
    my @fqdns = @$fqdns_ref;
    my %backups;

    return "No domains specified for offboarding" if (!@fqdns);

    # Create automatic backup before modifying config
    my $domain_list = join(', ', @fqdns);
    create_backup('offboard_domain', "Offboarding domain(s): $domain_list");

    # Create transactional backups
    foreach my $file ($config{'header_checks_file'}, $config{'sasl_passwd_file'}, $config{'sender_relay_map'}) {
        my $backup = $file . '.backup.' . time();
        if (!copy_source_dest($file, $backup)) {
            # Clean up any backups already created
            foreach my $bak (values %backups) {
                unlink($bak);
            }
            return "Failed to create backup of $file";
        }
        $backups{$file} = $backup;
    }

    # Modify header_checks - remove entries matching any domain
    my @header_entries = read_pcre_file($config{'header_checks_file'});
    my @new_header_entries;

    # Log the offboarding attempt
    my $domains_str = join(',', @fqdns);
    print STDERR "DEBUG: About to log header_checks_start with domains=$domains_str total=" . scalar(@header_entries) . "\n";
    webmin_log('offboard', 'header_checks_start', "domains=$domains_str total=" . scalar(@header_entries));
    print STDERR "DEBUG: Logged header_checks_start\n";

    foreach my $entry (@header_entries) {
        my $keep = 1;
        # Extract domain from pattern: /^From: .*@domain\.com/ -> domain.com
        if ($entry->{'pattern'} =~ /\@([^\/]+)\//) {
            my $pattern_domain = $1;
            my $pattern_domain_escaped = $pattern_domain;
            # Remove backslash escapes for comparison
            $pattern_domain =~ s/\\//g;

            foreach my $fqdn (@fqdns) {
                webmin_log('offboard', 'header_checks_compare', "pattern=$entry->{'pattern'} escaped=$pattern_domain_escaped unescaped=$pattern_domain vs=$fqdn");

                if ($pattern_domain eq $fqdn) {
                    $keep = 0;
                    webmin_log('offboard', 'header_checks_delete', "MATCH pattern=$entry->{'pattern'} domain=$fqdn");
                    last;
                }
            }
        }
        push(@new_header_entries, $entry) if $keep;
    }

    my $removed = scalar(@header_entries) - scalar(@new_header_entries);
    webmin_log('offboard', 'header_checks_complete', "removed=$removed remaining=" . scalar(@new_header_entries));

    my $err = write_pcre_file($config{'header_checks_file'}, \@new_header_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update header_checks: $err";
    }

    # Modify sasl_passwd - remove entries matching any domain
    my @sasl_entries = read_hash_map($config{'sasl_passwd_file'});
    my @new_sasl_entries;
    foreach my $entry (@sasl_entries) {
        my $keep = 1;
        foreach my $fqdn (@fqdns) {
            if ($entry->{'key'} eq '@' . $fqdn) {
                $keep = 0;
                last;
            }
        }
        push(@new_sasl_entries, $entry) if $keep;
    }

    $err = write_hash_map($config{'sasl_passwd_file'}, \@new_sasl_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update sasl_passwd: $err";
    }

    # Set permissions on sasl_passwd
    chmod(0600, $config{'sasl_passwd_file'});

    # Run postmap on sasl_passwd
    $err = update_hash_map($config{'sasl_passwd_file'});
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to run postmap on sasl_passwd: $err";
    }

    # Set permissions on sasl_passwd.db
    chmod(0600, $config{'sasl_passwd_file'} . '.db');

    # Modify sender_relay_map - remove entries matching any domain
    my @relay_entries = read_hash_map($config{'sender_relay_map'});
    my @new_relay_entries;
    foreach my $entry (@relay_entries) {
        my $keep = 1;
        foreach my $fqdn (@fqdns) {
            if ($entry->{'key'} eq '@' . $fqdn) {
                $keep = 0;
                last;
            }
        }
        push(@new_relay_entries, $entry) if $keep;
    }

    $err = write_hash_map($config{'sender_relay_map'}, \@new_relay_entries);
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to update sender_relay_map: $err";
    }

    # Run postmap on sender_relay_map
    $err = update_hash_map($config{'sender_relay_map'});
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        return "Failed to run postmap on sender_relay_map: $err";
    }

    # Apply changes with postfix reload
    $err = reload_postfix();
    if ($err) {
        # Rollback
        foreach my $file (keys %backups) {
            copy_source_dest($backups{$file}, $file);
            unlink($backups{$file});
        }
        # Re-run postmap after rollback
        update_hash_map($config{'sasl_passwd_file'});
        update_hash_map($config{'sender_relay_map'});
        return "Failed to reload Postfix: $err";
    }

    # Success - remove backups
    foreach my $backup (values %backups) {
        unlink($backup);
    }

    my $domain_list = join(', ', @fqdns);
    webmin_log('offboard', 'domain', $domain_list);
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

=head2 Server Management Functions

=item get_configured_servers()

Get list of configured remote servers. Returns array of hashrefs with keys: name, path, enabled, server_num.

=cut

sub get_configured_servers {
    my @servers;

    # Add local server first
    push(@servers, {
        'name' => 'Local Server',
        'path' => $config{'mail_log_file'},
        'enabled' => 1,
        'server_num' => 0,
        'is_local' => 1
    });

    # Add configured remote servers
    for (my $i = 1; $i <= 5; $i++) {
        my $name = $config{"server${i}_name"};
        my $path = $config{"server${i}_path"};
        my $enabled = $config{"server${i}_enabled"};

        if ($name && $path && $enabled) {
            push(@servers, {
                'name' => $name,
                'path' => $path,
                'enabled' => 1,
                'server_num' => $i,
                'is_local' => 0
            });
        }
    }

    return @servers;
}

=item check_server_availability($log_path)

Check if a log file is accessible. Returns 1 if accessible, 0 if not.

=cut

sub check_server_availability {
    my ($log_path) = @_;

    # Try alternate path if primary doesn't exist (for local server)
    if (!-f $log_path && $log_path eq $config{'mail_log_file'} && $config{'alt_mail_log_file'}) {
        $log_path = $config{'alt_mail_log_file'};
    }

    return (-f $log_path && -r $log_path) ? 1 : 0;
}

=head2 Log Parsing Functions

=item parse_postfix_log_line($line)

Parse a Postfix syslog line. Returns hashref with extracted fields or undef if not a valid Postfix log line.

Fields returned: timestamp, hostname, process, pid, queue_id, status, from, to, relay, delay, dsn, reject_reason, message

=cut

sub parse_postfix_log_line {
    my ($line) = @_;

    # Parse syslog format: Month Day HH:MM:SS hostname process[pid]: message
    if ($line =~ /^(\w+\s+\d+\s+\d+:\d+:\d+)\s+(\S+)\s+postfix\/(\w+)\[(\d+)\]:\s+(.+)$/) {
        my ($timestamp, $hostname, $process, $pid, $message) = ($1, $2, $3, $4, $5);

        my $entry = {
            'timestamp' => $timestamp,
            'hostname' => $hostname,
            'process' => $process,
            'pid' => $pid,
            'message' => $message,
            'queue_id' => '',
            'status' => '',
            'from' => '',
            'to' => '',
            'relay' => '',
            'delay' => '',
            'dsn' => '',
            'reject_reason' => '',
            'client_ip' => ''
        };

        # Extract queue ID (if present)
        if ($message =~ /^([A-F0-9]+):\s+(.+)$/) {
            $entry->{'queue_id'} = $1;
            $message = $2;
        } elsif ($message =~ /^NOQUEUE:\s+(.+)$/) {
            $entry->{'queue_id'} = 'NOQUEUE';
            $message = $1;
        }

        # Determine status
        if ($message =~ /status=sent/i) {
            $entry->{'status'} = 'sent';
        } elsif ($message =~ /status=deferred/i) {
            $entry->{'status'} = 'deferred';
        } elsif ($message =~ /status=bounced/i) {
            $entry->{'status'} = 'bounced';
        } elsif ($message =~ /reject:/i) {
            $entry->{'status'} = 'reject';
        }

        # Extract from address
        if ($message =~ /from=<([^>]*)>/i) {
            $entry->{'from'} = $1;
        }

        # Extract to address
        if ($message =~ /to=<([^>]*)>/i) {
            $entry->{'to'} = $1;
        }

        # Extract relay
        if ($message =~ /relay=([^,\s]+)/i) {
            $entry->{'relay'} = $1;
        }

        # Extract delay
        if ($message =~ /delay=([\d.]+)/i) {
            $entry->{'delay'} = $1;
        }

        # Extract DSN
        if ($message =~ /dsn=([\d.]+)/i) {
            $entry->{'dsn'} = $1;
        }

        # Extract rejection reason and client IP
        if ($entry->{'status'} eq 'reject') {
            if ($message =~ /reject:\s+(.+?)(?:;|$)/i) {
                $entry->{'reject_reason'} = $1;
            }

            # Extract client IP from rejection message
            # Format: "RCPT from unknown[10.152.7.111]:" or "RCPT from hostname[IP]:"
            if ($message =~ /from\s+[^\[]*\[([0-9.]+)\]/i) {
                $entry->{'client_ip'} = $1;
            }
        }

        return $entry;
    }

    return undef;
}

=item get_mail_logs($log_path, $start_time, $end_time, $max_lines)

Read and parse mail logs from a single log file within time range.
Returns array of parsed log entries.

$start_time and $end_time are Unix timestamps (optional, undef for all)
$max_lines limits number of lines read (default 10000)

=cut

sub get_mail_logs {
    my ($log_path, $start_time, $end_time, $max_lines) = @_;
    $max_lines ||= 10000;

    my @entries;

    # Check if file exists and is readable
    if (!-f $log_path) {
        # Try alternate path if this is the primary log
        if ($log_path eq $config{'mail_log_file'} && $config{'alt_mail_log_file'}) {
            $log_path = $config{'alt_mail_log_file'};
        }
        return @entries if (!-f $log_path);
    }

    return @entries if (!-r $log_path);

    # Read log file (tail -n for efficiency)
    my $cmd = "tail -n $max_lines " . quotemeta($log_path);
    my @lines = split(/\n/, backquote_command($cmd));

    foreach my $line (@lines) {
        my $entry = parse_postfix_log_line($line);
        next if (!$entry);

        # Time filtering would require parsing timestamp to Unix time
        # For now, we'll include all entries and filter by date string if needed
        push(@entries, $entry);
    }

    return @entries;
}

=item get_mail_logs_multi(\@servers, $start_time, $end_time, $max_lines)

Read and parse mail logs from multiple servers. Returns hashref with server names as keys,
each containing array of log entries and availability status.

=cut

sub get_mail_logs_multi {
    my ($servers, $start_time, $end_time, $max_lines) = @_;
    my %results;

    foreach my $server (@$servers) {
        my $available = check_server_availability($server->{'path'});

        if ($available) {
            my @entries = get_mail_logs($server->{'path'}, $start_time, $end_time, $max_lines);

            # Tag each entry with server name
            foreach my $entry (@entries) {
                $entry->{'server_name'} = $server->{'name'};
            }

            $results{$server->{'name'}} = {
                'available' => 1,
                'entries' => \@entries,
                'count' => scalar(@entries)
            };
        } else {
            $results{$server->{'name'}} = {
                'available' => 0,
                'entries' => [],
                'count' => 0
            };
        }
    }

    return \%results;
}

=item aggregate_mail_stats(\@log_entries)

Calculate aggregate statistics from log entries. Returns hashref with counts.

=cut

sub aggregate_mail_stats {
    my ($entries) = @_;

    my %stats = (
        'total' => 0,
        'sent' => 0,
        'deferred' => 0,
        'bounced' => 0,
        'reject' => 0
    );

    foreach my $entry (@$entries) {
        $stats{'total'}++;

        if ($entry->{'status'}) {
            $stats{$entry->{'status'}}++;
        }
    }

    # Calculate percentages
    if ($stats{'total'} > 0) {
        foreach my $key (keys %stats) {
            next if $key eq 'total';
            $stats{$key . '_pct'} = sprintf("%.1f", ($stats{$key} / $stats{'total'}) * 100);
        }
    }

    return \%stats;
}

=item get_top_senders(\@log_entries, $limit)

Get top N senders by message count. Returns array of hashrefs with keys: email, count.

=cut

sub get_top_senders {
    my ($entries, $limit) = @_;
    $limit ||= 10;

    my %counts;
    foreach my $entry (@$entries) {
        next if !$entry->{'from'};
        $counts{$entry->{'from'}}++;
    }

    my @sorted = sort { $counts{$b} <=> $counts{$a} } keys %counts;
    my @top = splice(@sorted, 0, $limit);

    return map { { 'email' => $_, 'count' => $counts{$_} } } @top;
}

=item get_top_recipients(\@log_entries, $limit)

Get top N recipients by message count. Returns array of hashrefs with keys: email, count.

=cut

sub get_top_recipients {
    my ($entries, $limit) = @_;
    $limit ||= 10;

    my %counts;
    foreach my $entry (@$entries) {
        next if !$entry->{'to'};
        $counts{$entry->{'to'}}++;
    }

    my @sorted = sort { $counts{$b} <=> $counts{$a} } keys %counts;
    my @top = splice(@sorted, 0, $limit);

    return map { { 'email' => $_, 'count' => $counts{$_} } } @top;
}

=item get_top_domains(\@log_entries, $limit)

Get top N domains (from sender emails) by message count. Returns array of hashrefs with keys: domain, count.

=cut

sub get_top_domains {
    my ($entries, $limit) = @_;
    $limit ||= 10;

    my %counts;
    foreach my $entry (@$entries) {
        if ($entry->{'from'} && $entry->{'from'} =~ /\@(.+)$/) {
            $counts{$1}++;
        }
    }

    my @sorted = sort { $counts{$b} <=> $counts{$a} } keys %counts;
    my @top = splice(@sorted, 0, $limit);

    return map { { 'domain' => $_, 'count' => $counts{$_} } } @top;
}

=item get_rejection_reasons(\@log_entries)

Get rejection reasons with counts, IPs, and senders. Returns array of hashrefs with keys: reason, count, percentage, ips, senders.

=cut

sub get_rejection_reasons {
    my ($entries) = @_;

    my %counts;
    my %ips;      # Track unique IPs per reason
    my %senders;  # Track unique senders per reason
    my $total_rejects = 0;

    foreach my $entry (@$entries) {
        next if $entry->{'status'} ne 'reject';
        $total_rejects++;

        my $reason = $entry->{'reject_reason'} || 'Unknown reason';
        # Normalize common rejection patterns
        $reason =~ s/^RCPT from \S+:\s*//;
        $reason =~ s/from=<[^>]*>\s+to=<[^>]*>//;

        $counts{$reason}++;

        # Track client IP
        if ($entry->{'client_ip'}) {
            $ips{$reason}{$entry->{'client_ip'}}++;
        }

        # Track sender
        if ($entry->{'from'}) {
            $senders{$reason}{$entry->{'from'}}++;
        }
    }

    my @sorted = sort { $counts{$b} <=> $counts{$a} } keys %counts;

    my @results;
    foreach my $reason (@sorted) {
        my $pct = $total_rejects > 0 ? sprintf("%.1f", ($counts{$reason} / $total_rejects) * 100) : 0;

        # Get top IPs for this reason (sorted by count, limit to top 5)
        my @top_ips;
        if ($ips{$reason}) {
            my @sorted_ips = sort { $ips{$reason}{$b} <=> $ips{$reason}{$a} } keys %{$ips{$reason}};
            @top_ips = splice(@sorted_ips, 0, 5);
        }

        # Get top senders for this reason (sorted by count, limit to top 5)
        my @top_senders;
        if ($senders{$reason}) {
            my @sorted_senders = sort { $senders{$reason}{$b} <=> $senders{$reason}{$a} } keys %{$senders{$reason}};
            @top_senders = splice(@sorted_senders, 0, 5);
        }

        push(@results, {
            'reason' => $reason,
            'count' => $counts{$reason},
            'percentage' => $pct,
            'ips' => \@top_ips,
            'senders' => \@top_senders,
            'ip_counts' => $ips{$reason} || {},
            'sender_counts' => $senders{$reason} || {}
        });
    }

    return @results;
}

=item group_by_hour(\@log_entries)

Group log entries by hour for trending. Returns hashref with hour strings as keys and counts as values.

=cut

sub group_by_hour {
    my ($entries) = @_;

    my %hourly;

    foreach my $entry (@$entries) {
        # Extract hour from timestamp (e.g., "Dec  5 10:23:45" -> "10")
        if ($entry->{'timestamp'} =~ /\d+:\d+:\d+/) {
            my $hour = $entry->{'timestamp'};
            $hour =~ s/^.*\s(\d+):\d+:\d+.*$/$1/;
            $hourly{$hour}++;
        }
    }

    return \%hourly;
}

=head2 Backup and Restore Functions

=item get_backup_dir()

Returns the backup root directory path, creating it if it doesn't exist.

=cut

sub get_backup_dir {
    my $dir = "$module_config_directory/backups";
    if (!-d $dir) {
        make_path($dir, { mode => 0700 });
    }
    return $dir;
}

=item get_managed_files()

Returns an array of arrayrefs [config_key, basename] for all files to back up.

=cut

sub get_managed_files {
    return (
        ['cidr_root_file', 'allowed_brightspeed_root_cidrs'],
        ['cidr_subdomain_file', 'allowed_brightspeed_subdomain_cidrs'],
        ['allow_root_pcre', 'allow_brightspeed_root.pcre'],
        ['block_root_pcre', 'block_brightspeed_root.pcre'],
        ['allow_subdomain_pcre', 'allow_brightspeed_subdomains.pcre'],
        ['sender_relay_map', 'sender_relay_map'],
        ['transport_file', 'transport'],
        ['domain_transport_file', 'domain-transport'],
        ['header_checks_file', 'header_checks'],
        ['sasl_passwd_file', 'sasl_passwd'],
        ['v_domains_file', 'v-domains'],
    );
}

=item create_backup($action, $description)

Create a backup of all managed configuration files.
Returns undef on success, error string on failure.

=cut

sub create_backup {
    my ($action, $description) = @_;

    my $backup_root = get_backup_dir();
    my $timestamp = time();
    my $dir_name = strftime("%Y%m%d-%H%M%S", localtime($timestamp));
    my $backup_dir = "$backup_root/$dir_name";

    if (!make_path($backup_dir, { mode => 0700 })) {
        return "Failed to create backup directory: $backup_dir";
    }

    my @managed = get_managed_files();
    my $file_count = 0;

    foreach my $entry (@managed) {
        my ($config_key, $basename) = @$entry;
        my $src = $config{$config_key};
        if ($src && -f $src) {
            if (copy_source_dest($src, "$backup_dir/$basename")) {
                $file_count++;
            }
        }
    }

    # Write backup.meta
    my $date_str = strftime("%Y-%m-%d %H:%M:%S", localtime($timestamp));
    my $user = $remote_user || 'unknown';
    open(my $fh, '>', "$backup_dir/backup.meta") or return "Failed to write backup metadata: $!";
    print $fh "timestamp=$timestamp\n";
    print $fh "date=$date_str\n";
    print $fh "user=$user\n";
    print $fh "action=$action\n";
    print $fh "description=$description\n";
    print $fh "files_backed_up=$file_count\n";
    close($fh);

    purge_old_backups();

    return undef;
}

=item purge_old_backups()

Delete backup directories older than 14 days.

=cut

sub purge_old_backups {
    my $backup_root = get_backup_dir();
    my $cutoff = time() - (14 * 24 * 60 * 60);

    opendir(my $dh, $backup_root) or return;
    my @dirs = grep { /^\d{8}-\d{6}$/ && -d "$backup_root/$_" } readdir($dh);
    closedir($dh);

    foreach my $dir (@dirs) {
        my $meta_file = "$backup_root/$dir/backup.meta";
        next if (!-f $meta_file);

        open(my $fh, '<', $meta_file) or next;
        my %meta;
        while (<$fh>) {
            chomp;
            if (/^(\w+)=(.*)$/) {
                $meta{$1} = $2;
            }
        }
        close($fh);

        if ($meta{'timestamp'} && $meta{'timestamp'} < $cutoff) {
            rmtree("$backup_root/$dir");
        }
    }
}

=item list_backups()

Returns an array of hashrefs (sorted newest-first) with backup metadata.

=cut

sub list_backups {
    my $backup_root = get_backup_dir();
    my @backups;

    opendir(my $dh, $backup_root) or return @backups;
    my @dirs = grep { /^\d{8}-\d{6}$/ && -d "$backup_root/$_" } readdir($dh);
    closedir($dh);

    foreach my $dir (sort { $b cmp $a } @dirs) {
        my $meta_file = "$backup_root/$dir/backup.meta";
        next if (!-f $meta_file);

        open(my $fh, '<', $meta_file) or next;
        my %meta;
        while (<$fh>) {
            chomp;
            if (/^(\w+)=(.*)$/) {
                $meta{$1} = $2;
            }
        }
        close($fh);

        $meta{'dir_name'} = $dir;
        push(@backups, \%meta);
    }

    return @backups;
}

=item restore_backup($backup_name)

Restore all configuration files from a backup. Creates a pre-restore backup first.
Returns undef on success, error string on failure.

=cut

sub restore_backup {
    my ($backup_name) = @_;

    my $backup_root = get_backup_dir();
    my $backup_dir = "$backup_root/$backup_name";

    if (!-d $backup_dir || !-f "$backup_dir/backup.meta") {
        return "Backup not found: $backup_name";
    }

    # Create pre-restore backup
    my $err = create_backup('pre_restore', "Auto-backup before restoring from $backup_name");
    if ($err) {
        return "Failed to create pre-restore backup: $err";
    }

    # Restore each file
    my @managed = get_managed_files();
    foreach my $entry (@managed) {
        my ($config_key, $basename) = @$entry;
        my $src = "$backup_dir/$basename";
        my $dest = $config{$config_key};
        if (-f $src && $dest) {
            copy_source_dest($src, $dest);
        }
    }

    # Set sasl_passwd permissions
    chmod(0600, $config{'sasl_passwd_file'}) if -f $config{'sasl_passwd_file'};

    # Run postmap on hash files (CIDR/PCRE files are read directly by Postfix)
    foreach my $file_key ('sender_relay_map', 'transport_file', 'sasl_passwd_file') {
        if (-f $config{$file_key}) {
            update_hash_map($config{$file_key});
        }
    }

    # Set sasl_passwd.db permissions
    chmod(0600, $config{'sasl_passwd_file'} . '.db') if -f ($config{'sasl_passwd_file'} . '.db');

    # Reload Postfix
    $err = reload_postfix();
    if ($err) {
        return "Files restored but Postfix reload failed: $err";
    }

    webmin_log('restore', 'backup', $backup_name);
    return undef;
}

=item get_backup_changes($backup_name)

Compute differences between a backup and the current live files.
Returns a hashref with per-file diff information.

=cut

sub get_backup_changes {
    my ($backup_name) = @_;

    my $backup_root = get_backup_dir();
    my $backup_dir = "$backup_root/$backup_name";
    my @managed = get_managed_files();
    my @changes;
    my $has_changes = 0;

    foreach my $entry (@managed) {
        my ($config_key, $basename) = @$entry;
        my $backup_file = "$backup_dir/$basename";
        my $live_file = $config{$config_key};

        my %file_info = (
            'basename' => $basename,
            'config_key' => $config_key,
            'changed' => 0,
            'diff' => '',
            'backup_exists' => (-f $backup_file ? 1 : 0),
            'live_exists' => ($live_file && -f $live_file ? 1 : 0),
        );

        if (-f $backup_file && $live_file && -f $live_file) {
            my $diff_out = backquote_command("diff -u " . quotemeta($backup_file) . " " . quotemeta($live_file) . " 2>&1");
            if ($? != 0 && $diff_out) {
                $file_info{'changed'} = 1;
                $file_info{'diff'} = $diff_out;
                $has_changes = 1;
            }
        } elsif (-f $backup_file && (!$live_file || !-f $live_file)) {
            $file_info{'changed'} = 1;
            $file_info{'diff'} = "File was removed since this backup.";
            $has_changes = 1;
        } elsif (!-f $backup_file && $live_file && -f $live_file) {
            $file_info{'changed'} = 1;
            $file_info{'diff'} = "File was added since this backup.";
            $has_changes = 1;
        }

        push(@changes, \%file_info);
    }

    return {
        'changes' => \@changes,
        'has_changes' => $has_changes,
    };
}

=back

=head1 AUTHOR

Brightspeed Postfix Relay Module

=head1 LICENSE

This module is licensed under the same terms as Webmin.

=cut

1;
