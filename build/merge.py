"""Merge all sources into build/doctors.json.

Usage:
  python3 -I build/merge.py --curated build/doctors.json --cpso-list L.json --cpso-details D.json \
      --postal postal_on_qc.json --subs subs.json --cos cos.json --hd-mtl mtl_hd.json \
      --mcgill mcgill_faculty.html --out build/doctors.json

- Ontario doctors and practice locations: CPSO register (active licences only).
- Montréal: McGill faculty directory and CMQ-verified HealthDoc listings.
- Subspecialties: curated list, university faculty pages (subs.json) and the COS directory.
- Curated entries (hand-checked) keep their notes, sources and contacts; register
  locations they don't already list are added.
Only locations between Windsor and Montréal are kept.
"""
import argparse, html, json, re, unicodedata

ap = argparse.ArgumentParser()
for a in ('curated', 'cpso-list', 'cpso-details', 'postal', 'subs', 'cos', 'hd-mtl', 'mcgill', 'out'):
    ap.add_argument('--' + a, default='')
A = ap.parse_args()
load = lambda p, d: json.load(open(p, encoding='utf-8')) if p else d

POSTAL = load(A.postal, {})            # "K1H8L6": [lat, lng]
def coords(pc):
    pc = re.sub(r'\s', '', (pc or '').upper())
    return POSTAL.get(pc)

def in_corridor(lat, lng):
    return 41.6 < lat < 45.75 and -83.3 < lng < -73.3

def fold(s):
    s = unicodedata.normalize('NFD', s or '')
    return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')

def letters(s):
    return re.sub(r'[^A-Z]', '', fold(s).upper())

def keyof(first, last):
    return letters(last) + '|' + letters((first or '').split()[0] if (first or '').split() else '')

def phone_fmt(s):
    s = s or ''
    ext = ''
    m = re.search(r'(?:ext\.?|extension|x)\s*:?\s*(\d+)', s, re.I)
    if m:
        ext = ' ext. ' + m.group(1)
        s = s[:m.start()]
    d = re.sub(r'\D', '', s)
    if len(d) == 11 and d[0] == '1':
        d = d[1:]
    return (f'{d[:3]}-{d[3:6]}-{d[6:]}' + ext) if len(d) == 10 else ''

PC_RX = r'([A-Z]\d[A-Z])\s?(\d[A-Z]\d)'
def split_address(lines):
    """CPSO address lines -> (clinic, street, city, prov, postal)."""
    lines = [l.strip() for l in lines if l.strip()]
    last = lines[-1] if lines else ''
    m = re.search(r'^(.*?)\s+(Ontario|ON|Quebec|QC|Québec)\s+' + PC_RX + r'\s*$', last, re.I)
    city, prov, pc = '', 'ON', ''
    if m:
        city = m.group(1).strip().rstrip(',')
        prov = 'QC' if m.group(2).upper().startswith('Q') else 'ON'
        pc = (m.group(3) + ' ' + m.group(4)).upper()
        lines = lines[:-1]
    else:
        m2 = re.search(PC_RX, ' '.join(lines).upper())
        if m2:
            pc = m2.group(1) + ' ' + m2.group(2)
    street, clinic = [], []
    for l in lines:
        if re.match(r'^(PO Box|P\.O\.|Box )', l, re.I):
            continue
        if re.search(r'\d', l) and not clinic and not street and re.match(r'^[A-Za-z].*(Hospital|Health|Centre|Center|Clinic|Institute)', l):
            clinic.append(l)
        elif re.search(r'^\s*(Suite|Unit|Room|Rm|#|\d)', l, re.I) or re.search(r'\d+\s+\w+\s+(St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Pkwy|Parkway|Cres|Way|Lane|Line|Hwy|Court|Ct|Place|Pl|Circle)\b', l, re.I):
            street.append(l)
        else:
            clinic.append(l)
    return '; '.join(clinic[:2]), ', '.join(street), city, prov, pc

