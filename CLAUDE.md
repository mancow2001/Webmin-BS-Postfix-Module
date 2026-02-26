# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Webmin module for managing a Brightspeed Postfix mail relay gateway. It provides a web-based interface for managing sophisticated mail routing, access control, domain onboarding/offboarding, and CIDR-based whitelisting for the brightspeed.com and brightspeedbroadband.net domains.

## Technology Stack

- **Language**: Perl 5.x
- **Framework**: Webmin module architecture
- **Mail Server**: Postfix
- **Access Control**: Webmin ACL system
- **Logging**: Webmin audit logging

## Development Commands

### Building Release Package
```bash
./build-release.sh [version]
```
Builds a Webmin module tarball (`.tar.gz`) for distribution. If version is not specified, it reads from `module.info`.

### Testing Configuration Changes
```bash
# Validate Postfix configuration
postfix check

# Test PCRE patterns
perl test_regex.pl

# Test standalone functions
perl test_standalone.pl

# Update hash databases after config changes (hash maps only)
# Note: CIDR and PCRE files are read directly by Postfix — no postmap needed
postmap hash:/etc/postfix/sender_relay_map
postmap hash:/etc/postfix/transport
postmap hash:/etc/postfix/sasl_passwd
```

## Architecture

### Module Entry Points

The module follows Webmin's CGI-based architecture where each `.cgi` file handles a specific function:

- **index.cgi**: Main dashboard showing status, statistics, and navigation
- **onboard_domain.cgi**: Domain onboarding workflow with preview and confirmation
- **offboard_domain.cgi**: Domain removal workflow
- **cidrs.cgi**: CIDR whitelist management (root and subdomain lists)
- **control.cgi**: Postfix service control (start/stop/reload/check)
- **queue.cgi**: Mail queue management
- **logs.cgi**: Mail log viewer
- **view_config.cgi**: Configuration file viewer

### Core Library (brightspeed-postfix-lib.pl)

The main library contains all shared functions organized into categories:

#### Postfix Management
- `get_postfix_version()`, `get_postfix_status()`: System info
- `start_postfix()`, `stop_postfix()`, `reload_postfix()`: Service control
- `check_postfix_config()`: Configuration validation
- `get_postfix_param($param)`, `set_postfix_param($param, $value)`: Parameter management

#### CIDR Operations
- `read_cidr_file($filename)`: Returns array of hashrefs with keys: `type`, `cidr`, `action`, `comment`
- `write_cidr_file($filename, \@entries)`: Writes CIDR entries
- `validate_cidr($cidr)`: Validates CIDR format
- `update_cidr_hash($filename)`: No-op (CIDR files are read directly by Postfix, like PCRE)

#### PCRE Operations
- `read_pcre_file($filename)`: Returns array of pattern entries
- `write_pcre_file($filename, \@entries)`: Writes PCRE patterns
- PCRE and CIDR files are NOT compiled with postmap (Postfix reads them directly)

#### Hash Map Operations
- `read_hash_map($filename)`: Returns array of key-value mappings
- `write_hash_map($filename, \@entries)`: Writes hash map
- `update_hash_map($filename)`: Runs `postmap hash:filename`

#### Domain Operations
- `onboard_domain_full($fqdn, $username, $password, $host, $port)`: Complete onboarding workflow
- `offboard_domain($fqdn)`: Complete offboarding workflow
- These functions update multiple config files atomically

### Configuration Files Architecture

The module manages a complex set of Postfix configuration files in `/etc/postfix/`:

**CIDR Files** (format: `cidr action #comment`):
- `allowed_brightspeed_root_cidrs`: IPs allowed to send from root domains
- `allowed_brightspeed_subdomain_cidrs`: IPs allowed to send from subdomains

**PCRE Files** (format: `pattern action #comment`):
- `allow_brightspeed_root.pcre`: Patterns for root domain senders
- `block_brightspeed_root.pcre`: Block patterns for root domains
- `allow_brightspeed_subdomains.pcre`: Patterns for subdomain senders

**Hash Map Files** (format: `key value #comment`):
- `sender_relay_map`: Sender-dependent relay routing (e.g., `@subdomain.brightspeed.com [smtp.mailgun.org]:587`)
- `transport`: Domain transport rules (exact match)
- `sasl_passwd`: SASL credentials for relay authentication (format: `[host]:port username:password`)

**Regexp Files**:
- `header_checks`: Header validation rules (From: field validation)
- `domain-transport`: Regexp-based transport rules

### Access Control System

