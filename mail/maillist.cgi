#!/usr/bin/perl

use JSON;
use CGI;
use IO::Socket::INET;
use DB_File;

$pagedir = "pages";

# Where we store the opt-ins
$TRACKERDB = "/data/lists-to-keep.db";
# Where to retrieve info on who owns/manages a list that's been flagged for purging
$INPUTDB = "/data/listmanagers.db";

$q = CGI->new;

$remote_user = $q->remote_user();

@params = $q->param;

main_page() if (!scalar(@params));

$cmd = $q->param("cmd");
$pagename = $q->param("page");

logger("starting $cmd");

if ($cmd eq "getqueue")
{
	get_lists();
}

if ($cmd eq "save_sel")
{
    save_selected();
    main_page();
}


sub main_page()
{
	load_page("maillist.html");
}


sub get_lists()
{
    tie %inputdb,"DB_File",$INPUTDB,O_RDONLY,0644,$DB_HASH;
    tie %trackdb,"DB_File",$TRACKERDB,O_RDONLY|O_CREAT,0644,$DB_HASH;
    my @lists = ();

    print "Content-type: text/html\n\n";

    my $content = "You are not a Manager or Owner of any maillists identified for deletion<br>";

    if (exists $inputdb{$remote_user})
    {
        @lists = split(/,/,$inputdb{$remote_user});
        $content = "<span class=\"maillistWarning\">The lists below will be deleted unless you select any of them to save</span>
            <table class=\"messageTable\"\n><tr id=\"messageHeading\" class=\"messageHeading\">
            <td>Keep</td>
            <td>Maillist</td>
            <td>Description</td>
            <td>Owner</td>
            <td>Member Count</td>
        </tr>";
        foreach $id (@lists)
        {
            # Fetch list data from MLRest
            $listObj = get_maillist($id)

            if (exists $trackdb{$id} )
            {
                # List has already been claimed. Use a different summary with no checkbox
                $content .= "
                    <tr class=\"messageList\">
                        <td class=\"messageSelect\">SAVED</td>
                        <td class=\"maillistName\">$id</td>
                        <td class=\"maillistDescr\">$listObj->{desc}</td>
                        <td class=\"maillistOwner\">$listObj->{owner}</td>
                        <td class=\"maillistMembers\">$listObj->{memberCount}</td>
                    </tr>\n";
            } 
            else
            {
                $content .= "
                    <tr class=\"messageList\">
                        <td class=\"messageSelect\">
                            <input name=\"$id\" id=\"$id\" class=\"messageSelector\" type=\"checkbox\"/></td>
                        <td class=\"maillistName\">$id</td>
                        <td class=\"maillistDescr\">$listObj->{desc}</td>
                        <td class=\"maillistOwner\">$listObj->{owner}</td>
                        <td class=\"maillistMembers\">$listObj->{memberCount}</td>
                    </tr>\n";
            }
        }
        # Ensure that jQuery marks up the message List
	    $content .= "</table><script type=\"text/javascript\">setMsgListCSS()</script>";
    
    }
    print $content;

    untie %inputdb;
    untie %trackdb;

    exit 0;
}

sub save_selected
{
    # First get the list of lists this user is authorized to claim
    tie %inputdb,"DB_File",$INPUTDB,O_RDONLY,0644,$DB_HASH;
    tie %trackdb,"DB_File",$TRACKERDB,O_RDWR|O_CREAT,0644,$DB_HASH;
    return if (! exists $inputdb{$remote_user});
    my %lists = map { $_ => 1 } split(/,/,$inputdb{$remote_user});

    # Save the list of selected lists from the passed in params, as long as they're authorized
    my @mylists;
    foreach my $param (@params)
    {
        if (exists $lists{$param})
        {
            $trackdb{$param} = $remote_user;
            logger("$param list has been claimed");
        }
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

sub logger()
{
	open(LOG,">>/tmp/maillistcgi.log") or return;
	print LOG scalar(localtime()),": $remote_user : ",@_,"\n";
	close LOG;
}
