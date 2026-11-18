"""Build the Glaucoma Referral Map.

Usage: python3 -I build/build.py <build_dir> <out_dir> [date]
Writes <out_dir>/index.html (full page for GitHub Pages) and
<out_dir>/artifact.html (body-only page for the Claude artifact).
Inputs in <build_dir>: template.html, leaflet.css, base.json, geo.json, doctors.json.
"""
import json, sys, datetime
b, out = sys.argv[1], sys.argv[2]
date = sys.argv[3] if len(sys.argv) > 3 else datetime.date.today().isoformat()
t = open(b + '/template.html', encoding='utf-8').read()
g = json.load(open(b + '/geo.json', encoding='utf-8'))
docs = json.load(open(b + '/doctors.json', encoding='utf-8'))
docs.sort(key=lambda d: d['id'])
page = (t.replace('/*LEAFLET_CSS*/', open(b + '/leaflet.css', encoding='utf-8').read())
         .replace('/*BASE*/', open(b + '/base.json', encoding='utf-8').read().strip())
         .replace('/*GAZ*/', json.dumps({'F': g['F'], 'C': g['C']}, separators=(',', ':'), ensure_ascii=False))
         .replace('/*SNAP*/', json.dumps(docs, separators=(',', ':'), ensure_ascii=False))
         .replace('/*DATE*/', date)
         .replace('/*SHARE*/', json.dumps(json.load(open(b + '/share_config.json', encoding='utf-8'))) if __import__('os').path.exists(b + '/share_config.json') else 'null')
         .replace('/*LOG*/', json.dumps(json.load(open(b + '/log_config.json', encoding='utf-8'))) if __import__('os').path.exists(b + '/log_config.json') else 'null'))
open(out + '/artifact.html', 'w', encoding='utf-8').write(page)
full = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        + open(b + '/favicon.html', encoding='utf-8').read().strip() +
        '<title>OphthalFind</title>'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0;font:14px system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>'
        '</head><body>\n' + page + '\n</body></html>\n')
open(out + '/index.html', 'w', encoding='utf-8').write(full)
print('built', len(docs), 'doctors,', date)