ACL permissions are defined in `acl_security.pl` and `defaultacl`:
- `cidrs`: Manage CIDR whitelists
- `onboard_domain` / `offboard_domain`: Domain onboarding/offboarding
- `control`: Service control
- `queue`: Mail queue management
- `logs`: View logs

Each CGI script checks `$access{'permission_name'}` before allowing operations.

### Two-Tier Domain Architecture

Brightspeed uses a two-tier access control system:

1. **Root Domains**: `brightspeed.com`, `brightspeedbroadband.net`
   - Restricted to specific CIDR ranges
   - Uses `allowed_brightspeed_root_cidrs` and `allow_brightspeed_root.pcre`

2. **Subdomains**: `*.brightspeed.com`, `*.brightspeedbroadband.net`
   - More permissive CIDR ranges
   - Each subdomain must be explicitly onboarded
   - Uses `allowed_brightspeed_subdomain_cidrs` and `allow_brightspeed_subdomains.pcre`

### Domain Onboarding Process

When onboarding a domain (e.g., `myapp.brightspeed.com`):

1. Adds to `allow_brightspeed_subdomains.pcre`: Pattern to allow sender
2. Adds to `header_checks`: From: validation rule (before final REJECT)
3. Adds to `sender_relay_map`: Routes to specified relay host
4. Optionally adds to `sasl_passwd`: SASL credentials for relay
5. Runs `postmap` on all hash files
6. Logs action to Webmin audit log

### Domain Offboarding Process

When offboarding a domain:

1. Removes from `allow_brightspeed_subdomains.pcre`
2. Removes from `header_checks` (the domain-specific IGNORE rule)
3. Removes from `sender_relay_map`
4. Removes from `sasl_passwd` (if present)
5. Runs `postmap` on all hash files
6. Logs action to Webmin audit log

## Important Patterns

### Error Handling
Functions return `undef` on success and an error message string on failure:
```perl
my $err = &some_operation();
if ($err) {
    print &ui_alert_box(&text('error_msg', $err), 'danger');
}
```

### File Structure Consistency
CIDR, PCRE, and hash map files all use a consistent entry structure:
```perl
{
    'type' => 'cidr'|'mapping'|'pattern'|'comment',
    'cidr' => '10.0.0.0/8',  # or 'key', 'pattern' for other types
    'action' => 'OK',        # or 'value' for hash maps
    'comment' => 'Description'
}
```

### Atomic Updates
When updating configuration files:
1. Read existing file into array
2. Modify array in memory
3. Write entire file
4. Run `postmap` if needed
5. Log action

Never modify files line-by-line to avoid inconsistencies.

### Header Checks Order Matters
The `header_checks` file has a specific order:
1. Domain-specific IGNORE rules (one per onboarded domain)
2. Final catch-all REJECT rule

New domain rules must be inserted BEFORE the final REJECT.

## Postfix Integration

### Restriction Classes
Postfix uses custom restriction classes defined in `main.cf`:
```
smtpd_restriction_classes = allow_brightspeed_root, allow_brightspeed_subdomains
allow_brightspeed_root = check_client_access cidr:allowed_brightspeed_root_cidrs, reject
allow_brightspeed_subdomains = check_client_access cidr:allowed_brightspeed_subdomain_cidrs, reject
```

### Relay Restrictions Flow
Mail is evaluated in this order:
1. Check sender against `allow_brightspeed_root.pcre` (root domain senders)
2. Check sender against `block_brightspeed_root.pcre` (block unauthorized root)
3. Check sender against `allow_brightspeed_subdomains.pcre` (subdomain senders)
4. Check SASL authentication
5. Check relay domains
6. Final reject

### Sender-Dependent Routing
Postfix uses `sender_dependent_default_transport_maps` to route based on sender:
- Each onboarded subdomain gets an entry like `@subdomain.brightspeed.com [smtp.mailgun.org]:587`
- Default relay is Mailgun for most domains
- Some domains route directly to internal MYNAH services

## File Permissions

Critical file permissions:
- Configuration files (`.pcre`, CIDR files): 644
- SASL password file: 600 (contains credentials)
- CGI scripts: 755 (executable)
- Perl libraries: 755 (executable)

## Logging

All administrative actions are logged via `webmin_log()`:
```perl
webmin_log($action, $type, $object, \%params);
```
Example: `webmin_log('onboard', 'domain', $fqdn);`

## Mail Flow Dashboard

### Overview

The module includes a comprehensive operational dashboard (`dashboard.cgi`) for monitoring mail flow across multiple Postfix servers. It provides real-time metrics, historical trending, and detailed analytics.

