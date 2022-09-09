#!/usr/bin/perl

use DB_File;

$INPUTDB = "/data/listmanagers.db";

tie %inputdb,$INPUTDB,O_RDWR|O_CREAT,0644,$DB_HASH;

while(<>)
{
    chomp;
    ($user,$list) = split(/[\s,]+/);
    if (exists $inputdb{$user})
    {
        $inputdb{$user} .= ",$list";
    }
    else 
    {
        $inputdb{$user} = $list;
    }
}

foreach $k (keys %inputdb)
{
    print $k,": ",$inputdb{$k},"\n";
}
untie $inputdb;