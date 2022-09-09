#!/usr/bin/perl

use CGI;
use FindBin;
use lib "$FindBin::Bin";
use lib "/usr/local/lib";
use Rest;

$q = CGI->new;

@params = $q->param;

$list = $q->param("list");
$regex = $q->param("regex");
$format = $q->param("format") || "csv";
$lookup = $q->param("lookup") ? 1 : 0;
$notes = $q->param("notes") ? 1 : 0;

if (!$list)
{
	error_page("Missing 'list' parameter");
}

$remote_user = $q->remote_user();

$excludes = [];
$members = [];
$mandatories = {};
@lists = split(/,/,$list);
foreach $l (@lists)
{
    	$mems = [];
	$exclude = $mandatory = 0;
	if ($l =~ /^\-/)
	{
		$exclude = 1;
		$l =~ s/^\-//;
	}
	elsif ($l =~ /^!/)
	{
		$hasmandatory = 1;
		$mandatory = 1;
		$l =~ s/^!//;
		$mandatories->{$l} = [];
	}

    	if ($l =~ /.txt$/ && $l !~ /\// && -f "/home/hillman/mail/files/$l")
    	{
		open(IN,"/home/hillman/mail/files/$l");
		while(<IN>)
		{
	   		chomp;
			push @$mems,$_;
		}
		close IN;
    	}
	else
	{
		$mems =  members_of_maillist($l);
	}

	if ($exclude)
	{
		push @$excludes,@$mems;
	}
	elsif ($mandatory)
	{
		push @{$mandatories->{$l}},@$mems;
	}
	else
	{
		push @$members,@$mems;
	}

}

if (!$members)
{
	error_page("Error retrieving members for list $list. Does it exist?");
}

foreach $u (@$excludes)
{
	$ex{$u} = 1;
}

if ($hasmandatory)
{
	$count = 0;
	foreach $k (keys %$mandatories)
	{
		$count++;
		foreach $u (@{$mandatories->{$k}})
		{
			$man{$u} += 1;
		}
	}
	foreach $u (keys %man)
	{
		delete($man{$u}) if ($man{$u} != $count);
	}
}
foreach $u (@$members)
{
	if ($hasmandatory)
	{
		next if (!defined($man{$u}));
	}
	$user{$u} = 1 if (!defined($ex{$u}));
}

print "Content-type: text/plain\n\n";

print "Migrate,ExportName,ImportName,ExportObjectType,ImportObjectType\n" if ($format eq "csv");
print "Migrate,Id,ParentNodeId,ExportObjectType,ImportObjectType,ExportName,ImportName,GivenName,FamilyName,Password,ArchivePath,DocumentsPath,MigrateMail,MigrateContacts,MigrateCalendar,MigrateDrive,MigrateSites,MigrateTasks,ExportObjectRef,I
mportObjectRef,MigrateNotes\n" if ($format eq "extended");

foreach $user (sort keys %user)
{
	if ($lookup)
	{
		$migrate = "true";
		if (-f "/home/hillman/mail/migrations/$user/all")
		{
			$status = `cat /home/hillman/mail/migrations/$user/all`;
			if ($status =~ /completed/)
			{
				$found = 1;
				@reports = split(/\n/,`ls -1t /home/hillman/mail/migrations/$user/reports`);
				if (open(IN,"/home/hillman/mail/migrations/$user/reports/".$reports[0]))
				{
					# scan the most recent report file for errors
					$found=0;
					while(<IN>)
					{
						if (/(mailbox database|connect.sfu.ca|Unauthorized)/)
						{
							$found=1;
							last;
						}
					}
					close IN;
				}
				$migrate = ($found) ? "true" : "false";
			}
		}
	}
	elsif ($notes)
	{
		next if (! -f "/home/hillman/mail/migrations/$user/userstats.txt");
		$errors=0;
		open(USERSTATS,"/home/hillman/mail/migrations/$user/userstats.txt");
		while(<USERSTATS>)
		{
			next if (! /All mail.Status: Migration completed with warnings or errors/);
			$errors = 1;
			last;
		}
		close USERSTATS;
		next if (! $errors);
		@reports = split(/\n/,`ls -1t /home/hillman/mail/migrations/$user/reports`);
		if (open(IN,"/home/hillman/mail/migrations/$user/reports/".$reports[0]))
		{
			# scan the most recent report file for errors
			$found=0;
			while(<IN>)
			{
				if (/A folder with the specified name/)
				{
					if (/Notes/i)
					{
						$found=1;
						last;
					}
					else
					{
						open(LOG,">>/tmp/$$.log");
						print LOG "$user: $_";
						close LOG;
					}
				}
			}
			close IN;
		}
		next if (!$found);
		$migrate =  "true";
	}
	else
	{
		$migrate = "true";
	}
	if ($regex)
	{
		next if ($user !~ /$regex/);
	}
	if ($user =~ /\@resource.sfu.ca/ && $format eq "csv")
	{
		$user =~ s/\@.*//;
		print "true,$user\@sfu.ca,$user,Resource,Resource\n";
	}
	elsif ($user =~ /\@resource.sfu.ca/ && $format eq "extended")
	{
		$user =~ s/\@.*//;
		print "true,,,Resource,Resource,$user\@sfu.ca,$user,,,,,,,,,,,,,,\n";
	}
	elsif ($format eq "extended")
	{
		print "$migrate,,,User,User,$user\@sfu.ca,$user,,,,,,,,,,,,,,\n";
	}

	elsif ($format eq "csv")
	{
		print "$migrate,$user\@sfu.ca,$user,User,User\n";
	}
	else
	{
		print "$user\n";
	}
}

exit 0;


sub error_page()
{
	$error = shift;
	print "Content-type: text/html\n\n";
	print <<EOF;
<HEAD>
 <Title>Something went wrong</Title>
</HEAD>
<Body>
<h3>
 An error occurred: $error
</h3>
<br>
<b>
Usage: generate.cgi?list=&lt;list&gt;[,&lt;list&gt;,&lt;list&gt;,&lt;-list&gt;][&amp;regex=&lt;regex&gt;][&amp;format=txt]
</b>
<p>
<ul>
<li>Specify one or more lists, comma separated, to combine members of lists.
<ul><li>Members of lists preceded with a "-" will be excluded from output. </li>
<li>Lists preceded with a '!' are "mandatory" - i.e. the user <b>must</b> be a member of that list to be included in the final result (this functions as a logical AND</li>
</ul></li>
<li>Optionally specify a regex to limit output to users matching the regex (e.g. regex=^a : only output accts beginning with 'a')</li>
<li>Optionally specify format=txt to just get a list of accounts, useful for populating a new maillist</li>
</ul>
</BODY>
EOF
	exit 0;
}