def title_name(raw):
    raw = re.sub(r'Former Name:.*$', '', raw).strip()
    raw = re.sub(r'^(Dr\.?\s+)+', '', raw)
    if ',' in raw:
        last, first = [x.strip() for x in raw.split(',', 1)]
    else:
        parts = raw.split()
        first, last = ' '.join(parts[:-1]), parts[-1] if parts else ''
    cap = lambda s: ' '.join(w if not w.isupper() else w.title() for w in s.split())
    first_given = first.split()[0] if first.split() else ''
    return cap(first), cap(last), f'Dr. {cap(first_given)} {cap(last)}'.strip()

def slug(first, last):
    s = fold(last + '-' + (first.split()[0] if first.split() else '')).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

# ---------- subspecialties ----------
COS_MAP = {
    'Anterior Segment': 'Cataract & refractive', 'Cataract/IOL': 'Cataract & refractive', 'Refractive Surgery': 'Cataract & refractive',
    'Cornea/External Disease': 'Cornea & external disease', 'Contact Lenses': 'Cornea & external disease', 'Conjunctivitis': 'Cornea & external disease',
    'Glaucoma': 'Glaucoma', 'General Ophthalmology': 'Comprehensive', 'Medical Retina': 'Retina', 'Retina Vitreous': 'Retina',
    'Neuro-ophthalmology': 'Neuro-ophthalmology', 'Ocular Oncology': 'Ocular oncology', 'Pediatric Ophthalmology': 'Pediatrics & strabismus',
    'Strabismus': 'Pediatrics & strabismus', 'Plastic Reconstructive Surgery': 'Oculoplastics & orbit', 'Uveitis': 'Uveitis', 'Immunology': 'Uveitis',
}
SUBS = {}
def add_sub(k, subs, src=None):
    e = SUBS.setdefault(k, {'subs': [], 'sources': []})
    for s in subs:
        if s and s not in e['subs']:
            e['subs'].append(s)
    if src and src not in e['sources']:
        e['sources'].append(src)
for k, v in load(A.subs, {}).items():
    add_sub(k, v['subs'], (v.get('sources') or [None])[0])
COS_URL = 'https://cos.imiscloud.com/COS_Member_Portal/COS-Member-Portal/Find-an-Ophthalmologist.aspx'
for r in load(A.cos, []):
    if len(r) < 13 or r[8] not in ('ON', 'QC', 'Ontario', 'Quebec'):
        continue
    last, _, first = r[12].partition(',')
    add_sub(keyof(first.strip(), last.strip()), [COS_MAP.get(r[0], '')], COS_URL)

def sub_key(first, last):
    """Match on any given name (many doctors go by a middle name), and on any part of a compound last name."""
    lasts = [last] + [p for p in re.split(r'[\s-]+', last) if p and p != last]
    for g in (first or '').split() or ['']:
        for l in lasts:
            k = keyof(g, l)
            if k in SUBS:
                return k, g
    return keyof(first, last), ''

def subs_for(first, last, extra=()):
    k, _ = sub_key(first, last)
    e = SUBS.get(k, {'subs': [], 'sources': []})
    ordered = []
    for s in list(extra) + e['subs']:
        if s and s not in ordered:
            ordered.append(s)
    return ordered, e['sources']

# ---------- curated ----------
curated = {d['id']: d for d in load(A.curated, [])}
cur_by_key = {}
for d in curated.values():
    nm = re.sub(r'^Dr\.?\s*', '', d['name']).replace('(Gary)', '').split()
    if len(nm) >= 2:
        cur_by_key[keyof(nm[0], nm[-1])] = d['id']
def curated_match(first, last):
    k = keyof(first, last)
    if k in cur_by_key:
        return cur_by_key[k]
    f = letters(first.split()[0] if first.split() else '')
    toks = [letters(t) for t in re.split(r'[\s-]+', last) if t]
    for ck, cid in cur_by_key.items():
        cl, cf = ck.split('|')
        if cf == f and (cl in toks or cl == letters(last)):
            return cid
    return None

out = {}
def postals(d):
    return {m.group(1) + m.group(2) for l in d['locations'] for m in [re.search(PC_RX, l.get('address', '').upper())] if m}

