#!/usr/bin/perl
#
# Manage email campaigns, or at least track the bounce rate and open rate
#
# TODO: 
#   - Add support for multiple campaigns (delineated by csv file name/maillist name and date?)
#   - Add support for uploading template and csv files from here
#   - Add support for previewing message
#   - Add support for nsse_survey stuff

use JSON;
use CGI;
use IO::Socket::INET;
use DB_File;

@servers = ("mailgw3.sfu.ca","mailgw4.sfu.ca");
$TRACKERDB = "/data/tracker.db";

$pagedir = "pages";

foreach (@servers) { $server_h{$_} = 1;}


$q = CGI->new;

@params = $q->param;

main_page() if (!scalar(@params));

$cmd = $q->param("cmd");
$pagename = $q->param("page");

logger("starting $cmd");

if ($cmd eq "getqueue")
{
	get_stats();
}

main_page();
exit 0;

sub main_page()
{
	load_page("campaign.html");
}

sub get_stats()
{
    # Fetch the bounce tracking numbers and return in a pretty table
    my $json = JSON->new->allow_nonref;
    my $deliveries_json = process_q_cmd($servers[0],"get bouncetracker");
    $count = 0;
    foreach my $server (@servers)
    {
        $bounces_json[$count] = process_q_cmd($server,"get bounces");
        $count++;
    }
    $deliveries = $json->decode($deliveries_json);
    foreach $k (keys %$deliveries)
    {
        ($campaign,$junk) = split(/:/,$k);
        $campaigns{$campaign} = [0,0,0] if (!defined($campaigns{$campaign}));
        ${$campaigns{$campaign}}[0]++;
    }
    $total_bounces = 0;
    foreach my $i (0..$count-1)
    {
        my $bounces = $json->decode($bounces_json[$i]);
        foreach my $k (keys %$bounces)
        {
            foreach my $ck (keys %campaigns)
            {
                ${$campaigns{$campaign}}[1]++ if (defined($deliveries->{"$ck:$k"}));
            }
        }
    }
    tie %tracked,"DB_File",$TRACKERDB,O_RDONLY,0644,$DB_HASH;

    $total_opened=0;
    foreach my $k (keys %tracked)
    {
        foreach my $ck (keys %campaigns)
        {
            ${$campaigns{$campaign}}[2]++ if (defined($deliveries->{"$ck:$k"}));
        }
    }

	print "Content-type: text/html\n\n";

    print "<table class=\"messageTable\"\n>";
    print "<tr id=\"messageHeading\" class=\"messageHeading\"><td>Campaign</td><td>Total Sent</td><td>Bounces</td><td>Confirmed Viewed</td></tr>\n";
    foreach my $k (keys %campaigns)
    {
        print "<tr class=\"messageList\">\n";
        print "<td>$k</td><td>",${$campaigns{$k}}[0],"</td><td>",${$campaigns{$k}}[1],"</td><td>",${$campaigns{$k}}[2],"</td></tr>\n";
    }
    
    exit 0;
}

sub load_page()
{
	print "Content-type: text/html\n\n";
	my ($page,$content) = @_;
	my $html;
	my $file = "$pagedir/$page";
	if (-f $file)
	{
		open(IN,$file) || error_page();
		$html = join("",<IN>);
		close (IN);
	}
	$html =~ s/##content##/$content/;
	print $html;
	exit 0;
}

sub process_q_cmd()
{
	my ($host,$cmd) = @_;
	my $sock = IO::Socket::INET->new("$host:6090");
	$junk = <$sock>;	# wait for "ok" prompt
	print $sock "$cmd\n";
	@res = <$sock>;
	close $sock;

	return join("",@res);

}

sub logger()
{
	open(LOG,">>/tmp/campaigncgi.log") or return;
	print LOG scalar(localtime()),": ",@_,"\n";
	close LOG;
}