### Multi-Server Architecture

The dashboard supports aggregating logs from up to 6 servers:
- 1 local server (where Webmin is running)
- Up to 5 remote servers accessed via NFS mounts

**Configuration**:
- Remote servers are configured via Module Config (Webmin → Configuration → Modules → Brightspeed Postfix Relay)
- Each remote server requires: name, NFS log file path, and enabled flag
- Server availability is checked before reading logs
- Unavailable servers display warnings but don't block the dashboard

### Dashboard Features

**Tabbed Interface**:
- "All Servers" tab: Aggregated view combining all available servers
- Individual server tabs: Per-server metrics and analytics

**Time Range Selection**:
- Last 1 Hour (10,000 lines per server)
- Last 6 Hours (30,000 lines per server)
- Last 24 Hours (50,000 lines per server)
- Last 7 Days (100,000 lines per server)

**Metrics Displayed**:
1. **Summary Statistics**: Total, sent, rejected, deferred, bounced (with percentages)
2. **Hourly Trend Chart**: SVG line graph showing message volume by hour
3. **Top 10 Senders**: Most active sender email addresses with message counts
4. **Top 10 Recipients**: Most active recipient email addresses with message counts
5. **Top 10 Domains**: Most active sender domains with message counts
6. **Rejection Analysis**: Breakdown of rejection reasons with counts, percentages, top 5 client IPs, and top 5 senders per reason

### Log Parsing Architecture

**Core Functions** (in `brightspeed-postfix-lib.pl`):

#### Server Management
- `get_configured_servers()`: Returns array of configured servers (local + remote)
- `check_server_availability($path)`: Tests if log file is accessible

#### Log Parsing
- `parse_postfix_log_line($line)`: Extracts structured data from syslog format
  - Returns hashref with: timestamp, hostname, process, pid, queue_id, status, from, to, relay, delay, dsn, reject_reason, client_ip
  - Handles: sent, deferred, bounced, reject, NOQUEUE entries
  - Extracts client IP from rejection messages (format: `from unknown[10.152.7.111]:`)

- `get_mail_logs($path, $start_time, $end_time, $max_lines)`: Read and parse single log file
  - Uses `tail -n` for efficiency (reads most recent entries)
  - Returns array of parsed log entries

- `get_mail_logs_multi(\@servers, $start_time, $end_time, $max_lines)`: Multi-server aggregation
  - Reads logs from all configured servers
  - Tags each entry with source server name
  - Returns hashref with server availability status and entries

#### Analytics
- `aggregate_mail_stats(\@entries)`: Calculate sent/rejected/deferred/bounced counts and percentages
- `get_top_senders(\@entries, $limit)`: Top N senders by volume with counts
- `get_top_recipients(\@entries, $limit)`: Top N recipients by volume with counts
- `get_top_domains(\@entries, $limit)`: Top N sender domains by volume with counts
- `get_rejection_reasons(\@entries)`: Group rejections by reason with counts, percentages, top 5 IPs, and top 5 senders per reason
- `group_by_hour(\@entries)`: Bucket entries by hour for trending

### Postfix Log Format

The parser handles standard Postfix syslog format:
```
Month Day HH:MM:SS hostname postfix/process[pid]: queue_id: message details
```

**Example Entries**:
```
Dec  5 10:23:45 hostname postfix/smtp[12345]: AB123456789: to=<user@example.com>, relay=mail.example.com[1.2.3.4]:25, delay=0.52, status=sent
Dec  5 10:24:12 hostname postfix/smtpd[12346]: NOQUEUE: reject: RCPT from unknown[1.2.3.4]: 554 5.7.1 Relay access denied
```

### Server Configuration Page

The `servers.cgi` page provides:
- List of all configured servers (local + remote)
- Real-time availability status for each server
- "Test Connection" functionality
  - Checks file accessibility
  - Displays recent log entries on success
  - Shows troubleshooting tips on failure
- Summary statistics (total servers, available, unavailable)

### Performance Considerations

- **Line Limits**: Configurable max lines per server prevents parsing large files
- **Tail Reading**: Uses `tail -n` instead of reading entire log files
- **NFS Timeout Handling**: Unavailable servers don't block dashboard rendering
- **No Database**: All metrics calculated in real-time from log files
- **Warning Thresholds**: Large time ranges show warnings about performance

### ACL Permissions

- `dashboard`: Access to mail flow dashboard
- `servers`: View and test server configuration

Both default to enabled in `defaultacl`.

## Sample Configuration Files

The `postfix_config/` directory contains example configuration files showing the expected format and structure for each file type.