# ---------- Ontario (CPSO) ----------
details = load(A.cpso_details, {})
listed = {d['cpso']: d for d in load(A.cpso_list, [])}
for cpso, det in details.items():
    if listed and cpso not in listed:
        continue  # no longer found in the register sweep
    if not str(det.get('status', '')).startswith('ACTIVE') and 'ACTIVE' not in str(listed.get(cpso, {}).get('status', '')):
        continue
    first, last, display = title_name(det.get('name') or listed.get(cpso, {}).get('name', ''))
    if not last:
        continue
    locs = []
    for L in det.get('locations', []):
        clinic, street, city, prov, pc = split_address(L.get('address', []))
        c = coords(pc)
        if not c or not in_corridor(*c):
            continue
        city = city.title() if city.isupper() else city
        addr = ', '.join(x for x in [street, f'{city}, {prov} {pc}'.strip(', ')] if x)
        locs.append(dict(clinic=clinic, address=addr, city=city or '', lat=round(c[0], 5), lng=round(c[1], 5),
                         phone=phone_fmt(L.get('phone')), fax=phone_fmt(L.get('fax')), email=(L.get('email') or '').strip()))
    # the same place often appears both as a practice location and as a corporation address:
    # keep the first (practice entries come first and carry the fax)
    seen_pc, uniq = set(), []
    for l in locs:
        m = re.search(PC_RX, l['address'].upper())
        k = (m.group(1) + m.group(2)) if m else l['address']
        if k in seen_pc:
            continue
        seen_pc.add(k)
        uniq.append(l)
    locs = uniq
    if not locs:
        continue
    cid = curated_match(first, last)
    src = 'https://register.cpso.on.ca/physician-info/?cpsonum=' + cpso
    if cid:
        d = json.loads(json.dumps(curated[cid]))
        have = postals(d)
        for l in locs:
            m = re.search(PC_RX, l['address'].upper())
            if m and (m.group(1) + m.group(2)) not in have:
                d['locations'].append(l)
                have.add(m.group(1) + m.group(2))
        subs, ssrc = subs_for(first, last, ['Glaucoma'] if d.get('tier') == 'specialist' else [])
        d['subs'] = subs or (['Glaucoma'] if d.get('tier') == 'specialist' else [])
        if src not in d['sources']:
            d['sources'].append(src)
        d['cpso'] = cpso
        out[d['id']] = d
        continue
    subs, ssrc = subs_for(first, last)
    _, used = sub_key(first, last)
    if used and first.split() and used != first.split()[0]:
        g = first.split()
        display = f'Dr. {" ".join(g[:g.index(used) + 1])} {last}'   # e.g. Dr. Christine Maya Tong (goes by Maya)
    did = slug(first, last)
    if did in out or did in curated:
        did += '-' + cpso
    out[did] = dict(id=did, name=display, legal=f'{first} {last}', focus=', '.join(subs) if subs else 'Ophthalmology', subs=subs, tier='',
                    sources=[src] + ssrc[:2], note='', cpso=cpso, locations=locs)

# curated entries not matched on the register (e.g. Québec) are kept as they are
for cid, d in curated.items():
    if cid in out or any(o.get('id') == cid for o in out.values()):
        continue
    nm = re.sub(r'^Dr\.?\s*', '', d['name']).replace('(Gary)', '').split()
    subs, _ = subs_for(nm[0], nm[-1], ['Glaucoma'] if d.get('tier') == 'specialist' else [])
    d = json.loads(json.dumps(d))
    d['subs'] = subs or (['Glaucoma'] if d.get('tier') == 'specialist' else [])
    out[cid] = d

