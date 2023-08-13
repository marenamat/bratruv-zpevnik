#!/usr/bin/perl

use utf8;
use common::sense;
use Data::Dump;
use List::Util qw/max/;
use JSON;

use FindBin;
use lib "$FindBin::Bin";
use TFSBF;

binmode STDOUT, ":utf8" or die $!;

open F, "<", "songbook.json" or die $!;
undef local $/;
print TFSBF::from_json decode_json <F>;
