import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = fs.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const SCREENSHOTS_DIR = path.resolve(__dirname, '../tests/screenshots');
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const PROD_URL = 'https://intellistock-frontend-897258608555-us-east-1.s3.us-east-1.amazonaws.com/index.html';

async function runProdAudit() {
  console.log('===============================================================');
  console.log('STARTING REAL BROWSER PRODUCTION AWS VERIFICATION');
  console.log('Target URL:', PROD_URL);
  console.log('Chrome Binary:', CHROME_PATH);
  console.log('===============================================================\n');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,960']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 960 });

  const consoleErrors = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.error('  [CONSOLE ERROR]:', msg.text());
    }
  });

  const fillInput = async (selector, value) => {
    await page.focus(selector);
    await page.keyboard.down('Control');
    await page.keyboard.press('A');
    await page.keyboard.up('Control');
    await page.keyboard.press('Backspace');
    await page.type(selector, String(value));
  };

  try {
    // 1. Navigate to Production Frontend
    console.log('[1/7] Navigating to Deployed S3 Frontend...');
    await page.goto(PROD_URL, { waitUntil: 'networkidle2', timeout: 30000 });
    await sleep(2000);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_1_initial_load.png') });

    // 2. Perform Cognito Login
    console.log('[2/7] Checking Authentication State...');
    const loginModal = await page.$('.modal-overlay');
    if (loginModal) {
      console.log('  Login modal displayed. Clicking Admin One-Click Login...');
      const buttons = await page.$$('button');
      let adminBtn = null;
      for (const btn of buttons) {
        const text = await page.evaluate(el => el.textContent, btn);
        if (text.includes('Admin (Dr. Sharma)')) {
          adminBtn = btn;
          break;
        }
      }
      if (adminBtn) {
        await adminBtn.click();
        await sleep(3500);
      } else {
        console.log('  Submitting login form directly...');
        await page.click('button[type="submit"]');
        await sleep(3500);
      }
    }
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_2_authenticated_dashboard.png') });

    // 3. Inspect Navbar Badges
    console.log('[3/7] Inspecting Production Header Badges...');
    const navbarText = await page.evaluate(() => document.querySelector('header')?.innerText || '');
    console.log('  Header snippet:\n', navbarText.split('\n').filter(Boolean).join(' | '));
    const hasCognitoAuth = navbarText.includes('AWS COGNITO');
    const hasDynamoDB = navbarText.includes('DYNAMODB');
    console.log(`  AUTH: AWS COGNITO -> ${hasCognitoAuth ? '✅ CONFIRMED' : '❌ FAILED'}`);
    console.log(`  DB: DYNAMODB -> ${hasDynamoDB ? '✅ CONFIRMED' : '❌ FAILED'}`);

    // 4. Inspect Active Alerts Count
    console.log('[4/7] Checking Alerts Count on Navigation & Badge...');
    const alertCountText = await page.evaluate(() => {
      const badge = document.querySelector('.badge-danger, .badge-warning');
      return badge ? badge.innerText : '0';
    });
    console.log(`  Active Alerts Badge: ${alertCountText}`);

    // Navigate to Alerts View
    const navButtons = await page.$$('button, a');
    for (const nb of navButtons) {
      const txt = await page.evaluate(el => el.textContent, nb);
      if (txt.includes('Stockout & Low Stock') || txt.includes('Alerts')) {
        await nb.click();
        await sleep(1500);
        break;
      }
    }
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_3_alerts_before_purchase.png') });

    // 5. Navigate to Inbound Purchases & Record Purchase
    console.log('[5/7] Navigating to Inbound Purchases...');
    const navButtons2 = await page.$$('button, a');
    for (const nb of navButtons2) {
      const txt = await page.evaluate(el => el.textContent, nb);
      if (txt.includes('Inbound Purchases') || txt.includes('Purchases')) {
        await nb.click();
        await sleep(1500);
        break;
      }
    }

    console.log('  Opening Record Purchase Modal...');
    const openPurModalBtn = await page.$('#btn-open-purchase-modal');
    if (openPurModalBtn) {
      await openPurModalBtn.click();
      await sleep(1000);

      // Select PRD-1005
      await page.select('#purchase-select-product', 'PRD-1005');
      await sleep(500);

      // Fill Quantity: 40
      await fillInput('#purchase-input-quantity', '40');
      // Fill Unit Cost: 45
      await fillInput('#purchase-input-cost', '45');

      await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_4_purchase_modal_filled.png') });

      // Click Confirm & Increment Stock
      console.log('  Submitting Inbound Purchase of 40 units for PRD-1005...');
      await page.click('#btn-submit-purchase');
      await sleep(3500);
    }
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_5_purchase_history_updated.png') });

    // 6. Navigate to Inventory Ledger & Verify Stock
    console.log('[6/7] Verifying Inventory Ledger...');
    const navButtons3 = await page.$$('button, a');
    for (const nb of navButtons3) {
      const txt = await page.evaluate(el => el.textContent, nb);
      if (txt.includes('Warehouse Inventory') || txt.includes('Inventory Ledger')) {
        await nb.click();
        await sleep(1500);
        break;
      }
    }
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_6_inventory_ledger_verified.png') });

    // 7. Return to Alerts View & Verify Alert Disappeared
    console.log('[7/7] Returning to Alerts View to Confirm Alert Cleared...');
    const navButtons4 = await page.$$('button, a');
    for (const nb of navButtons4) {
      const txt = await page.evaluate(el => el.textContent, nb);
      if (txt.includes('Stockout & Low Stock') || txt.includes('Alerts')) {
        await nb.click();
        await sleep(1500);
        break;
      }
    }
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_7_alerts_after_purchase.png') });

    const alertsRemainingText = await page.evaluate(() => {
      const cards = document.querySelectorAll('.glass-card, tr');
      return Array.from(cards).map(c => c.innerText).join('\n');
    });
    const prd1005StillInAlert = alertsRemainingText.includes('PRD-1005');
    console.log(`  PRD-1005 alert cleared in UI: ${!prd1005StillInAlert ? '✅ CONFIRMED (Alert Gone)' : '❌ Still Present'}`);

    console.log('\n===============================================================');
    console.log('PRODUCTION BROWSER VERIFICATION COMPLETE');
    console.log('Console Errors:', consoleErrors.length);
    console.log('Screenshots saved to:', SCREENSHOTS_DIR);
    console.log('===============================================================');

  } catch (err) {
    console.error('Browser Test Error:', err);
    await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'prod_error.png') });
  } finally {
    await browser.close();
  }
}

runProdAudit();
