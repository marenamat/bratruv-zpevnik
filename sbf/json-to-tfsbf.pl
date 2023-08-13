#!/usr/bin/perl

use utf8;
use common::sense;
use Data::Dump;
use JSON;

use FindBin;
use lib "$FindBin::Bin";
use TFSBF;

open F, "<", "songbook.json" or die $!;
open G, ">:utf8", "songbook.tfsbf" or die $!;
undef local $/;

print G TFSBF::from_obj decode_json <F>;
close G;
close F;
