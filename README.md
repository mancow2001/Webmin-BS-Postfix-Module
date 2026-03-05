# Brightspeed Postfix Relay - Webmin Module

A comprehensive Webmin module for managing a specialized Postfix mail relay gateway for Brightspeed domains with sophisticated access control, sender-dependent routing, and integration with Mailgun and internal services.

## Features

### Core Functionality
- **CIDR Whitelist Management**: Manage IP address whitelists for root domains and subdomains separately
- **Subdomain Onboarding**: One-click onboarding of new subdomains across all configuration files
- **Sender-Dependent Routing**: Configure different relay hosts based on sender domain
- **Transport Rules**: Manage both hash-based and regex-based domain transport routing
- **Service Control**: Start, stop, reload, and check Postfix configuration
- **Mail Queue Management**: View and manage queued messages
- **Virtual Aliases**: Configure virtual domain alias mappings
- **Header Validation**: Manage header check rules for From: validation
- **SASL Authentication**: Securely manage SASL credentials for relay authentication
- **Log Viewer**: Real-time viewing of mail logs with filtering

### Access Control
- Granular per-user permissions for each module function
- Secure credential storage with restricted file permissions
- Full audit logging of all administrative actions

### Specialized for Brightspeed
- Dual domain support: brightspeed.com and brightspeedbroadband.net
- Two-tier CIDR whitelisting (root domain vs subdomains)
- Restriction classes for sophisticated access control
- Integration with Mailgun for default relay
- Support for direct routing to internal MYNAH services
- HAProxy proxy protocol support

## Installation

### Prerequisites
- Webmin installed and running
- Postfix mail server installed
- Root or sudo access
- Perl 5.x

### Installation Steps

1. **Copy Module Files**
   ```bash
   cd /usr/share/webmin
   git clone https://github.com/yourusername/Webmin-BS-Postfix-Module brightspeed-postfix
   ```

   Or download and extract:
   ```bash
   cd /usr/share/webmin
   tar xzf brightspeed-postfix.tar.gz
   ```

2. **Set Permissions**
   ```bash
   cd /usr/share/webmin/brightspeed-postfix
   chmod +x *.cgi *.pl
   chmod 644 config config.info defaultacl module.info
   chmod 644 lang/en
   ```

3. **Install in Webmin**
   - Log in to Webmin
   - Go to **Webmin** → **Webmin Configuration** → **Webmin Modules**
   - Click **Install Module**
   - Select **From local file**
   - Choose the module directory or upload a tar.gz
   - Click **Install Module**

4. **Configure Module**
   - Go to **Webmin** → **Webmin Configuration** → **Webmin Modules**
   - Find **Brightspeed Postfix Relay**
   - Click **Module Config**
   - Verify paths to Postfix configuration files
   - Save configuration

5. **Create Module Icon** (Optional)
   - Create a 48x48 pixel GIF icon
   - Save as `/usr/share/webmin/brightspeed-postfix/images/icon.gif`
   - Refresh Webmin

## Configuration

### Initial Setup

After installation, configure the module for your environment:

1. **Verify Postfix Paths**
   - Go to Module Configuration
   - Verify paths to:
     - Postfix config directory (default: /etc/postfix)
     - postfix, postmap, postconf commands
     - Configuration files (main.cf, master.cf, etc.)

2. **Import Existing Configuration**
   - If you have existing configuration files in `postfix_config/`, copy them to `/etc/postfix`:
     ```bash
     cp postfix_config/* /etc/postfix/
     ```

3. **Set File Permissions**
   ```bash
   chmod 644 /etc/postfix/allowed_brightspeed_*
   chmod 644 /etc/postfix/*.pcre
   chmod 644 /etc/postfix/sender_relay_map
   chmod 644 /etc/postfix/transport
   chmod 644 /etc/postfix/domain-transport
   chmod 644 /etc/postfix/header_checks
   chmod 600 /etc/postfix/sasl_passwd
   ```

