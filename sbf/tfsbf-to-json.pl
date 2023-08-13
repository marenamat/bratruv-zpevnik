#!/usr/bin/perl

use utf8;
use common::sense;
use Data::Dump;
use JSON;

use FindBin;
use lib "$FindBin::Bin";
use TFSBF;

say "n";
open F, "<:utf8", "songbook.tfsbf" or die $!;
open G, ">", "songbook.json" or die $!;
undef local $/;

my $J = JSON->new;
$J->pretty();
$J->canonical(1);
$J->space_before(0);

my $edata = $J->encode(TFSBF::to_obj <F>);
$edata =~ s/   /  /g;
print G $edata;
close G;
close F;
