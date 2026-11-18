"""Build an Ontario + Québec postal-code -> [lat, lng] table.

Data: the npm package "canada-postal-codes" (Canada Post reference data). Its
binary file is read directly; none of the package's code is run.

  mkdir -p /tmp/pc && cd /tmp/pc && npm pack canada-postal-codes && tar xzf canada-postal-codes-*.tgz
  python3 -I build/postal.py /tmp/pc/package/dist/data /tmp/postal_on_qc.json
"""
import json, struct, sys
d, out = sys.argv[1], sys.argv[2]
provs = json.load(open(d + '/provinces.json'))
meta = json.load(open(d + '/meta.json'))
size = meta['recordSize']
b = open(d + '/postal-codes.bin', 'rb').read()
res = {}
for i in range(0, len(b), size):
    code, pi, tz, ci, lat, lng = struct.unpack('<6sBbHff', b[i:i + size])
    if provs[pi] in ('ON', 'QC'):
        res[code.decode()] = [round(lat, 5), round(lng, 5)]
json.dump(res, open(out, 'w'), separators=(',', ':'))
print(len(res), 'postal codes')
