#!/usr/bin/perl

use JSON;
use CGI;
use IO::Socket::INET;

@servers = ("rm-rstar1.tier2.sfu.ca","rm-rstar2.tier2.sfu.ca","mailgw1.tier2.sfu.ca","mailgw2.tier2.sfu.ca","pobox1.tier2.sfu.ca","pobox2.tier2.sfu.ca","mailgw.alumni.sfu.ca");
@mailfromds = ("antibody1.tier2.sfu.ca","antibody2.tier2.sfu.ca");

$pagedir = "pages";



foreach (@servers) { $server_h{$_} = 1;}


$q = CGI->new;

@params = $q->param;

main_page() if (!scalar(@params));

$cmd = $q->param("cmd");
$pagename = $q->param("page");


if ($cmd eq "getqueue")
{
	get_stats();
}


# If we got here, unknown command, just reload the main page

main_page();


sub main_page()
{
	load_page("dashboard.html");
}

# Get the quarantine queue from each mail server as a json blob and
# return as HTML (by default)
sub get_stats()
{
	my ($q_json,$total,$limit,$start,$content);

	print "Content-type: text/html\n\n";

	my $json = JSON->new->allow_nonref;
	my $jsonstr = process_q_cmd("mailgw1.tier2.sfu.ca","sendexchange getqueue");
	$q_json = $json->decode($jsonstr);
	# Exchange returns an array of hashes, one per queue
	$total = 0;
	$content = "<table class=\"messageTable\">\n";

	foreach $ex_q (@$q_json)
	{
		$msgs = $ex_q->{MessageCount};
		if ($msgs)
		{
			$total += $msgs;
			$content .= "<tr class=\"messageServer\"><td style=\"text-align: center;\">" . $ex_q->{Identity} . "</td><td style=\"text-align: center;\">$msgs</td></tr>\n";			
		}
	}

	$content .= "</table>\n";

	$content .= "<div>Total: $total</div>\n";

	print $content;

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

sub error_page()
{
	print "Content-type: text/html\n\n";
	print <<EOF;
<HEAD>
 <Title>Something went wrong</Title>
</HEAD>
<Body>
 An error occurred: $error $@
</BODY>
/
EOF
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
