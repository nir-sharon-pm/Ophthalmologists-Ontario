// Read the Canadian Ophthalmological Society's public "Find an Ophthalmologist" table.
// Usage: node build/cos_list.js <out.json>   (rows of table cells)
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('https://cos.imiscloud.com/COS_Member_Portal/COS-Member-Portal/Find-an-Ophthalmologist.aspx', { waitUntil: 'networkidle', timeout: 90000 }).catch(() => {});
  const all = p.locator('a', { hasText: 'Show all' });
  if (await all.count()) { await all.first().click(); await p.waitForLoadState('networkidle', { timeout: 90000 }).catch(() => {}); await p.waitForTimeout(4000); }
  const rows = await p.$$eval('table tr', trs => trs.map(tr => [...tr.querySelectorAll('td')].map(td => td.innerText.trim())).filter(r => r.length >= 10));
  require('fs').writeFileSync(process.argv[2], JSON.stringify(rows));
  console.error(rows.length, 'rows');
  await b.close();
})();
