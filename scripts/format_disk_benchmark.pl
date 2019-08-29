#!/usr/bin/perl

# Usage
#
# 1. Run benchmarking
#
#   $ cchq <env> run-shell-command -b <groups> 'wget -q -O /root/iolatency https://raw.githubusercontent.com/brendangregg/perf-tools/master/iolatency; chmod +x /root/iolatency; hostname; cd /opt/data/; iostat; dd bs=8192 if=/dev/zero of=/opt/data/testfile count=125000 conv=fdatasync; dd bs=8192 if=/opt/data/testfile of=/dev/null iflag=nocache count=125000; rm /opt/data/testfile; ls -l `mount | grep "on /opt/data type ext4" | cut -d\  -f 1 | cut -d/ -f 4 | cut -d- -f 1 | xargs -I "{}" bash -c "grep \"{}\" <(pvs)" | cut -d\  -f 3` | cut -d\  -f 5,6 | sed "s/ //" | xargs -I "{}" /root/iolatency -T 10 1 -d {}; rm /root/iolatency' > disk-all-benchmark
#
#    Descriptions of components in command chain:
#       Retrieve the iolatency script (available in package perf-tools-unstable starting in Ubuntu Xenial).
#
#           wget -q -O /root/iolatency https://raw.githubusercontent.com/brendangregg/perf-tools/master/iolatency
#
#       General IO metrics.
#
#           iostat
#
#       Copy and read back 1GB of zeros from a directory, ignoring caching as much as possible.
#
#           dd bs=8192 if=/dev/zero of=/opt/data/postgresql/9.6/main/testfile count=125000 conv=fdatasync; dd bs=8192 if=/opt/data/postgresql/9.6/main/testfile of=/dev/null iflag=nocache count=125000;
#
#       Report a histogram on the latencies experienced by device {}, with one 10 second sample taken.
#       Device should be specified as major,minor number as found in /dev.
#       E.g. for a device which appears in ls -l as brw-rw---- 1 root disk 8, 0 Jul 29 17:29 /dev/sda, the major,minor would be 8,0:
#
#           /root/iolatency -T 10 1 -d {}
#
#       A long chain designed to run the iolatency command only for the device containing the /opt/data mountpoint.
#       Mostly useful if you have large amounts of IO occurring on different devices.
#       Can be removed otherwise, along with the -d {} parameter for iolatency.
#
#           ls -l `mount | grep "on /opt/data type ext4" | cut -d\  -f 1 | cut -d/ -f 4 | cut -d- -f 1 | xargs -I "{}" bash -c "grep \"{}\" <(pvs)" | cut -d\  -f 3` \
#               | cut -d\  -f 5,6 | sed "s/ //" | xargs -I "{}" /root/iolatency -T 10 1 -d {}

#
# 2. Format benchmark
#
#   $ ./format_disk_benchmark.pl disk-all-benchmark
#

use strict;
use warnings;
no warnings qw(uninitialized);

use Data::Dumper;

