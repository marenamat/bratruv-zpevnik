package TFSBF;

use utf8;
use common::sense;
use List::Util qw/max/;

our (%mapping_by_json, %mapping_by_tfsbf);

sub mapping(@) {
  my $obj = { @_ };
  die "json name not set" unless exists $obj->{json};
  die "tfsbf name not set" unless exists $obj->{tfsbf};

  die "duplicate json name" if exists $mapping_by_json{$obj->{json}};
  die "duplicate tfsbf name" if exists $mapping_by_tfsbf{$obj->{tfsbf}};

  $mapping_by_json{$obj->{json}} = $obj;
  $mapping_by_tfsbf{$obj->{tfsbf}} = $obj;
}

mapping (
  json => "lyrics",
  tfsbf => "LYRI",
  fill => "~",
  order => 0,
);

mapping (
  json => "chord",
  tfsbf => "CHRD",
  fill => " ",
  order => -10,
  always_fill => 1,
);

sub from_json($) {
  my @lines;
  foreach my $s (@{$_[0]->{"universal-songbook-format:songbook"}->{"songs"}})
  {
    push @lines, "SONG";
    push @lines, "TITL $s->{title}";
    push @lines, "AUTH $_" foreach (@{$s->{authors}});

    foreach my $blk (@{$s->{blocks}})
    {
      push @lines, "REFR $blk->{ref}" and next if exists $blk->{ref};
      push @lines, "BLCK $blk->{name}";
      foreach my $l (@{$blk->{lines}})
      {
	my %keys = map +( map +( $_ => 1 ), grep { $_ ne "key" } keys %$_ ), @{$l->{segments}};
	exists $mapping_by_json{$_} or die "Unknown segment key \"$_\", update mappings in TFSBF.pm accordingly" foreach (keys %keys);
	defined $mapping_by_json{$_} or delete $keys{$_} foreach (keys %keys);
	my @k = sort { $mapping_by_json{$a}->{order} <=> $mapping_by_json{$b}->{order} } keys %keys;

	my %lines = map +( $_ => $mapping_by_json{$_}->{tfsbf} . " " ), @k;
	foreach my $s (@{$l->{segments}})
	{
	  my $m = max map +( $mapping_by_json{$_}->{always_fill} + length $s->{$_} ), grep { exists $s->{$_} } @k;
	  $lines{$_} .= ($s->{$_} . $mapping_by_json{$_}->{fill} x ($m - length $s->{$_})) foreach (@k);
	}
	push @lines, $lines{$_} foreach (@k);
      }
    }

    push @lines, "ENDS";
  }

  return join "\n", (@lines, "");
}

42;
