#!/usr/bin/env node
/**
 * Weighs the page: how many bytes a first visit costs, how many requests it
 * makes, how many DOM nodes it builds. This is the script behind the numbers
 * in docs/performance.md, so anyone can re-run it and check them.
 *
 *   npm i -D playwright   (once)
 *   node tools/measure.js
 *
 * It serves the repo over a throwaway static server on port 8099 and drives
 * Chromium against it. Pass --keep-external to let Google Fonts and the map
 * CDNs load; by default they are blocked so the numbers describe what this
 * repository ships rather than what the internet adds to it.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.dirname(__dirname);
const PORT = 8099;
const KEEP_EXTERNAL = process.argv.includes('--keep-external');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.png': 'image/png',
  '.webp': 'image/webp',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

function serve() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const rel = decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/, '') || 'index.html';
      const file = path.join(ROOT, rel);
      if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404).end('not found');
        return;
      }
      res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    server.listen(PORT, '127.0.0.1', () => resolve(server));
  });
}

(async () => {
  const server = await serve();
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  if (!KEEP_EXTERNAL) {
    await page.route('**://fonts.googleapis.com/**', (r) => r.abort());
    await page.route('**://fonts.gstatic.com/**', (r) => r.abort());
    await page.route('**://unpkg.com/**', (r) => r.abort());
    await page.route('**://*.basemaps.cartocdn.com/**', (r) => r.abort());
  }

  const requests = [];
  page.on('response', async (res) => {
    let size = 0;
    try {
      size = (await res.body()).length;
    } catch (_) {
      /* redirects and aborted requests have no body */
    }
    requests.push({ url: res.url(), size, type: res.request().resourceType() });
  });

  await page.goto(`http://127.0.0.1:${PORT}/index.html`, { waitUntil: 'load', timeout: 60000 });

  const dom = await page.evaluate(() => ({
    nodes: document.getElementsByTagName('*').length,
    listeners: document.querySelectorAll('[onclick]').length,
    images: document.images.length,
  }));

  const total = requests.reduce((sum, r) => sum + r.size, 0);

  console.log(`\nfirst visit${KEEP_EXTERNAL ? '' : ' (external hosts blocked)'}`);
  console.log('─'.repeat(56));
  for (const r of requests.sort((a, b) => b.size - a.size)) {
    console.log(`${String(Math.round(r.size / 1024)).padStart(5)} KB  ${r.type.padEnd(9)} ${r.url.replace(`http://127.0.0.1:${PORT}/`, '')}`);
  }
  console.log('─'.repeat(56));
  console.log(`${String(Math.round(total / 1024)).padStart(5)} KB  total across ${requests.length} requests`);
  console.log(`${String(dom.nodes).padStart(5)}     DOM nodes, ${dom.images} images\n`);

  await browser.close();
  server.close();
})();
