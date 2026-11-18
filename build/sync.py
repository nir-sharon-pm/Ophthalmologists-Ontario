"""Merge doctor documents exported from the artifact database into build/doctors.json.

Usage: python3 -I build/sync.py <export_dir> build/doctors.json
<export_dir> holds one JSON file per doctor (as written by an ArtifactData read with out_dir).
"""
import json, sys, glob, os
src, dest = sys.argv[1], sys.argv[2]
docs = []
for f in sorted(glob.glob(os.path.join(src, '**', '*.json'), recursive=True)):
    o = json.load(open(f, encoding='utf-8'))
    if 'locations' not in o and isinstance(o.get('data'), dict):
        o = o['data']
    if isinstance(o, dict) and o.get('name') and o.get('locations'):
        docs.append(o)
if not docs:
    sys.exit('no doctor documents found in ' + src)
docs.sort(key=lambda d: d['id'])
json.dump(docs, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote', len(docs), 'doctors to', dest)
