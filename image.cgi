#!/usr/bin/perl

use CGI;
use DB_File;

$q = CGI->new;

@params = $q->param;

$uuid = $q->param("uuid");

if (defined($uuid))
{
    tie %tracker, "DB_File","/data/tracker.db",O_CREAT|O_RDWR,0644,$DB_HASH;
    $tracker{$uuid} = time();
    untie %tracker;
}

print "Content-Type: image/png\n\n";
open(IMG,"/var/www/html/resources/images/1x1.png");
binmode IMG;
my $buf;
read IMG,$buf,1024;
print $buf;
close IMG;
exit 0;
