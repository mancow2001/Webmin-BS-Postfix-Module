#!/usr/bin/perl
# acl_security.pl
# Access control functions for Brightspeed Postfix Relay module

require 'brightspeed-postfix-lib.pl';
&ReadParse();

=head1 NAME

acl_security.pl - Access control for Brightspeed Postfix Relay module

=head1 FUNCTIONS

=over 4

=item acl_security_form(\%acl)

Display ACL options form for module

=cut

sub acl_security_form {
    my ($acl) = @_;

    print &ui_table_row($text{'acl_cidrs'},
        &ui_radio("cidrs", int($acl->{'cidrs'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_subdomains'},
        &ui_radio("subdomains", int($acl->{'subdomains'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_sender_relay'},
        &ui_radio("sender_relay", int($acl->{'sender_relay'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_transport'},
        &ui_radio("transport", int($acl->{'transport'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_headers'},
        &ui_radio("headers", int($acl->{'headers'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_virtual'},
        &ui_radio("virtual", int($acl->{'virtual'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_sasl'},
        &ui_radio("sasl", int($acl->{'sasl'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_control'},
        &ui_radio("control", int($acl->{'control'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_queue'},
        &ui_radio("queue", int($acl->{'queue'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_logs'},
        &ui_radio("logs", int($acl->{'logs'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_dashboard'},
        &ui_radio("dashboard", int($acl->{'dashboard'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_servers'},
        &ui_radio("servers", int($acl->{'servers'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_onboard_domain'},
        &ui_radio("onboard_domain", int($acl->{'onboard_domain'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_offboard_domain'},
        &ui_radio("offboard_domain", int($acl->{'offboard_domain'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));

    print &ui_table_row($text{'acl_backups'},
        &ui_radio("backups", int($acl->{'backups'}),
            [ [ 1, $text{'yes'} ], [ 0, $text{'no'} ] ]));
}

=item acl_security_save(\%acl, \%in)

Save ACL options from form

=cut

sub acl_security_save {
    my ($acl, $in) = @_;

    $acl->{'cidrs'} = $in->{'cidrs'};
    $acl->{'subdomains'} = $in->{'subdomains'};
    $acl->{'sender_relay'} = $in->{'sender_relay'};
    $acl->{'transport'} = $in->{'transport'};
    $acl->{'headers'} = $in->{'headers'};
    $acl->{'virtual'} = $in->{'virtual'};
    $acl->{'sasl'} = $in->{'sasl'};
    $acl->{'control'} = $in->{'control'};
    $acl->{'queue'} = $in->{'queue'};
    $acl->{'logs'} = $in->{'logs'};
    $acl->{'dashboard'} = $in->{'dashboard'};
    $acl->{'servers'} = $in->{'servers'};
    $acl->{'onboard_domain'} = $in->{'onboard_domain'};
    $acl->{'offboard_domain'} = $in->{'offboard_domain'};
    $acl->{'backups'} = $in->{'backups'};
}

=back

=cut

1;
