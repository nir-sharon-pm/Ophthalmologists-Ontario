"""Collect subspecialty labels for ophthalmologists from university directory pages.

Usage: python3 -I build/subspecialty.py <out.json> [uoft_profiles_dir] [uwo_index.html]
                 [queens_referrals.html] [uottawa_roles.html] [mcgill_faculty.html]
Any argument may be '-' to skip that source. Pages are untrusted input; only
plain text is read. Output: {"<LAST>|<FIRST>": {"subs": [...], "sources": [...]}}
"""
import glob, html, json, os, re, sys, unicodedata

CATS = [
    ('Glaucoma', r'glaucoma'),
    ('Retina', r'retin|vitreo|macul|diabetic eye|vitreous'),
    ('Cornea & external disease', r'cornea|corneal|external disease|ocular surface|dry eye'),
    ('Cataract & refractive', r'cataract|refractive|lasik|anterior segment'),
    ('Pediatrics & strabismus', r'p(a)?ediatric|strabismus|children'),
    ('Neuro-ophthalmology', r'neuro.?ophthalm'),
    ('Oculoplastics & orbit', r'oculoplast|orbit|eyelid|lacrimal|plastic'),
    ('Uveitis', r'uveitis|ocular inflammat'),
    ('Ocular oncology', r'oncolog|tumou?r'),
    ('Comprehensive', r'comprehensive|general ophthalm'),
]

def classify(text):
    t = text.lower()
    return [c for c, rx in CATS if re.search(rx, t)]

def key(first, last):
    def n(s):
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return re.sub(r'[^A-Z]', '', s.upper())
    return n(last) + '|' + n(first.split()[0] if first.split() else '')

def lines_of(path):
    raw = open(path, encoding='utf-8', errors='ignore').read()
    m = re.search(r'<main.*?</main>', raw, re.S)
    raw = m.group(0) if m else raw
    raw = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', '', raw, flags=re.S)
    txt = html.unescape(re.sub(r'<[^>]+>', '\n', raw)).replace('\xa0', ' ')
    return [l.strip() for l in txt.split('\n') if l.strip()]

def split_name(full):
    full = re.sub(r'^(Dr\.?\s*)+|,?\s*(MD|M\.D\.|FRCSC|FRCS\(C\)|PhD|BSc|MSc|MPH|B\.Med|SC).*$', '', full.strip(), flags=re.I)
    full = full.replace('Dr.', '').replace('Dre', '').strip()
    parts = full.split()
    return (parts[0], parts[-1]) if len(parts) >= 2 else ('', '')

out = {}
def add(first, last, subs, src):
    if not first or not last or not subs:
        return
    k = key(first, last)
    e = out.setdefault(k, {'subs': [], 'sources': []})
    for s in subs:
        if s not in e['subs']:
            e['subs'].append(s)
    if src not in e['sources']:
        e['sources'].append(src)

args = sys.argv[1:] + ['-'] * 6
dest, uoft, uwo, queens, uott, mcgill = args[:6]

if uoft != '-':
    for f in sorted(glob.glob(os.path.join(uoft, '*.html'))):
        L = lines_of(f)
        slug = os.path.basename(f)[:-5]
        name = ''
        for i, l in enumerate(L):
            if l.startswith('Ophthalmology & Vision Sciences') and i > 0:
                name = L[i - 1]
                div = l.split(' - ', 1)[1] if ' - ' in l else ''
                break
        else:
            continue
        txt = div
        for h in ('Clinical Interests', 'Research Interests'):
            if h in L:
                j = L.index(h)
                txt += ' ' + ' '.join(L[j + 1:j + 2])
        for l in L:
            if re.match(r'(Clinical )?Fellowship', l):
                txt += ' ' + l
        first, last = split_name(name)
        add(first, last, classify(txt), 'https://ophthalmology.utoronto.ca/faculty/' + slug)

if uwo != '-':
    L = lines_of(uwo)
    for i, l in enumerate(L):
        if l.startswith('Research Interests / Specializations') and i + 1 < len(L):
            nm = L[i - 1] if not re.search(r'MD|FRCS|PhD|BSc', L[i - 1]) else L[i - 2]
            first, last = split_name(nm)
            add(first, last, classify(L[i + 1]), 'https://www.schulich.uwo.ca/ophthalmology/people/faculty/index.html')

if queens != '-':
    L = lines_of(queens)
    labels = r'^(Comprehensive|Oculoplastics|Retina|Medical Retina|Cornea|Oncology|Ocular Oncology|Strabismus|Glaucoma|Medical Glaucoma|Surgical Glaucoma|Pathology|Uveitis|Neuro|Pediatrics|Vision Rehabilitation|Cataract|Anterior segment|Complex Cataracts|Comprehensive \+ Anterior Segment|Medical retina)'
    cur = None
    for l in L:
        m = re.match(r'^Dr\.? ([A-Z][^()]+?)(\s*\(.*\))?$', l)
        if m and len(l) < 60:
            cur = split_name(m.group(1))
            continue
        if cur and re.match(labels + r'\s*$', l):
            add(cur[0], cur[1], classify(l), 'https://ophthalmology.queensu.ca/clinic/referrals')
        elif cur and not re.match(r'^\(', l):
            cur = None   # the doctor's label list ended; ignore section headings that follow

if uott != '-':
    L = lines_of(uott)
    for i, l in enumerate(L[:-1]):
        if re.match(r'^Dr\.? [A-Z]', l) and len(l) < 50:
            first, last = split_name(l[3:].strip())
            add(first, last, classify(L[i + 1]), 'https://www.uottawa.ca/faculty-medicine/ophthalmology/overview/faculty-members-and-roles')

if mcgill != '-':
    L = lines_of(mcgill)
    cur = None
    for i, l in enumerate(L):
        if re.match(r'^Dr\.? ', l) and len(l) < 60:
            cur = split_name(re.sub(r'^(Dr\.?\s*)+', '', l))
        elif l == 'Specialty:' and cur and i + 1 < len(L):
            add(cur[0], cur[1], classify(L[i + 1]), 'https://www.mcgill.ca/ophthalmology/contact-us/faculty')

json.dump(out, open(dest, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'doctors with subspecialty labels')
