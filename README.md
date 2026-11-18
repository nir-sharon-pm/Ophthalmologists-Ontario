# OphthalFind

A map of ophthalmologists between Windsor, Ontario and Montréal, Québec, for referring a patient
who has moved. Enter the patient's new postal code, town or address (or a doctor's name); the page
ranks the nearest doctors, highlights the top 3, and shows each clinic's address, phone, fax and
email where published. Filter by city and subspecialty (Glaucoma by default).

- Public site (GitHub Pages): https://ns-pm.github.io/Ophthalmologists-Ontario/ (`index.html`)
- Claude version: https://claude.ai/artifact/XnRTqYhh6t8kquXMSvFf8Q

Distances are straight-line. Always confirm the referral fax by phone before sending patient information.

## Sources

- Ontario doctors and practice locations: CPSO public register (active licences only).
- Montréal: McGill Department of Ophthalmology faculty list and CMQ-verified HealthDoc listings.
- Subspecialties: Canadian Ophthalmological Society directory and university faculty pages
  (Toronto, Western, Queen's, Ottawa, McGill). "Subspecialty not listed" means none was published.
- Hand-checked entries (mostly glaucoma specialists) in `build/curated.json` take priority.

## How it is updated

A scheduled Claude task runs every Sunday evening (Toronto time). It runs `build/weekly.sh`, which
re-reads the sources and rebuilds `index.html`, commits it here, and republishes the Claude version,
so both links show the same data.

```
bash build/weekly.sh YYYY-MM-DD     # full rebuild, 2-3 hours
python3 -I build/build.py build . YYYY-MM-DD   # rebuild the page from build/doctors.json only
```

Files in `build/`: `template.html` (page), `base.json` (basemap, Natural Earth), `geo.json`
(postal-code and place centroids for offline lookup), `leaflet.css`, the source readers
(`cpso_list.js`, `cpso_details.js`, `cos_list.js`, `fetch_sources.sh`, `parse_healthdoc.py`,
`subspecialty.py`, `add_missing.py`, `postal.py`), `merge.py`, and `data/` (register snapshots).
