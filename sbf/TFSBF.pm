package TFSBF;

use utf8;
use locale;
use common::sense;
use Data::Dump;
use List::Util qw/max min/;

our (%mapping_by_json, %mapping_by_tfsbf);

sub mapping(@) {
  my $obj = { @_ };
  die "tfsbf name not set" unless exists $obj->{tfsbf};

  die "duplicate json name" if exists $obj->{json} and exists $mapping_by_json{$obj->{json}};
  die "duplicate tfsbf name" if exists $mapping_by_tfsbf{$obj->{tfsbf}};

  $obj->{chunkre} = qr/^(?<data>[^$obj->{fill}]*)(?<fill>[$obj->{fill}]+)/ if exists $obj->{fill};

  $mapping_by_json{$obj->{json}} = $obj if exists $obj->{json};
  $mapping_by_tfsbf{$obj->{tfsbf}} = $obj;
}

sub flushline($) {
  my ($ctx) = @_;

  my @L = @{$ctx->{curline}};
  delete $ctx->{curline};
  delete $ctx->{lastorder};
  
  my @segments;

  while (1) {
    foreach (@L)
    {
      %$_ = ( %$_, ($_->{args} =~ $mapping_by_tfsbf{$_->{name}}->{chunkre})
      ? %+ : ( data => $_->{args}, fill => "" ));

      $_->{len} = length $_->{data} . $_->{fill};
    }

    my $len = min map +($_->{len}), @L;

    last if $len == 0;

    foreach (@L) {
      $_->{data} = substr $_->{data}, 0, $len;
      substr $_->{args}, 0, $len, "";
    }

    push @segments, {
      key => 1 + scalar @segments,
      map +( length $_->{data} ? ($mapping_by_tfsbf{$_->{name}}->{json} => $_->{data}) : ()), @L,
    };
  }

  push @{$ctx->{curblock}->{lines}}, { key => 1 + scalar @{$ctx->{curblock}->{lines}}, segments => [ @segments ] };
}

sub linegen($$) {
  my ($ctx, %arg) = @_;
  exists $ctx->{curblock} or die "Open block by BLCK first: $arg{name} $arg{args}";
  my $map = $mapping_by_tfsbf{$arg{name}};
  flushline $ctx if defined $ctx->{lastorder} and $ctx->{lastorder} >= $map->{order};

  push @{$ctx->{curline}}, { %arg };
  $ctx->{lastorder} = $map->{order};
}

mapping (
  json => "lyrics",
  tfsbf => "LYRI",
  fill => "~",
  nofill => 1,
  order => 0,
  generate => \&linegen,
);

mapping (
  json => "chord",
  tfsbf => "CHRD",
  fill => " ",
  order => -10,
  generate => \&linegen,
);

mapping (
  tfsbf => "SONG",
  generate => sub {
    my $ctx = shift;
    exists $ctx->{cursong} and die "Previous song not ended by ENDS";
    $ctx->{cursong} = {};
  },
);

mapping (
  tfsbf => "TITL",
  generate => sub {
    my ($ctx, %arg) = @_;
    exists $ctx->{cursong} or die "Open song by SONG first";
    exists $ctx->{cursong}->{title} and die "Song title already set";
    $ctx->{cursong}->{title} = $arg{args};
  },
);

mapping (
  tfsbf => "AUTH",
  generate => sub {
    my ($ctx, %arg) = @_;
    exists $ctx->{cursong} or die "Open song by SONG first";
    push @{$ctx->{cursong}->{authors}}, $arg{args};
    push @{$ctx->{authors}->{$arg{args}}}, $ctx->{cursong};
  },
);

sub open_block($$) {
  my ($ctx, $name) = @_;
  exists $ctx->{block_index}->{$name} and die "Duplicate block name $name";
  push @{$ctx->{cursong}->{blocks}}, $ctx->{curblock} = $ctx->{block_index}->{$name} = { name => $name };
}

sub close_block($) {
  my ($ctx) = @_;
  flushline $ctx if defined $ctx->{lastorder};
}

mapping (
  tfsbf => "REFR",
  generate => sub {
    my ($ctx, %arg) = @_;
    exists $ctx->{cursong} or die "Open song by SONG first";
    close_block $ctx;
    exists $ctx->{block_index}->{$arg{args}} or die "Bad block reference $arg{args}";
    open_block $ctx, "_autoref_" . int $ctx->{autoref}++;
    delete $ctx->{curblock};
  },
);

mapping (
  tfsbf => "BLCK",
  generate => sub {
    my ($ctx, %arg) = @_;
    exists $ctx->{cursong} or die "Open song by SONG first";
    close_block $ctx;
    open_block $ctx, $arg{args};
  },
);

mapping (
  tfsbf => "ENDS",
  generate => sub {
    my $ctx = shift;
    exists $ctx->{cursong} or die "Open song by SONG first";
    close_block $ctx;
    push @{$ctx->{songs}}, $ctx->{cursong};
    map { delete $ctx->{$_} } grep { $_ !~ m/^songs|authors$/ } keys %$ctx;
  },
);

sub from_obj($) {
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
	  my $m = max map +( 1 - $mapping_by_json{$_}->{nofill} + length $s->{$_} ), grep { exists $s->{$_} } @k;
	  $lines{$_} .= ($s->{$_} . $mapping_by_json{$_}->{fill} x ($m - length $s->{$_})) foreach (@k);
	}
	push @lines, $lines{$_} foreach (@k);
      }
    }

    push @lines, "ENDS";
  }

  return join "\n", (@lines, "");
}

sub to_obj($) {
  my $ctx = { songs => [] };

  foreach (split /\n/, $_[0])
  {
    /^\s*$/ and next; # ignore empty lines
    /^(?<name>[A-Za-z0-9]{4})(?: (?<args>.*))?$/p or die "Malformed line: $_";
    exists $mapping_by_tfsbf{$+{name}} or die "Unknown line tag $+{name}";
    $mapping_by_tfsbf{$+{name}}->{generate}->($ctx, %+);
  }

  return { "universal-songbook-format:songbook" => {
      songs => $ctx->{songs},
      authors => [ map +( {
	    name => $_,
	  } ), sort { $a cmp $b } keys %{$ctx->{authors}} ],
    }};
}

42;