# ---------- Montréal: McGill faculty + HealthDoc (CMQ verified) ----------
def mcgill_records(path):
    if not path:
        return []
    raw = open(path, encoding='utf-8', errors='ignore').read()
    raw = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', '', raw, flags=re.S)
    L = [l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '\n', raw)).split('\n') if l.strip()]
    recs, cur = [], None
    for l in L:
        if re.match(r'^Dr\.? ', l) and len(l) < 70:
            if cur:
                recs.append(cur)
            cur = {'name': re.sub(r'^(Dr\.?\s*)+', '', l).split(',')[0].strip(), 'lines': []}
        elif cur is not None:
            cur['lines'].append(l)
    if cur:
        recs.append(cur)
    res = []
    for r in recs:
        txt = '\n'.join(r['lines'][:16])
        pc = re.search(PC_RX, txt.upper())
        tel = re.search(r'Tel\.?:\s*([^\n]+)', txt)
        fax = re.search(r'Fax:\s*([^\n]+)', txt)
        spec = re.search(r'Specialty:\n([^\n]+)', txt)
        em = re.search(r'([\w.+-]+)\n\[at\]\n([\w.-]+\.\w+)', txt)
        addr_lines = []
        for l in r['lines'][1:8]:
            if l.startswith(('Specialty', 'Tel', 'Fax', 'Web page', 'Email')) or l == '[at]':
                break
            addr_lines.append(l)
        res.append(dict(name=r['name'], lines=addr_lines, postal=(pc.group(1) + ' ' + pc.group(2)) if pc else '',
                        tel=tel.group(1) if tel else '', fax=fax.group(1) if fax else '', spec=spec.group(1) if spec else '',
                        email=(em.group(1) + '@' + em.group(2)) if em else ''))
    return res

MG_URL = 'https://www.mcgill.ca/ophthalmology/contact-us/faculty'
mtl = {}
for r in mcgill_records(A.mcgill):
    parts = r['name'].split()
    if len(parts) < 2 or not r['postal']:
        continue
    c = coords(r['postal'])
    if not c or not in_corridor(*c):
        continue
    first, last = parts[0], parts[-1]
    clinic = r['lines'][0] if r['lines'] else ''
    addr = ', '.join(r['lines'][1:] if len(r['lines']) > 1 else r['lines'])
    mtl[keyof(first, last)] = dict(first=first, last=last, name=f'Dr. {first} {last}', src=MG_URL,
        loc=dict(clinic=clinic, address=addr or clinic, city='Montréal', lat=round(c[0], 5), lng=round(c[1], 5),
                 phone=phone_fmt(r['tel']), fax=phone_fmt(r['fax']), email=r['email']))
for r in load(A.hd_mtl, []):
    nm = re.sub(r'^Dr\.?\s*', '', r['name']).split()
    if len(nm) < 2:
        continue
    first, last = nm[0], nm[-1]
    m = re.search(PC_RX, r['address'].upper())
    c = coords(m.group(1) + m.group(2)) if m else None
    if not c or not in_corridor(*c):
        continue
    k = keyof(first, last)
    if k in mtl:
        loc = mtl[k]['loc']
        loc['phone'] = loc['phone'] or r['phone']
        loc['fax'] = loc['fax'] or r['fax']
        continue
    city = r['address'].split(',')[-2].strip() if r['address'].count(',') >= 2 else 'Montréal'
    mtl[k] = dict(first=first, last=last, name=f'Dr. {first} {" ".join(nm[1:])}', src='https://www.healthdoc.ca/listing/' + r['url_slug'],
                  loc=dict(clinic=r['clinic'] or r['address'].split(',')[0], address=r['address'], city=city, lat=round(c[0], 5), lng=round(c[1], 5),
                           phone=r['phone'], fax=r['fax'], email=''))
for k, m in mtl.items():
    cid = curated_match(m['first'], m['last'])
    if cid and cid in out:
        continue
    subs, ssrc = subs_for(m['first'], m['last'])
    did = slug(m['first'], m['last'])
    if did in out:
        continue
    out[did] = dict(id=did, name=m['name'], focus=', '.join(subs) if subs else 'Ophthalmology', subs=subs, tier='',
                    sources=[m['src']] + ssrc[:2], note='', locations=[m['loc']])

# link CPSO sources to the doctor's own register page, not the register's home page
for d in out.values():
    if d.get('cpso'):
        spec = 'https://register.cpso.on.ca/physician-info/?cpsonum=' + d['cpso']
        srcs = [s for s in d.get('sources', []) if s.rstrip('/') != 'https://register.cpso.on.ca']
        if spec not in srcs:
            srcs.insert(0, spec)
        d['sources'] = srcs
docs = sorted(out.values(), key=lambda d: d['id'])
json.dump(docs, open(A.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print(len(docs), 'doctors;', sum(len(d['locations']) for d in docs), 'locations')
print(Counter(s for d in docs for s in (d['subs'] or ['(not listed)'])).most_common())
print(Counter(l['city'] for d in docs for l in d['locations']).most_common(25))
