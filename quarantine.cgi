#!/usr/bin/perl

use JSON;
use CGI;
use IO::Socket::INET;
use FindBin;
use lib "$FindBin::Bin";
use Rest;

@servers = ("mailgw1.tier2.sfu.ca","mailgw2.tier2.sfu.ca","mailgw3.sfu.ca","mailgw4.sfu.ca","pobox1.sfu.ca","pobox2.sfu.ca","mailgw1.alumni.sfu.ca","mailgw2.alumni.sfu.ca");
@mailfromds = ("antibody1.tier2.sfu.ca","antibody2.tier2.sfu.ca","lcp-antibody-p1.dc.sfu.ca","lcp-antibody-p2.dc.sfu.ca");

$pagedir = "pages";



foreach (@servers) { $server_h{$_} = 1;}


$q = CGI->new;

@params = $q->param;

main_page() if (!scalar(@params));

$cmd = $q->param("cmd");
$pagename = $q->param("page");

log("starting $cmd");

if ($cmd eq "getqueue")
{
	get_queue();
}
elsif ($cmd eq "view")
{
	viewmsg($q->param("msgid"));		
}
elsif ($cmd =~ /^[rd]_sel/)
{
	release_or_del_msgs($cmd);
}
elsif ($cmd =~ /^ratelimit_add_([wb])/)
{
	ratelimit_quickadd($1);
}

# TODO: We should be able to pass a status message to the page that displays briefly after the page loads


if ($pagename eq "ratelimit")
{
	load_page("ratelimit.html")
}
elsif ($pagename eq "ratelimit_b")
{
	load_page("ratelimit_b.html")
}
elsif ($pagename eq "ratelimit_w")
{
	load_page("ratelimit_w.html")
}

# If we got here, unknown command, just reload the main page

main_page();


sub main_page()
{
	load_page("main.html");
}

