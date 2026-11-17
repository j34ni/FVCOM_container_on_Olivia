#!/bin/sh
# usage: sh medians.sh   (dans le dossier des .out sur Olivia)
for f in fvcal-1n-2681304.out fvcal-2n-2681487.out; do
echo "== $f"
grep -E '^[[:space:]]*![[:space:]]+[0-9]{7}[[:space:]]' "$f" > /tmp/med.t
head -2 /tmp/med.t
echo "n=$(wc -l < /tmp/med.t)"
for col in 5 6 7; do
awk -v c="$col" '{print $c}' /tmp/med.t | tail -n +21 | sort -n | awk -v c="$col" '{a[NR]=$1} END{printf "col%d median %s n=%d\n", c, a[int(NR/2)], NR}'
done
done