4. **Generate Hash Databases**
   ```bash
   cd /etc/postfix
   postmap hash:sender_relay_map
   postmap hash:transport
   postmap hash:v-domains
   postmap hash:sasl_passwd
   ```
   > **Note**: PCRE files are read directly by Postfix as text — do NOT run `postmap` on them. CIDR and `hash:` type maps are updated via `postmap` automatically by the module.

## Usage

### Dashboard

The main dashboard displays:
- Postfix service status
- Statistics (CIDR entries, onboarded subdomains, queue size)
- Quick action buttons
- Navigation links to all features

### CIDR Whitelist Management

**Path**: CIDR Whitelists

Manage IP address whitelists for controlling which hosts can send mail:

- **Root Domain List**: IPs allowed to send from @brightspeed.com and @brightspeedbroadband.net
- **Subdomain List**: IPs allowed to send from Brightspeed subdomains

**Add a CIDR Range**:
1. Enter the CIDR range (e.g., 10.152.0.0/24)
2. Add a comment describing the range
3. Select action (OK or reject)
4. Click Save

The module automatically runs `postmap` on the updated CIDR file and reloads Postfix to apply changes.

### Subdomain Onboarding

**Path**: Subdomain Onboarding

Onboard a new subdomain with one click:

1. Enter the subdomain (e.g., myapp.brightspeed.com)
2. Specify relay host (default: [smtp.mailgun.org]:587)
3. Click "Onboard Subdomain"

This automatically:
- Adds the subdomain to allow_brightspeed_subdomains.pcre
- Adds From: validation to header_checks
- Adds sender relay mapping
- Updates all hash databases

**Remove a Subdomain**:
- Click "Remove" next to the subdomain in the list
- Confirms removal from all configuration files

### Sender Relay Configuration

**Path**: Sender Relay Configuration

Configure sender-dependent relay routing:

1. Enter sender domain (e.g., @myapp.brightspeed.com)
2. Enter relay host (e.g., [smtp.mailgun.org]:587)
3. Click Save

Default relay for all domains: [smtp.mailgun.org]:587

### Domain Transport Rules

**Path**: Domain Transport Rules

Configure domain-specific transport routing:

**Hash Transport Map** (exact domain matching):
- Add domain → transport mappings
- Example: `example.com` → `smtp:[192.168.1.100]:25`

**Regexp Transport Map** (pattern matching):
- Add regex patterns → transport mappings
- Example: `/^.*@mynah\.brightspeed\.com$/` → `smtp:[10.152.0.10]:25`

Special transports:
- `discard:silently` - Blackhole mail
- `smtp:[host]:port` - Direct SMTP
- `relay:[host]:port` - Relay through host

### Service Control

**Path**: Service Control

Control the Postfix service:
- **Start**: Start Postfix
- **Stop**: Stop Postfix
- **Reload**: Reload configuration (graceful, no downtime)
- **Check**: Validate configuration without restarting

Always run "Check" before "Reload" to catch configuration errors.

### Mail Queue

**Path**: Mail Queue

View and manage queued messages:
- View all queued messages with ID, size, sender
- Delete individual messages
- Flush entire queue (retry all messages)

### Virtual Domain Aliases

**Path**: Virtual Domain Aliases

Configure virtual alias mappings:
- Map source addresses to destination addresses
- Example: `user@example.com` → `realuser@internal.local`

### Header Validation

**Path**: Header Validation Rules

Manage header check rules:
- Add patterns to match From: headers
- Choose action: IGNORE (allow) or REJECT
- Final catch-all rejects any non-onboarded domains

### SASL Authentication

**Path**: SASL Authentication

Manage SASL credentials for outbound relay:
1. Enter relay host (e.g., [smtp.mailgun.org]:587)
2. Enter username
3. Enter password
4. Click Save

Credentials are stored with secure permissions (600) and automatically hashed.

### Log Viewer

**Path**: Mail Log Viewer

View Postfix mail logs:
- Shows last 100 log lines
- Filter by keyword
- Color-coded for errors, warnings, accepts, rejects
- Real-time refresh

