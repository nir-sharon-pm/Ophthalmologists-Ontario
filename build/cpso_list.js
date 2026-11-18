// List active ophthalmologists on the CPSO public register, city by city,
// using the register's own search form (one search at a time, with pauses).
// Usage: node build/cpso_list.js <cities.json> <out.json>
// cities.json: array of city names exactly as in the register's City/Town list, and/or
//   "last:<prefix>" entries to search by last-name prefix across all of Ontario.
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
  let b = await chromium.launch();
  let p = await b.newPage();
  await openResultsPage(p);
  const all = fs.existsSync(outPath) ? new Map(JSON.parse(fs.readFileSync(outPath)).map(d => [d.cpso, d])) : new Map();
  let i = 0;
  for (const city of cities) {
    i++;
    try {
      const before = await p.$$eval('table tbody tr', trs => trs.map(tr => tr.innerText).join('|')).catch(() => '');
      // the page fetches results itself after the form is submitted; wait for that reply
      const reply = p.waitForResponse(r => r.url().includes('Get-Search-Results'), { timeout: 45000 }).catch(() => null);
      await p.evaluate(c => {
        const f = document.getElementById('searchForm');
        ['lastName', 'firstName'].forEach(n => { const el = f.querySelector('[name=' + n + ']'); if (el) el.value = ''; });
        const inc = document.getElementById('cbx-includeinactive'); if (inc) inc.checked = false;
        const lang = document.getElementById('language');
        if (lang) { [...lang.options].forEach(o => { o.selected = false; }); lang.dispatchEvent(new Event('change', { bubbles: true })); }
        const lh = document.getElementById('languageSelectedHidden'); if (lh) lh.value = '';
        const s = document.getElementById('SpecialistType'); s.value = 'Ophthalmology';
        const cd = document.getElementById('cityDropDown');
        const pcf = f.querySelector('[name=postalCode]'); if (pcf) pcf.value = '';
        if (c.startsWith('last:')) { cd.value = '-1'; f.querySelector('[name=lastName]').value = c.slice(5); }
        else if (c.startsWith('pc:')) { cd.value = '-1'; if (pcf) pcf.value = c.slice(3); }
        else cd.value = c;
        [s, cd].forEach(x => x.dispatchEvent(new Event('change', { bubbles: true })));
        f.querySelector('button.search-button').click();
      }, city);
      const got = await reply;
      if (!got) {
        // fall back to watching the table change
        for (let w = 0; w < 20; w++) {
          await sleep(1000);
          const now = await p.$$eval('table tbody tr', trs => trs.map(tr => tr.innerText).join('|')).catch(() => '');
          if (now && now !== before && !/Loading|Processing/i.test(now)) break;
        }
      }
      await sleep(1800);
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
        const prevPage = await p.$$eval('table tbody tr', trs => trs.map(tr => tr.innerText).join('|'));
        await next.first().click();
        for (let w = 0; w < 20; w++) {
          await sleep(700);
          const now = await p.$$eval('table tbody tr', trs => trs.map(tr => tr.innerText).join('|')).catch(() => '');
          if (now && now !== prevPage) break;
        }
      }
      console.error(i + '/' + cities.length, city, 'total', all.size);
    } catch (e) {
      console.error(city, 'ERR', e.message.slice(0, 80));
      // start over with a fresh browser if the page or browser went away
      try { await b.close(); } catch {}
      b = await chromium.launch(); p = await b.newPage();
      await openResultsPage(p).catch(() => {});
    }
    if (i % 10 === 0) fs.writeFileSync(outPath, JSON.stringify([...all.values()], null, 1));
    await sleep(1500);
  }
  fs.writeFileSync(outPath, JSON.stringify([...all.values()], null, 1));
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
