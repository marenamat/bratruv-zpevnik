#!/usr/bin/perl

use utf8;
use locale;
use common::sense;
use Data::Dump;
use JSON;

open F, "<:utf8", "../zpevnik.tex" or die $!;
my $data;
{ undef local $/; $data = <F>; }
close F;

sub segmentLine {
  $_[0] =~ s#^\s+##;
  chomp $_[0];
  return unless length $_[0];

  my @segments;

  my $d = $_[0];
  my $prevchord;
  while ($d =~ m#\\([ABCDEFGH][^{}]*)\{\}#p)
  {
    my $prevly = ${^PREMATCH};
    push @segments, { (defined $prevchord ? ("chord" => $prevchord) : ()), "lyrics" => $prevly, key => 1 + scalar @segments } if (defined $prevchord or length $prevly);
    $prevchord = $1;
    $d = ${^POSTMATCH};
  }

  push @segments, { (defined $prevchord ? ("chord" => $prevchord) : ()), "lyrics" => $d, key => 1 + scalar @segments } if (defined $prevchord or length $d);

  return [ @segments ];
}

sub lineBlock {
  #    dd [ $_[0] ];
  my $name = ($_[0] =~ s#^\{([^{}]+)\}##s) ? $1 : "_pab_" . (int 1000 * rand);
  #    dd [ $name, $_[0] ];
  my $o = { "name" => "$name" // ("_pab_" . (int 1000 * rand)), "lines" => [ grep { scalar @{$_->{segments}} } map +( { "segments" => segmentLine($_) } ), split /\\\\/, $_[0] ], };

  return unless @{$o->{lines}};

  for (my $i=0; $i<@{$o->{lines}}; $i++)
  {
    $o->{lines}->[$i]->{key} = $i + 1;
  }
  return $o;
}

my @songs;
my %authors;

while ($data =~ m#\\song\{(?<title>[^{}]+)\}\{(?<author>[^{}]+)\}\{(?:[^{}]+)\}\{(?:[^{}]+)\}\{(?<contents>(?:[^{}]|\{(?&contents)\})*)\}#gs)
{
  my %song = %+;

  $song{contents} =~ s#(?<=[^\\])%.*##gm;
  my $chcnt;
  while ($song{contents} =~ s#\\chorus(\{\})?#\\verse{R$chcnt}#s)
  {
    $chcnt = 1 unless defined $chcnt;
    $chcnt++;
  }

  $song{contents} =~ s#\\printchords\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#$+{inner}#gs;
  $song{contents} =~ s#\\uv\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#„$+{inner}“#gs;
  $song{contents} =~ s#\\noexport\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}##gs;
  $song{contents} =~ s#\\scalebox\{[^{}]+\}\[\d+\]\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#„$+{inner}“#gs;
  $song{contents} =~ s#\\(vskip |leftskip |hskip |rightskip |crdheight=)-?\d+(\.\d+)?(pt|ex|em)##gm;
  $song{contents} =~ s#\\setlength\{[^{}]+\}\{[^{}]+\}##gm;
  $song{contents} =~ s#\\(smallskip|medskip|clearpage|vfill|begin\{minipage\}\[t\]\{[^{}]+\}|end\{minipage\})##gm;
  $song{contents} =~ s#\$\\sharp\$#s#gm;
  $song{contents} =~ s#\\ldots#…#gm;
  $song{contents} =~ s#\n# #gs;

  $song{contents} =~ s#\\capo\{(?<capo>\d+)\}##gm; # TODO: store the capo information

  $song{blocks} = [ grep { scalar @{$_->{lines}} } map +( lineBlock($_ ) ), split /\\verse/, $song{contents} ];
  delete $song{contents};
  
  $authors{$song{author}}++;
  $song{authors} = [ $song{author} ];
  delete $song{author};

  push @songs, \%song;
  #dd \%song;
  #  say $song{contents};
}

my $J = JSON->new;
$J->pretty();
$J->space_before(0);
$J->canonical(1);

open F, ">", "imported.json" or die $!;
my $edata = $J->encode ({
  "universal-songbook-format:songbook" => {
    "authors" => [ map +( { "name" => $_ } ), sort { $::a cmp $::b } keys %authors ],
    "songs" => \@songs,
  },
});
$edata =~ s/   /  /g;
print F $edata;
close F;
