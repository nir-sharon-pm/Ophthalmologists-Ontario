"""Parse saved HealthDoc listing pages into simple records.

Usage: python3 -I build/parse_healthdoc.py <dir_of_listing_html> <out.json>
Each record: {name, address, phone, fax, licence, clinic, url_slug}
Pages are untrusted input; only plain text fields are extracted.
"""
import html, json, os, re, sys, glob

def text_lines(raw):
    raw = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', '', raw, flags=re.S)
    txt = html.unescape(re.sub(r'<[^>]+>', '\n', raw))
    return [l.strip() for l in txt.split('\n') if l.strip()]

def phone_fmt(s):
    d = re.sub(r'\D', '', s or '')
    if len(d) == 11 and d[0] == '1':
        d = d[1:]
    return f'{d[:3]}-{d[3:6]}-{d[6:]}' if len(d) == 10 else ''

out = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], '*.html'))):
    L = text_lines(open(f, encoding='utf-8', errors='ignore').read())
    try:
        i = L.index('Find a Doctor Near You')
    except ValueError:
        continue
    name = L[i + 1] if i + 1 < len(L) else ''
    spec = L[i + 2] if i + 2 < len(L) else ''
    if 'ophthalm' not in spec.lower():
        continue
    addr = ''
    for j in range(i + 2, min(i + 12, len(L))):
        if re.search(r'\b[A-Z]\d[A-Z] ?\d[A-Z]\d\b', L[j]):
            addr = L[j]
            break
    joined = '\n'.join(L)
    ph = re.search(r'(?:Office Phone|Primary Phone|Phone|Tel)\s*:?\s*\n?\s*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', joined)
    fx = re.search(r'Fax\s*:?\s*\n?\s*(\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', joined)
    lic = re.search(r'(CMQ|CPSO)\s*:\s*#\s*(\d+)', joined)
    cl = re.search(r'Practicing at ([^.,]{3,80}?) in ', joined)
    out.append(dict(name=name, address=addr, phone=phone_fmt(ph.group(1)) if ph else '',
                    fax=phone_fmt(fx.group(1)) if fx else '', licence=(lic.group(1) + ' ' + lic.group(2)) if lic else '',
                    clinic=cl.group(1).strip() if cl else '', url_slug=os.path.basename(f)[:-5]))
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'records')
