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
    $total_delivered = scalar(keys(%$deliveries));
    $total_bounces = 0;
    foreach my $i (0..$count-1)
    {
        my $bounces = $json->decode($bounces_json[$i]);
        foreach my $k (keys %$bounces)
        {
            $total_bounces++ if (defined($deliveries->{$bounces->{$k}}));
        }
    }
    tie %tracked,"DB_File",$TRACKERDB,O_RDONLY,0644,$DB_HASH;
    $total_opened = scalar(keys %tracked);

    print "Total delivered: $total_delivered<br>\n";
    print "<a href=\"#\" class=\"viewbounces\">Total bounces: $total_bounces</a><br>\n";
    print "Total viewed: $total_opened<br>\n";
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
