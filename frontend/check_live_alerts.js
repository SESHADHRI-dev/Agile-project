import puppeteer from 'puppeteer-core';
import fs from 'fs';

const CHROME_PATH = fs.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const LIVE_URL = 'http://intellistock-frontend-897258608555-us-east-1.s3-website-us-east-1.amazonaws.com';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function run() {
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,960']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 960 });

  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('response', async res => {
    if (res.url().includes('/api/')) {
      console.log(`API [${res.status()}] ${res.url()}`);
      try {
        const text = await res.text();
        if (res.url().includes('/alerts') || res.url().includes('/inventory')) {
          console.log(`  Response (${res.url()}):`, text.slice(0, 300));
        }
      } catch (e) {}
    }
  });

  console.log('Navigating to live application:', LIVE_URL);
  await page.goto(LIVE_URL, { waitUntil: 'networkidle0' });
  await sleep(3000);

  const state = await page.evaluate(() => {
    return {
      bodyText: document.body.innerText.slice(0, 500),
      hasUser: !document.querySelector('.login-modal')
    };
  });
  console.log('Page initial state:', state);

  // Navigate to Alerts
  await page.evaluate(() => {
    const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Low-Stock Alerts') || b.textContent.includes('Review Alerts'));
    if (btn) btn.click();
  });
  await sleep(3000);

  const alertElements = await page.evaluate(() => {
    return {
      alertsContainerText: document.querySelector('main')?.innerText,
      alertCardsCount: document.querySelectorAll('.alert-card-item').length
    };
  });
  console.log('Alert elements on alerts tab:', alertElements);

  await browser.close();
}

run().catch(err => {
  console.error('Error running test:', err);
  process.exit(1);
});
