#!/usr/bin/env bash
# Download the public directory pages used by subspecialty.py and merge.py.
# Usage: bash build/fetch_sources.sh <dir>
# Pages are saved as-is and treated as untrusted data by the parsers.
set -u
D="$1"; mkdir -p "$D/uoft/prof" "$D/hd/mtl"
get() { curl -sL -m 30 --retry 2 -o "$2" "$1" || echo "failed: $1" >&2; }
# University of Toronto faculty directory and profiles
for i in $(seq 0 25); do get "https://ophthalmology.utoronto.ca/faculty-directory?page=$i" "$D/uoft/p$i.html"; done
grep -oh 'href="/faculty/[^"]*"' "$D"/uoft/p*.html | sed 's#href="/faculty/##;s/"//' | sort -u > "$D/uoft/slugs.txt"
while read -r s; do get "https://ophthalmology.utoronto.ca/faculty/$s" "$D/uoft/prof/$s.html"; sleep 0.3; done < "$D/uoft/slugs.txt"
# Other faculty lists
get https://www.schulich.uwo.ca/ophthalmology/people/faculty/index.html "$D/uwo.html"
get https://ophthalmology.queensu.ca/clinic/referrals "$D/queens.html"
get https://www.uottawa.ca/faculty-medicine/ophthalmology/overview/faculty-members-and-roles "$D/uottawa.html"
get https://www.mcgill.ca/ophthalmology/contact-us/faculty "$D/mcgill.html"
# Montreal ophthalmologists (CMQ-verified HealthDoc listings)
get "https://www.healthdoc.ca/find/qc/montreal-metropolitan-community/ophthalmologist" "$D/hd/list1.html"
for pg in 2 3 4 5; do get "https://www.healthdoc.ca/find/qc/montreal-metropolitan-community/ophthalmologist?pg=$pg" "$D/hd/list$pg.html"; done
grep -oh 'href="https://www.healthdoc.ca/listing/[^"]*"' "$D"/hd/list*.html | sed 's/.*href="//;s/"//' | sort -u > "$D/hd/urls.txt"
while read -r u; do get "$u" "$D/hd/mtl/$(basename "$u").html"; sleep 0.3; done < "$D/hd/urls.txt"
echo "done: $(ls "$D/uoft/prof" | wc -l) U of T profiles, $(ls "$D/hd/mtl" | wc -l) Montreal listings"