my ($filename) = @ARGV;
open my $fh, '<', $filename or die $!;
my $hostname;
my $loadstats = {};
my $iostats = {};
my $latency = {};
my $writespeed = {};
my $readspeed = {};
while (my $line = <$fh>) {
    chomp $line;
    $hostname = $line if $line =~ /^MUMGCCWCD/;
    if ($hostname) {
        # Parse iostat output
        if ($line =~ /^avg-cpu/) {
            my (undef, $user, $nice, $system, $iowait, $steal, $idle) = split(/\s+/, <$fh>);
            $loadstats->{$hostname} = {
                user => $user,
                nice => $nice,
                system => $system,
                iowait => $iowait,
                steal => $steal,
                idle => $idle,
            };
            <$fh>, <$fh>;
            while (my $line = <$fh>) {
                last if $line !~ /^(dm-|vd)/;
                my ($device, $tps, $rkbps, $wkbps, $kbr, $kbw) = split(/\s+/, $line);
                $iostats->{$hostname}{$device} = {
                    tps => $tps,
                    rkbps => $rkbps,
		    wkbps => $wkbps,
                    kbr => $kbr,
                    kbw => $kbw,
                };
            }
        }
        # Parse iolatency output
        if ($line =~ /^Tracing block I/) {
            <$fh>, <$fh>, <$fh>;
            my $total;
            while (my $line = <$fh>) {
                last if $line =~ /^\s+$/;
                my (undef, $lower, undef, $upper, undef, $count) = split(/\s+/, $line);
                $total += $count;
                $latency->{$hostname}{"$lower:$upper"} = {
                    count => $count,
                };
            }
            for my $boundary (keys %{$latency->{$hostname}}) {
                $latency->{$hostname}{$boundary}{pct} = sprintf('%.2f%%', $latency->{$hostname}{$boundary}{count} / ($total || 1) * 100);
            }
        }
        # Parse dd output
        if ($line =~ /^1024000000 bytes \(1\.0 GB\) copied, \d+(?:\.\d+)? s, (.*)/) {
            if ($writespeed->{$hostname}) {
                $readspeed->{$hostname} = $1;
            }
            else {
                $writespeed->{$hostname} = $1;
            }
        }
    }
}
close($fh);

# Grab hostname, IP and group from inventory files.
my $hostnamemap = {};
opendir(my $dir, 'environments/icds-cas/inventory/') or die $!;
while (my $filename = readdir($dir)) {
    next if $filename =~ /^\./;
    open($fh, '<', 'environments/icds-cas/inventory/' . $filename);
    my $mapping = <$fh>;
    chomp $mapping;
    my $indexes = {};
    my $i = 0;
    for my $key (split(/,/, $mapping)) {
        $indexes->{$key} = $i;
        $i++;
    }
    while (my $line = <$fh>) {
        chomp $line;
        my @vals = split(/,/, $line);
        $hostnamemap->{$vals[$indexes->{'var: hostname'}]} = {
            name => $vals[$indexes->{hostname}],
            ip => $vals[$indexes->{host_address}],
            role => $vals[$indexes->{'group 1'}],
        };
        last unless $vals[0];
    }
    close $fh;
}

print join(',', 'Server Info', (undef,) x 3, 'Load Info', (undef,) x 5, 'Throughput', (undef,), 'IOP Latency (ms)', (undef,) x 19, 'IO Stats', (undef,) x 27) . "\n";

print join(',', ((undef,) x 12), (map { ($_, undef) } qw(
    0:1
    1:2
    2:4
    4:8
    8:16
    16:32
    32:64
    64:128
    128:256
    256:512
)), (map { ($_, undef, undef, undef, undef) } qw( vda vdb vdc dm-0 dm-1 dm-2 dm-3 ))
) . "\n";

print join(',', qw(
    hostname
    ip
    servername
    role
    user
    nice
    system
    iowait
    steal
    idle
    readspeed
    writespeed
), (qw(count pct) x 10),
(qw(tps rkbps wkbps kbr kbw) x 7)) . "\n";

for my $host (keys %$hostnamemap) {
    print join(',',
        $host,
        $hostnamemap->{$host}{ip},
        $hostnamemap->{$host}{name},
        $hostnamemap->{$host}{role},
        @{$loadstats->{$host}}{qw(
            user
            nice
            system
            iowait
            steal
            idle
        )},
        $readspeed->{$host},
        $writespeed->{$host},
        (map { @{$_}{qw(count pct)} }
        @{$latency->{$host}}{qw(
            0:1
            1:2
            2:4
            4:8
            8:16
            16:32
            32:64
            64:128
            128:256
            256:512
        )}),
        (map { @{$_}{qw(tps rkbps wkbps kbr kbw)} }
        @{$iostats->{$host}}{qw(
            vda
            vdb
            vdc
            dm-0
            dm-1
            dm-2
            dm-3
        )}),
    ) . "\n";
}