## Architecture

### File Structure
```
brightspeed-postfix/
├── module.info              # Module metadata
├── config                   # Default configuration
├── config.info              # Configuration UI definition
├── defaultacl               # Default permissions
├── brightspeed-postfix-lib.pl  # Core library functions
├── install_check.pl         # Installation verification
├── acl_security.pl          # Access control
├── log_parser.pl            # Action log parser
├── index.cgi                # Main dashboard
├── cidrs.cgi                # CIDR management
├── subdomains.cgi           # Subdomain onboarding
├── sender_relay.cgi         # Sender relay configuration
├── domain_transport.cgi     # Transport rules
├── control.cgi              # Service control
├── queue.cgi                # Mail queue management
├── virtual.cgi              # Virtual aliases
├── headers.cgi              # Header validation
├── sasl.cgi                 # SASL credentials
├── logs.cgi                 # Log viewer
├── images/
│   └── icon.gif             # Module icon
└── lang/
    └── en                   # English language strings
```

### Core Library Functions

The `brightspeed-postfix-lib.pl` library provides:

- **Postfix Management**: get_postfix_version(), reload_postfix(), start_postfix(), stop_postfix()
- **CIDR Operations**: read_cidr_file(), write_cidr_file(), validate_cidr(), update_cidr_hash()
- **PCRE Operations**: read_pcre_file(), write_pcre_file()
- **Hash Map Operations**: read_hash_map(), write_hash_map(), update_hash_map()
- **Subdomain Operations**: onboard_subdomain(), remove_subdomain()
- **Queue Operations**: get_mail_queue(), flush_mail_queue(), delete_queue_message()
- **Validation**: validate_domain(), validate_email(), validate_relay_host()

## Postfix Configuration

### Key Configuration Parameters

The module manages these Postfix parameters in main.cf:

```ini
# Network and host settings
myhostname = PE1ENCTLSMTPR.ENCRD.CO
mydomain = mail.brightspeed.com
myorigin = /etc/mailname
inet_interfaces = all
inet_protocols = ipv4

# Restriction classes
smtpd_restriction_classes = allow_brightspeed_root, allow_brightspeed_subdomains
allow_brightspeed_root = check_client_access cidr:/etc/postfix/allowed_brightspeed_root_cidrs, reject
allow_brightspeed_subdomains = check_client_access cidr:/etc/postfix/allowed_brightspeed_subdomain_cidrs, reject

# Relay restrictions
smtpd_relay_restrictions =
    check_sender_access pcre:/etc/postfix/allow_brightspeed_root.pcre,
    check_sender_access pcre:/etc/postfix/block_brightspeed_root.pcre,
    check_sender_access pcre:/etc/postfix/allow_brightspeed_subdomains.pcre,
    permit_sasl_authenticated,
    reject_unauth_destination,
    check_relay_domains,
    reject

# Transport and routing
transport_maps = hash:/etc/postfix/transport,regexp:/etc/postfix/domain-transport
sender_dependent_default_transport_maps = hash:/etc/postfix/sender_relay_map
header_checks = regexp:/etc/postfix/header_checks

# SASL authentication
smtp_sender_dependent_authentication = yes
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd

# TLS
smtpd_tls_cert_file = /etc/pki/tls/certs/pfxtransport-encrd-co-cert.pem
smtpd_tls_key_file = /etc/pki/tls/private/pfxtransport-encrd-co.key
```

### Configuration Files

| File | Purpose | Format |
|------|---------|--------|
| allowed_brightspeed_root_cidrs | Root domain CIDR whitelist | CIDR |
| allowed_brightspeed_subdomain_cidrs | Subdomain CIDR whitelist | CIDR |
| allow_brightspeed_root.pcre | Root domain sender patterns | PCRE |
| block_brightspeed_root.pcre | Block unauthorized root domain | PCRE |
| allow_brightspeed_subdomains.pcre | Subdomain sender patterns | PCRE |
| sender_relay_map | Sender-dependent routing | Hash |
| transport | Domain transport rules | Hash |
| domain-transport | Regexp transport rules | Regexp |
| header_checks | Header validation rules | Regexp |
| v-domains | Virtual domain aliases | Hash |
| sasl_passwd | SASL credentials | Hash |

