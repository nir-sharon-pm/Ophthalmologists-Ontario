// List active ophthalmologists on the CPSO public register, city by city,
// using the register's own search form (one search at a time, with pauses).
// Usage: node build/cpso_list.js <cities.json> <out.json>
// cities.json: array of city names exactly as in the register's City/Town list.
// Output: [{cpso, name, specialties, location, status, url, cities:[...]}]
const { chromium } = require('playwright');
const fs = require('fs');

const cities = JSON.parse(fs.readFileSync(process.argv[2]));
const outPath = process.argv[3];
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function openResultsPage(p) {
  await p.goto('https://register.cpso.on.ca/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await p.fill('#lastName', 'Sharon');
  await p.click('#searchForm button[type=submit], #searchForm input[type=submit]');
  await p.waitForSelector('table tbody tr td', { timeout: 60000 });
}

async function readRows(p) {
  return p.$$eval('table tbody tr', trs => trs.map(tr => {
    const tds = [...tr.querySelectorAll('td')].map(td => td.innerText.replace(/\s+/g, ' ').trim());
    const a = tr.querySelector('a');
    return { tds, url: a ? a.href : '' };
  }));
}

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await openResultsPage(p);
  const all = fs.existsSync(outPath) ? new Map(JSON.parse(fs.readFileSync(outPath)).map(d => [d.cpso, d])) : new Map();
  let i = 0;
  for (const city of cities) {
    i++;
    try {
      await p.evaluate(c => {
        const f = document.getElementById('searchForm');
        ['lastName', 'firstName'].forEach(n => { const el = f.querySelector('[name=' + n + ']'); if (el) el.value = ''; });
        const inc = document.getElementById('cbx-includeinactive'); if (inc) inc.checked = false;
        const lang = document.getElementById('language');
        if (lang) { [...lang.options].forEach(o => { o.selected = false; }); lang.dispatchEvent(new Event('change', { bubbles: true })); }
        const lh = document.getElementById('languageSelectedHidden'); if (lh) lh.value = '';
        const s = document.getElementById('SpecialistType'); s.value = 'Ophthalmology';
        const cd = document.getElementById('cityDropDown'); cd.value = c;
        [s, cd].forEach(x => x.dispatchEvent(new Event('change', { bubbles: true })));
        f.querySelector('button.search-button').click();
      }, city);
      await sleep(8000);
      let seenFirst = '';
      for (let page = 1; page < 60; page++) {
        const rows = await readRows(p);
        const first = rows[0] ? rows[0].tds.join('|') : '';
        if (page > 1 && first === seenFirst) break;
        seenFirst = first;
        for (const r of rows) {
          const m = r.url.match(/cpsonum=(\d+)/);
          if (!m || r.tds.length < 4) continue;
          const prev = all.get(m[1]);
          const rec = prev || { cpso: m[1], name: r.tds[0], specialties: r.tds[2], location: r.tds[3], status: r.tds[4] || '', url: r.url, cities: [] };
          if (!rec.cities.includes(city)) rec.cities.push(city);
          all.set(m[1], rec);
        }
        const next = p.locator('a.page-select-link', { hasText: 'Next page' });
        if (!(await next.count())) break;
        await next.first().click();
        await sleep(1500);
      }
      console.error(i + '/' + cities.length, city, 'total', all.size);
    } catch (e) {
      console.error(city, 'ERR', e.message.slice(0, 80));
      await openResultsPage(p).catch(() => {});
    }
    if (i % 10 === 0) fs.writeFileSync(outPath, JSON.stringify([...all.values()], null, 1));
    await sleep(1500);
  }
  fs.writeFileSync(outPath, JSON.stringify([...all.values()], null, 1));
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
