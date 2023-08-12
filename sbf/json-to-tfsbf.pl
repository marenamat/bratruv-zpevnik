#!/usr/bin/perl

use utf8;
use common::sense;
use Data::Dump;
use List::Util qw/max/;
use JSON;

binmode STDOUT, ":utf8" or die $!;

my $j;

{
  open F, "<", "songbook.json" or die $!;
  undef local $/;
  $j = decode_json <F>;
}

my %mapping = (
  lyrics => {
    fill => "~",
    name => "LYRI",
    order => 0,
  },
  chord => {
    name => "CHRD",
    fill => " ",
    order => -10,
    always_fill => 1,
  },
  key => undef,
);

foreach my $s (@{$j->{"universal-songbook-format:songbook"}->{"songs"}})
{
  say "SONG";
  say "TITL $s->{title}";
  say "AUTH $_" foreach (@{$s->{authors}});

  foreach my $blk (@{$s->{blocks}})
  {
    say "REFR $blk->{ref}" and next if exists $blk->{ref};
    say "BLCK $blk->{name}";
    foreach my $l (@{$blk->{lines}})
    {
      my %keys = map +( map +( $_ => 1 ), keys %$_ ), @{$l->{segments}};
      exists $mapping{$_} or die "Unknown segment key \"$_\", update 'my \%mapping' accordingly" foreach (keys %keys);
      defined $mapping{$_} or delete $keys{$_} foreach (keys %keys);
      my @k = sort { $mapping{$a}->{order} <=> $mapping{$b}->{order} } keys %keys;

      my %lines = map +( $_ => $mapping{$_}->{name} . " " ), @k;
      foreach my $s (@{$l->{segments}})
      {
	my $m = max map +( $mapping{$_}->{always_fill} + length $s->{$_} ), grep { exists $s->{$_} } @k;
	$lines{$_} .= ($s->{$_} . $mapping{$_}->{fill} x ($m - length $s->{$_})) foreach (@k);
      }
      say $lines{$_} foreach (@k);
    }
  }

  say "ENDS";
}