# Get the quarantine queue from each mail server as a json blob and
# return as HTML (by default)
sub get_queue()
{
	my ($q_json,$total,$limit,$start,$content);
	$limit = 0;
	$limit = $q->param("limit") if ($q->param("limit"));
	$start = $q->param("start") if ($q->param("start"));
	my @today = localtime(time());

	my $unique = defined($q->param('uniqueusers'));
	my %seenusers;

	print "Content-type: text/html\n\n";

	$recipColumn = ($unique) ? "Messages" : "Recipients";

	my $heading = "<tr id=\"messageHeading\" class=\"messageHeading\"><td>√</td><td>Envelope Sender</td><td>X-Auth-Sender</td><td>Host</td><td>Subject</td><td>Date</td><td>$recipColumn</td></tr>\n";
	# If starting from the beginning, add the header to the result
	if (!$start)
	{
		$content = "<table class=\"messageTable\">\n";
	}
	my $json = JSON->new->allow_nonref;
	foreach $server (@servers)
	{
		log("getqueue processing $server");
		my $jsonstr = process_q_cmd($server,"queuejson");
		$q_json = $json->decode($jsonstr);
		if ($q_json->{total} > 0)
		{
			$content .= "<tr class=\"messageServer\"><td colspan=\"7\" style=\"text-align: center;\">Host: $server</td></tr>\n$heading";
			foreach $msg (@{$q_json->{messages}})
			{
				$total++;
				next if ($start > $total);
				my $authuser = $msg->{authuser};
				$unclickable = "clickable"; 
				$content .= "<!-- $authuser -->\n";
				if (!defined($authuser) || $authuser eq "")
				{
					if (defined($cached{$msg->{sender}}))
					{
						$object = $cached{$msg->{sender}};
					}
					else
					{
						$object = amaint_type($msg->{sender});
						$cached{$msg->{sender}} = $object;
					}

					if (!defined($object->{type}) || $object->{type} eq "unknown")
					{
						$authuser = "[<unknown>]";
						$unclickable = "unclickable";
					}
					elsif ($object->{type} eq "maillist")
					{
						$authuser = "[<maillist>]";
						$unclickable = "unclickable";
					}
					else
					{
						$authuser = $object->{username} . "\@sfu.ca";
						if ($authuser ne $msg->{sender})
						{
							$unclickable = "unclickable";
							$authuser = "[$authuser]";
						}
					}					
				}

				$seenusers{$authuser}++;
				next if ($unique && $seenusers{$authuser} > 1);

				# Calculate date the msg was originally sent
				my @msgtime = localtime($msg->{ctime});
				$date = sprintf("%02d:%02d",$msgtime[2],$msgtime[1]);			
				if ($msgtime[7] == $today[7] - 1)
				{
					$date .= " Yesterday";
				} elsif ($msgtime[7] != $today[7])
				{
					$date = sprintf("%s %d/%02d",$date,$msgtime[4],$msgtime[3]);
				}
					
				# Build the HTMl table row for this msg
				$recipValue = ($unique) ? "###$authuser###" : $msg->{recips};
				my $id = "${server}_$msg->{id}";
				$content .= "
					<tr id=\"row_${server}_$msg->{id}\" class=\"messageList\">
							 <td class=\"messageSelect\">
							 	<input name=\"$id\" id=\"$id\" class=\"messageSelector\" type=\"checkbox\"/></td>
							 <td class=\"msgEnvSender\"><span id=\"${id}_sender\"><a href=\"#\" id=\"a_$id\" class=\"viewmsg\">$msg->{sender}</a></span></td>
							 <td class=\"msgAuthSender\"><span id=\"${id}_authuser\" class=\"$unclickable\">$authuser</span></td>
							 <td class=\"msgHost\"><span id=\"${id}_host\">$msg->{host}</span></td>
							 <td class=\"msgSubject\"><a href=\"#\" id=\"a_$id\" class=\"viewmsg\">$msg->{subject}</a></td>
							 <td class=\"msgDate\">$date</td>
							 <td class=\"msgRecips\">$recipValue</td>
					</tr>\n";
				last if ($total == $limit);
			}
		}
		last if ($limit && $total >= $limit);
	}
	# Ensure that jQuery marks up the message List
	$content .= "</table><script type=\"text/javascript\">setMsgListCSS()</script>";

	if ($total == 0 && !$start)
	{
		$content = "No Messages";		
	}

	if ($unique)
	{
		foreach $key (keys %seenusers)
		{
			my $count = $seenusers{$key};
			$content =~ s/###\Q$key\E###/$count/g;
		}
	}
	print $content;
	exit 0;
}

