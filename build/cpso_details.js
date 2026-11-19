// Read each doctor's public CPSO register page: primary and additional
// business locations, phone, fax, email and hospital privileges.
// Usage: node build/cpso_details.js <list.json> <details.json> [maxAgeDays]
// list.json: output of cpso_list.js. details.json is updated in place (resumable);
// entries newer than maxAgeDays (default 0 = always refresh) are skipped.
const { chromium } = require('playwright');
const fs = require('fs');

const list = JSON.parse(fs.readFileSync(process.argv[2]));
const outPath = process.argv[3];
const maxAge = +(process.argv[4] || 0) * 86400000;
const out = fs.existsSync(outPath) ? JSON.parse(fs.readFileSync(outPath)) : {};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const clean = s => (s || '').replace(/No Information Available/i, '').trim();

function parseBlock(lines) {
  const o = { address: [], phone: '', fax: '', email: '' };
  let mode = 'addr';
  for (const l of lines) {
    if (/^Phone:?/.test(l)) { mode = 'phone'; const v = l.replace(/^Phone:?/, '').trim(); if (v) o.phone = v; continue; }
    if (/^Fax:?/.test(l)) { mode = 'fax'; const v = l.replace(/^Fax:?/, '').trim(); if (v) o.fax = v; continue; }
    if (/^Business Email:?/.test(l)) { mode = 'email'; const v = l.replace(/^Business Email:?/, '').trim(); if (v) o.email = v; continue; }
    if (/^Extension:?/.test(l)) { mode = 'ext'; continue; }
    if (mode === 'addr') o.address.push(l);
    else if (mode === 'phone' && !o.phone) o.phone = l;
    else if (mode === 'ext') { o.phone += ' ext. ' + l; mode = 'x'; }
    else if (mode === 'fax' && !o.fax) o.fax = l;
    else if (mode === 'email' && !o.email) o.email = l;
  }
  o.phone = clean(o.phone); o.fax = clean(o.fax); o.email = clean(o.email);
  return o;
}

async function worker(p, queue) {
  while (queue.length) {
    const d = queue.shift();
    try {
      await p.goto('https://register.cpso.on.ca/physician-info/?cpsonum=' + d.cpso, { waitUntil: 'domcontentloaded', timeout: 60000 });
      await p.waitForSelector('text=Primary Business Location', { timeout: 40000 });
      await sleep(800);
      const more = p.locator('text=VIEW ADDITIONAL BUSINESS LOCATIONS');
      if (await more.count()) { await more.first().click().catch(() => {}); await sleep(1500); }
      const t = (await p.innerText('body')).split('\n').map(s => s.trim()).filter(Boolean);
      const a = t.findIndex(l => l.startsWith('Primary Business Location'));
      const z = t.findIndex((l, i) => i > a && l === 'Specialties');
      const sec = t.slice(a + 1, z);
      const blocks = [];
      let cur = [];
      for (const l of sec) {
        if (/^VIEW ADDITIONAL BUSINESS LOCATIONS/.test(l)) continue;
        if (l === 'Address:') { if (cur.length) blocks.push(cur); cur = []; continue; }
        cur.push(l);
      }
      if (cur.length) blocks.push(cur);
      const locs = blocks.map(parseBlock).filter(b => b.address.length && !/Address not Available/i.test(b.address.join(' ')));
      const h = t.findIndex(l => /^HOSPITAL\s+LOCATION/.test(l) || l === 'HOSPITAL\tLOCATION');
      const hz = t.findIndex((l, i) => i > h && l.startsWith('Professional Corporation'));
      const priv = h >= 0 ? t.slice(h + 1, hz > h ? hz : h + 12).filter(l => !/No information/i.test(l)) : [];
      const st = t.find(l => /^(ACTIVE|INACTIVE)/.test(l)) || '';
      // business addresses of the doctor's active professional corporation(s)
      const corp = await p.evaluate(() => {
        const out = [];
        document.querySelectorAll('[id^=collapseProfCorp]').forEach(box => {
          let sec = box.parentElement, txt = '';
          for (let i = 0; i < 4 && sec; i++) { txt = sec.innerText || ''; if (/Certificate of Authorization/i.test(txt)) break; sec = sec.parentElement; }
          if (/Status:\s*Inactive/i.test(txt)) return;
          box.querySelectorAll('.scrp-businessaddress-row').forEach(r => {
            const a = r.querySelector('.scrp-address-value'), ph = r.querySelector('.scrp-phone-value');
            if (!a) return;
            const lines = a.innerHTML.split(/<br\s*\/?>/i).map(s => s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').trim()).filter(Boolean);
            out.push({ address: lines, phone: ph ? ph.textContent.trim() : '', fax: '', email: '', corp: true });
          });
        });
        const seen = new Set();
        return out.filter(o => { const k = o.address.join('|'); if (seen.has(k)) return false; seen.add(k); return true; });
      });
      locs.push(...corp);
      out[d.cpso] = { cpso: d.cpso, name: d.name, locations: locs, privileges: priv, status: st, checked: Date.now() };
      console.error('ok', d.cpso, d.name, locs.length);
    } catch (e) {
      console.error('ERR', d.cpso, e.message.slice(0, 80));
    }
    await sleep(1500);
  }
}

(async () => {
  const b = await chromium.launch();
  const queue = list.filter(d => !out[d.cpso] || Date.now() - out[d.cpso].checked > maxAge);
  console.error('to fetch', queue.length);
  const pages = [await b.newPage(), await b.newPage()];
  const timer = setInterval(() => fs.writeFileSync(outPath, JSON.stringify(out)), 30000);
  await Promise.all(pages.map(p => worker(p, queue)));
  clearInterval(timer);
  fs.writeFileSync(outPath, JSON.stringify(out));
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
