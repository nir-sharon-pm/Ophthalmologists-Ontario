#!/usr/bin/env bash
# Rebuild the directory from public sources. Run from the repository root:
#   bash build/weekly.sh YYYY-MM-DD
# Produces build/doctors.json, index.html and artifact.html, and refreshes build/data/.
# Takes 2-3 hours (the CPSO register is read one search at a time, with pauses).
set -eu
DATE="${1:?date}"
T="$(mktemp -d)"
echo "work dir: $T"

# 1. Postal-code coordinates (Canada Post reference data from the npm registry; data only, no code run)
(cd "$T" && npm pack canada-postal-codes >/dev/null 2>&1 && tar xzf canada-postal-codes-*.tgz)
python3 -I build/postal.py "$T/package/dist/data" "$T/postal.json"

# 2. Public directory pages (faculty lists, Montreal and Ontario HealthDoc listings)
bash build/fetch_sources.sh "$T/src"
python3 -I build/parse_healthdoc.py "$T/src/hd/mtl" "$T/mtl_hd.json"
python3 -I build/parse_healthdoc.py "$T/src/hd/on" "$T/on_hd.json"

# 3. Ontario: CPSO register by 3-character postal area (the register returns at most 100 results per
#    search, so postal areas keep each search small), plus licence lookups for anyone still missed
node build/cpso_list.js build/data/fsas.json "$T/cpso_list.json"
python3 -I build/add_missing.py "$T/on_hd.json" "$T/cpso_list.json"
cp "$T/cpso_list.json" build/data/cpso_list.json
#    details older than 28 days are refreshed (about a quarter each week); new doctors always
node build/cpso_details.js build/data/cpso_list.json build/data/cpso_details.json 28

# 4. Subspecialties
node build/cos_list.js "$T/cos.json"
python3 -I build/subspecialty.py "$T/subs.json" "$T/src/uoft/prof" "$T/src/uwo.html" "$T/src/queens.html" "$T/src/uottawa.html" "$T/src/mcgill.html"

# 5. Merge and build
python3 -I build/merge.py --curated build/curated.json --cpso-list build/data/cpso_list.json \
  --cpso-details build/data/cpso_details.json --postal "$T/postal.json" --subs "$T/subs.json" \
  --cos "$T/cos.json" --hd-mtl "$T/mtl_hd.json" --mcgill "$T/src/mcgill.html" --out build/doctors.json
python3 -I build/build.py build . "$DATE"
echo "weekly build done"