sub viewmsg()
{
	my $msgid = shift;
	$msgid =~ s/^a_//; #/
	($server,$qid) = split(/_/,$msgid);
	if (!$server_h{$server})
	{
		$error = "Unrecognized queue identifier";
		error_page();	
	}
	my $msg = process_q_cmd($server,"view $qid");

	print "Content-type: text/html\n\n";
	print "<pre>";
	$rawmsg = $q->escapeHTML($msg);
	$inpre = 1;
	$inrcpt = 0;
	$inmsg = 0;
	@rcpts = ();
	foreach $l (split(/\n/,$rawmsg))
	{
		if ($inpre)
		{
			if ($l !~ /^RCPT:/)
			{
				$premsg .= "$l\n";
			}
			else
			{
				$inpre = 0;
				$inrcpt = 1;
			}
		}
		if ($inrcpt)
		{
			if ($l =~ /^RCPT: (.*)/)
			{
				push(@rcpts,$1);
			}
			else
			{
				$inrcpt = 0;
				$inmsg = 1;
			}
		}
		if ($inmsg)
		{
			$postmsg .= "$l\n";
		}
	}
	if (scalar(@rcpts) < 15)
	{
		$premsg .= join("\n",@rcpts);
		$hiddenrcpts = "0";
	}
	else
	{
		$premsg .= join("\n",@rcpts[0..9]);
		$hiddenrcpts = join("\n",@rcpts[10..$#rcpts]);
	}

	print $premsg;
	if ($hiddenrcpts ne "0")
	{
		print "</pre>\n";
		print "[ " . ($#rcpts - 10) . " more recipients hidden. <a href=\"#\" onClick=\"unhideRecipients()\"><b>Toggle hidden</b></a> ]\n";
		print "<div id=\"hiddenrcpts\" style=\"display: none;\">";
		print "<pre>$hiddenrcpts</pre>\n";
		print "</div>\n<pre>";
	}
	print $postmsg,"</pre>";
	exit 0;
}

sub release_or_del_msgs()
{
	my $cmd = shift;
	my @filters,@selected;

    my $del = 0;
    $del = 1 if ($cmd =~ /^d/);

	## after debugging, remove the prints and call main_page when we're done
	print "Content-type: text/html\n\n";

	# If we're releasing/deleting based on sender or hostname, collect the filter
	# Otherwise, get the list of selected queue IDs
	if ($cmd =~ /_[sha]$/)
	{
		@filters = split(/;/,$q->param("filterOn"));
		foreach (@filters)
		{
			if ($cmd =~ /_h$/)
			{
				# Our filter is a host - strip it down to just the IP address if possible
				if (/\[(\d+\.\d+\.\d+\.\d+)\]/)
				{
					$_ = $1;
				}
			}
			release_or_del_filter_msg($_,$del);
		}
	} 
	else
	{
		@selected = get_selected_msgs();
		foreach (@selected)
		{
			release_or_del_id_msg($_,$del);
		}
	}

}

## Release a single message from a single server
# Argument is in the form of $server_$queueIdentifier
sub release_or_del_id_msg()
{
	my ($msgid,$del) = @_;
	($server,$qid) = split(/_/,$msgid);
	if (!$server_h{$server})
	{
		$error = "Unrecognized queue identifier";
		error_page();	
	}
	my $cmd = ($del) ? "deleteI" : "releaseI";
	process_q_cmd($server,"$cmd $qid");
	# print "$server releaseI $qid<br>\n";
}

# Release/delete msgs based on sender or host - must be sent to all mail servers just in case
# Argument is sender email or hostname (for hostname, we can only delete, not release)
sub release_or_del_filter_msg()
{
	my ($filter,$del) = @_;
	my $cmd = ($del) ? "delete" : "releaseS";
	foreach my $server (@servers)
	{
		log("release_or_del_by_filter processing $server")
		process_q_cmd($server,"$cmd $filter");
		# print "$server releaseS $filter<br>\n";
	}
}

sub get_selected_msgs()
{
	my @results;
	foreach my $server (@servers)
	{
		foreach my $param (@params)
		{
			push (@results,$param) if ($param =~ /${server}_/);
		}
	}
	return @results;
}

# Handle additions to the whitelist or blacklist db files for the Rate Limit
# Milter servers

sub ratelimit_quickadd()
{
	my $op = shift;

	my $value = "";

	# Collect the key (IP, netblock, username, or email address) from the form
	my $key = $q->param("address_".$op);
	# Collect the value (only set if it's a whitelist entry)
	$value = $q->param("threshold") if ($op eq "w");

	# TODO: We should do some sanity checking on the key/value pair we got

	# Encode the key/value pair (even if the value is empty) as a JSON-encoded hash
	$data = to_json({ $key => $value });

	# Target file we'll be making changes to
	my $what = ($op eq "b") ? "mailfromdblacklist" : "mailfromdwhitelist";

	foreach $server (@mailfromds)
	{
		# Send the 'append' command to each mailfromd server
		process_q_cmd($server,"append $what $data");
	}
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

sub log()
{
	open(LOG,">>/tmp/quarantinecgi.log") or return;
	print LOG scalar(localtime()),": ",@_,"\n";
	close LOG;
}
