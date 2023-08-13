#!/usr/bin/perl

use utf8;
use locale;
use common::sense;
use Data::Dump;
use Devel::Peek qw/ Dump /;
use JSON;

$|++;

open F, "<:utf8", "../zpevnik.tex" or die $!;
my $data;
{ undef local $/; $data = <F>; }
close F;

sub segmentLy($) {
  my $p = $_[0];
  $p =~ s/^\s+$//;
  $p =~ s/\s+-\s+$//;
  $p =~ s/\s+$/ /;
  return $p;
}

sub segmentLine {
  $_[0] =~ s#^\s+##;
  chomp $_[0];
  return unless length $_[0];

  my @segments;

  my $d = $_[0];
  my $prevchord;
  while ($d =~ m#\\([ABCDEFGH].*?)\{\}#p)
  {
    $d = ${^POSTMATCH};
    my $newchord = $1;
    my $prevly = segmentLy ${^PREMATCH};

    push @segments, {
      (defined $prevchord ? ("chord" => $prevchord) : ()),
      (length $prevly ? ("lyrics" => $prevly) : ()),
      key => 1 + scalar @segments,
    } if (defined $prevchord or length $prevly);

    $prevchord = $newchord;
    $prevchord =~ s/\s+$//;
  }

  $d = segmentLy $d;

  push @segments, {
    (defined $prevchord ? ("chord" => $prevchord) : ()),
    (length $d ? ("lyrics" => $d): ()),
    key => 1 + scalar @segments,
  } if (defined $prevchord or length $d);

  return [ @segments ];
}

sub autoBlockCnt($$)
{
  return "_$_[1]_" . ($_[0]->{autoblockcnt}++);
}

sub lineBlock {
  my @oo;
 
  push @oo, {
    "name" => (autoBlockCnt $_[1], "autoref"),
    "ref" => $+{"ref"},
  } if $_[0] =~ s/^\{!!reference!!(?<ref>[^{}!]+)!!\}//;

  my $name = ($_[0] =~ s#^\{([^{}]+)\}##s) ? $1 : autoBlockCnt $_[1], "pab";
  $_[0] =~ s#^\{\}##g;

  my $o = { "name" => "$name", "lines" => [ grep { scalar @{$_->{segments}} } map +( { "segments" => segmentLine($_) } ), split /\\\\/, $_[0] ], };

  return @oo unless @{$o->{lines}};

  for (my $i=0; $i<@{$o->{lines}}; $i++)
  {
    $o->{lines}->[$i]->{key} = $i + 1;
  }

  push @oo, $o;
  return @oo;
}

my @songs;
my %authors;

while ($data =~ m#\\song\{(?<title>[^{}]+)\}\{(?<author>[^{}]+)\}\{(?:[^{}]+)\}\{(?:[^{}]+)\}\{(?<contents>(?:[^{}]|\{(?&contents)\})*)\}#gs)
{
  my %song = %+;

  $song{contents} =~ s#(?<=[^\\])%.*##gm;
  $song{autoblockcnt} = 0;
  my $chcnt;
  while ($song{contents} =~ s#\\chorus(?:\{\})?#\\verse{R$chcnt}#s)
  {
    $chcnt = 1 unless defined $chcnt;
    $chcnt++;
  }

  $song{contents} =~ s#^~\\\\$##gm;
  $song{contents} =~ s#\\printchords\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#$+{inner}#gs;
  $song{contents} =~ s#\\uv\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#„$+{inner}“#gs;
  $song{contents} =~ s#\s*\\noexport\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#$+{inner}#gs;
  $song{contents} =~ s#\\(scalebox|textls)\{[^{}]+\}\[\d+\]\{(?<inner>(?:[^{}]|\{(?&inner)\})*)\}#$+{inner}#gs;
  $song{contents} =~ s#\\(vskip |leftskip |hskip |rightskip |crdheight=)-?\d+(\.\d+)?(pt|ex|em)##gm;
  $song{contents} =~ s#\\setlength\{[^{}]+\}\{[^{}]+\}##gm;
  $song{contents} =~ s#\\(smallskip|medskip|clearpage|vfill|begin\{minipage\}\[t\]\{[^{}]+\}|end\{minipage\})##gm;
  $song{contents} =~ s#\$\\sharp\$#s#gm;
  $song{contents} =~ s#\\ldots#…#gm;
  $song{contents} =~ s#\n# #gs;
  $song{contents} =~ s#---#—#gs;
  $song{contents} =~ s#--#–#gs;

  $song{contents} =~ s#\\capo\{(?<capo>\d+)\}##gm; # TODO: store the capo information
  $song{contents} =~ s#\\textbf\{(?<ref>[^{}:]{1,3}):?\}#\\verse{!!reference!!$+{ref}!!}#gm;

  $song{blocks} = [ grep { scalar @{$_->{lines}} or exists $_->{ref} } map +( (lineBlock($_, \%song ))), split /\\verse/, $song{contents} ];
  delete $song{contents};
  delete $song{autoblockcnt};
  
  $authors{$song{author}}++;
  $song{authors} = [ $song{author} ];
  delete $song{author};

  push @songs, \%song;
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
