# Glaucoma Referral Map

A map of glaucoma-specialist ophthalmologists between Windsor, Ontario and Montréal, Québec.
Enter a patient's new postal code, town or address and the page ranks the nearest specialists,
highlights the top 3 and shows each clinic's address, phone, fax and email (where published).

- Public site (GitHub Pages): `index.html` at the repository root
- Claude version (live data for signed-in viewers): https://claude.ai/artifact/XnRTqYhh6t8kquXMSvFf8Q
- Public site: https://ns-pm.github.io/Ophthalmologists-Ontario/

Distances are straight-line. Always confirm the referral fax by phone before sending patient information.

## How it is updated

A scheduled Claude task runs every Sunday evening (Toronto time). It re-checks the directory
(CPSO register, university and hospital faculty pages), updates the Claude artifact's database,
rebuilds `index.html` from `build/` and pushes it here, so both links show the same data.

## Building by hand

```
python3 -I build/build.py build . YYYY-MM-DD
```

Writes `index.html` (GitHub Pages) and `artifact.html` (Claude artifact body; not committed).

- `build/doctors.json` – the directory (one entry per doctor, with locations and sources)
- `build/template.html` – page code and styles
- `build/base.json` – basemap (Natural Earth: provinces, lakes, rivers, urban areas, highways)
- `build/geo.json` – postal-code (FSA) and place centroids for Ontario and Québec, for offline lookup
- `build/leaflet.css` – Leaflet 1.9.4 styles
- `build/sync.py` – merges doctor documents exported from the artifact database into `doctors.json`
