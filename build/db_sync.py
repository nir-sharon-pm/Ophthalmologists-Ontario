"""Plan the database writes that make the artifact's "doctors" collection match doctors.json.

Usage: python3 -I build/db_sync.py <doctors.json> <export_dir> <versions.txt> <out_dir> [YYYY-MM-DD]
  export_dir   : folder written by ArtifactData "list" with out_dir (contains doctors/<id>.json)
  versions.txt : one line per existing document: "<doc_id> <version>" (copied from that listing)
  out_dir      : receives docs/<id>.json and batch_01.json, batch_02.json ... (<= 50 writes each),
                 each a ready-to-use ArtifactData "batch" writes array. The last batch also
                 updates meta/info (pass its current version as META_VERSION env var if it exists).
Prints a summary of added / changed / removed doctors.
"""
import glob, json, os, sys

docs_path, export_dir, versions_path, out_dir = sys.argv[1:5]
date = sys.argv[5] if len(sys.argv) > 5 else ''
want = {d['id']: d for d in json.load(open(docs_path, encoding='utf-8'))}
have = {}
for f in glob.glob(os.path.join(export_dir, '**', '*.json'), recursive=True):
    o = json.load(open(f, encoding='utf-8'))
    if 'locations' not in o and isinstance(o.get('data'), dict):
        o = o['data']
    if isinstance(o, dict) and o.get('id'):
        have[o['id']] = o
versions = {}
for line in open(versions_path, encoding='utf-8'):
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():
        versions[parts[0]] = int(parts[1])

os.makedirs(os.path.join(out_dir, 'docs'), exist_ok=True)
writes, added, changed, removed = [], [], [], []
for i, d in sorted(want.items()):
    if i in have and have[i] == d:
        continue
    fp = os.path.abspath(os.path.join(out_dir, 'docs', i + '.json'))
    json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False)
    w = {'op': 'set', 'collection': 'doctors', 'doc_id': i, 'file_path': fp}
    if i in have:
        if i not in versions:
            sys.exit(f'missing version for existing document {i}')
        w['if_version'] = versions[i]
        changed.append(i)
    else:
        added.append(i)
    writes.append(w)
for i in sorted(set(have) - set(want)):
    if i not in versions:
        sys.exit(f'missing version for existing document {i}')
    writes.append({'op': 'delete', 'collection': 'doctors', 'doc_id': i, 'if_version': versions[i]})
    removed.append(i)

meta_fp = os.path.abspath(os.path.join(out_dir, 'meta.json'))
json.dump({'lastVerified': date, 'count': len(want)}, open(meta_fp, 'w'))
meta = {'op': 'set', 'collection': 'meta', 'doc_id': 'info', 'file_path': meta_fp}
if os.environ.get('META_VERSION'):
    meta['if_version'] = int(os.environ['META_VERSION'])
writes.append(meta)

n = 0
for k in range(0, len(writes), 50):
    n += 1
    json.dump(writes[k:k + 50], open(os.path.join(out_dir, f'batch_{n:02d}.json'), 'w'))
print(f'{len(added)} added, {len(changed)} changed, {len(removed)} removed -> {n} batch file(s) in {out_dir}')
for label, ids in (('added', added), ('changed', changed), ('removed', removed)):
    if ids:
        print(label + ':', ', '.join(ids[:60]) + (' …' if len(ids) > 60 else ''))
