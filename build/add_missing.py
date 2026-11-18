"""Add doctors found in HealthDoc's CPSO-verified Ontario lists but missed by the
register's town search to the CPSO list, so cpso_details.js looks them up by licence number.
Usage: python3 -I build/add_missing.py <on_hd.json> <cpso_list.json>
"""
import json, sys
hd = json.load(open(sys.argv[1], encoding='utf-8'))
lst = json.load(open(sys.argv[2], encoding='utf-8'))
have = {x['cpso'] for x in lst}
n = 0
for x in hd:
    if not x.get('licence', '').startswith('CPSO'):
        continue
    num = x['licence'].split()[-1]
    if num in have:
        continue
    lst.append({'cpso': num, 'name': x['name'], 'specialties': 'Ophthalmology', 'location': x['address'],
                'status': '', 'url': '', 'cities': ['healthdoc']})
    have.add(num)
    n += 1
json.dump(lst, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('added', n, 'doctors; list now', len(lst))