## Security Considerations

### File Permissions
- Configuration files: 644 (readable by all, writable by root)
- SASL password files: 600 (readable/writable by root only)
- CGI scripts: 755 (executable)
- Perl libraries: 755 (executable)

### Access Control
- Use Webmin ACLs to restrict access by user
- Grant minimum necessary permissions
- Audit log tracks all administrative actions

### Best Practices
- Always run "Check" before "Reload"
- Test new CIDR ranges in a development environment first
- Keep SASL credentials secure and rotate regularly
- Monitor logs for unauthorized access attempts
- Back up configuration files before making changes

## Troubleshooting

### Postfix Not Found
- Ensure Postfix is installed: `which postfix`
- Check module configuration for correct paths
- Run `install_check.pl` to verify installation

### postmap Errors
- Verify file permissions on configuration files
- Check syntax of configuration files
- Run `postfix check` to identify configuration errors

### Mail Not Relaying
- Verify sender is in CIDR whitelist
- Check that subdomain is onboarded
- Review header_checks for From: validation
- Check mail logs for rejection reason

### Configuration Not Applied
- Run "Reload" after making changes
- Some changes (like master.cf) require a full restart
- Check logs for errors during reload

### Permission Denied
- Verify Webmin user has necessary ACL permissions
- Check file permissions on Postfix configuration files
- Ensure Webmin runs as root or with sudo access

## Development

### Adding New Features

To add a new CGI page:

1. Create the CGI script in the module directory
2. Make it executable: `chmod +x newpage.cgi`
3. Add language strings to `lang/en`
4. Add ACL option to `acl_security.pl` and `defaultacl`
5. Add navigation link in `index.cgi`
6. Add action parsing to `log_parser.pl`

### Testing

Test the module thoroughly:

1. **Installation Test**: Verify module installs without errors
2. **Permission Test**: Test with restricted user accounts
3. **CIDR Test**: Add/remove CIDR ranges and verify postmap runs
4. **Subdomain Test**: Onboard and remove subdomains
5. **Transport Test**: Configure and test transport rules
6. **Relay Test**: Send test emails through the relay
7. **Log Test**: Verify actions appear in Webmin action log

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/yourusername/Webmin-BS-Postfix-Module/issues
- Documentation: This README
- Webmin Forums: https://forum.webmin.com/

## License

This module is provided as-is for managing Brightspeed Postfix relay gateways.

## Changelog

### Version 1.2
- CIDR whitelist saves now run `postmap cidr:` on the updated file before reloading Postfix
- `update_cidr_hash()` is no longer a no-op; it now runs `postmap cidr:$filename` to update the corresponding `.db` file
- Offboard domain process confirmed to run `postmap` on hash files and reload Postfix, matching the onboard workflow

### Version 1.1
- All configuration changes now automatically reload Postfix so changes take effect immediately
- Removed incorrect `postmap` calls on CIDR files (CIDR/PCRE files are read directly by Postfix)
- Removed inline comments from sasl_passwd entries to prevent parsing issues
- Fixed cidrs.cgi, sender_relay.cgi, and domain_transport.cgi to call `postfix reload` after saving

### Version 1.0 (Initial Release)
- CIDR whitelist management (root and subdomain)
- Subdomain onboarding with one-click configuration
- Sender-dependent relay routing
- Domain transport rules (hash and regexp)
- Service control (start/stop/reload/check)
- Mail queue management
- Virtual domain aliases
- Header validation rules
- SASL authentication management
- Real-time log viewer
- Full ACL support
- Comprehensive audit logging

## Credits

Developed for managing Brightspeed mail relay gateways with specialized access control and routing requirements.
