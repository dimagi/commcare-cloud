#!/usr/bin/env bash

# example usage
# ./scripts/archive_dbs.sh dbs +2d
# to archive all dbs in the dbs/ directory that haven't been accessed for more than 2 days


dir=${1}
mtime=${2}


if [ $(echo $mtime | cut -c1) = "+" ]
then
    # linux doesn't support -{a,m}time with [smhd] units,
    # but I'd like it to be very easy to play around with +10m / +1h / +1d
    # so I'd like to emulate a subset of the freebsd behavior
    # and I want it to work the same way on freebsd (mac) and linux.
    # This is ugly but reasonably straight-foward and it works
    unit=$(echo $mtime | cut -c2- | grep -o '.$')
    number=$(echo $mtime | cut -c2- | grep -o '[0-9]*')
    case $unit in
    m)
        time_suffix="min +${number}"
        ;;
    h)
        time_suffix="min +$((${number} * 60))"
        ;;
    d)
        time_suffix="time +${number}"
        ;;
    *)
        echo >&2 "mtime must have a time unit in [mhd]: ${mtime}"
        ;;
    esac
else
    echo >&2 "mtime must start with +: ${mtime}"
    exit 1
fi

test -d ${dir} || {
    echo >&2 "dir must be a directory: ${dir}"
    exit 1
}

echo "find ${dir} -name '*.db' -type f -m${time_suffix}"

while read line
do
    db="${line}"
    lock="${line}.lock"
    gz="${line}.gz"

    if [ -f ${lock} ]
    then
        echo >&2 "skipping due to ${lock}"
        continue
    fi

    touch ${lock}
    gzip ${db}
    rm ${lock}
done < <(find ${dir} -name '*.db' -type f -m${time_suffix})
