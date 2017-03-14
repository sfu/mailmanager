#!/usr/bin/perl

use JSON;
use CGI;
use IO::Socket::INET;

@servers = ("rm-rstar1.tier2.sfu.ca","rm-rstar2.tier2.sfu.ca","mailgw1.tier2.sfu.ca","mailgw2.tier2.sfu.ca","pobox1.tier2.sfu.ca","pobox2.tier2.sfu.ca","mailgw.alumni.sfu.ca");

$pagedir = "pages";



foreach (@servers) { $server_h{$_} = 1;}


$q = CGI->new;

@params = $q->param;

main_page() if (!scalar(@params));

$cmd = $q->param("cmd");

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

	print "Content-type: text/html\n\n";

	my $heading = "<tr id=\"messageHeading\" class=\"messageHeading\"><td>√</td><td>Envelope Sender</td><td>X-Auth-Sender</td><td>Host</td><td>Subject</td><td>Date</td><td>Recipients</td></tr>\n";
	# If starting from the beginning, add the header to the result
	if (!$start)
	{
		$content = "<table class=\"messageTable\">\n";
	}
	my $json = JSON->new->allow_nonref;
	foreach $server (@servers)
	{
		my $jsonstr = process_q_cmd($server,"queuejson");
		$q_json = $json->decode($jsonstr);
		if ($q_json->{total} > 0)
		{
			$content .= "<tr class=\"messageServer\"><td colspan=\"7\" style=\"text-align: center;\">Host: $server</td></tr>\n$heading";
			foreach $msg (@{$q_json->{messages}})
			{
				$total++;
				next if ($start > $total);

				# Calculate date the msg was originally sent
				my @msgtime = localtime($msg->{ctime});
				$date = $msgtime[2].":".$msgtime[1];			
				if ($msgtime[7] == $today[7] - 1)
				{
					$date .= " Yesterday";
				} elsif ($msgtime[7] != $today[7])
				{
					$date .= " $msgtime[4]/$msgtime[3]";
				}
					
				# Build the HTMl table row for this msg
				my $id = "${server}_$msg->{id}";
				$content .= "
					<tr id=\"row_${server}_$msg->{id}\" class=\"messageList\">
							 <td class=\"messageSelect\">
							 	<input name=\"$id\" id=\"$id\" class=\"messageSelector\" type=\"checkbox\"/></td>
							 <td class=\"msgEnvSender\"><span id=\"${id}_sender\">$msg->{sender}</span></td>
							 <td class=\"msgAuthSender\"><span id=\"${id}_authuser\">$msg->{authuser}</span></td>
							 <td class=\"msgHost\"><span id=\"${id}_host\">$msg->{host}</span></td>
							 <td class=\"msgSubject\"><a href=\"#\" id=\"a_$id\" class=\"viewmsg\">$msg->{subject}</a></td>
							 <td class=\"msgDate\">$date</td>
							 <td class=\"msgRecips\">$msg->{recips}</td>
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
	print $content;
	exit 0;
}

sub viewmsg()
{
	my $msgid = shift;
	$msgid =~ s/^a_//;
	($server,$qid) = split(/_/,$msgid);
	if (!$server_h{$server})
	{
		$error = "Unrecognized queue identifier";
		error_page();	
	}
	my $msg = process_q_cmd($server,"view $qid");

	$msg =~ s/</&lt;/g;
	$msg =~ s/>/&gt;/g;
	$msg =~ s/&/&amp;/g;

	print "Content-type: text/html\n\n";
	print "<pre>$msg</pre>\n";

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
	if ($cmd =~ /_[sh]$/)
	{
		@filters = split(/;/,$q->param("filterOn"));
		foreach (@filters)
		{
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
