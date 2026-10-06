import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = fs.existsSync('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe')
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function runAcceptanceTest() {
  console.log('===============================================================');
  console.log('RUNNING BROWSER ACCEPTANCE TEST FOR DEMAND FORECASTING');
  console.log('Browser:', CHROME_PATH);
  console.log('Target URL: http://localhost:5173');
  console.log('===============================================================\n');

  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,960']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 960 });

  const consoleErrors = [];
  const networkRequests = [];
  const networkFailures = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log('  [CONSOLE ERROR]:', msg.text());
    }
  });

  page.on('request', req => {
    if (req.url().includes('/api/')) {
      networkRequests.push({ method: req.method(), url: req.url() });
    }
  });

  page.on('requestfailed', req => {
    networkFailures.push({ url: req.url(), error: req.failure()?.errorText });
    console.log('  [NETWORK FAILURE]:', req.url(), req.failure()?.errorText);
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
    // 1. Initial Load
    console.log('1. Loading http://localhost:5173 ...');
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle0', timeout: 15000 });
    await sleep(1000);

    const hasLoginModal = await page.$('.modal-overlay');
    if (hasLoginModal) {
      console.log('  Authenticating as Administrator...');
      const submitBtn = await page.$('button[type="submit"]');
      if (submitBtn) await submitBtn.click();
      await page.waitForSelector('.modal-overlay', { hidden: true, timeout: 5000 });
      await sleep(1000);
    }

    // 2. Navigate to Demand Forecasting tab
    console.log('\n2. Navigating to Demand Forecasting tab...');
    await page.waitForSelector('#nav-tab-prediction');
    await page.evaluate(() => document.querySelector('#nav-tab-prediction').click());
    await sleep(2000);

    // Verify no initial error banner
    const initErrorBanner = await page.$('#prediction-error-banner');
    console.log('  Initial error banner present:', initErrorBanner !== null ? 'YES' : 'NO');
    if (initErrorBanner) {
      const txt = await page.evaluate(el => el.innerText, initErrorBanner);
      console.log('  Error text:', txt);
    }

    // 3. Test Valid Forecast for Product 1 (SES)
    console.log('\n3. Testing Valid Forecast with SES (Exponential Smoothing)...');
    await page.select('#prediction-method-select', 'exponential_smoothing');
    await fillInput('#prediction-forecast-days', '30');
    await fillInput('#prediction-lead-time', '7');
    await page.click('#btn-run-prediction');
    await sleep(1500);

    let predDemand = await page.evaluate(() => {
      const el = document.querySelector('.glass-card div[style*="font-size: 2rem"]');
      return el ? el.innerText.trim() : null;
    });
    let formulaText = await page.evaluate(() => {
      const el = document.querySelector('.glass-card div[style*="color: white"]');
      return el ? el.innerText.trim() : null;
    });
    console.log('  Projected Demand:', predDemand);
    console.log('  Formula Explanation:', formulaText);
    const passSES = formulaText && formulaText.includes('Recommended Restock');
    console.log('  SES Forecast Completed Successfully:', passSES ? '✅ YES' : '❌ NO');

    // 4. Test Valid Forecast with WMA (Weighted Moving Average)
    console.log('\n4. Testing Valid Forecast with WMA...');
    await page.select('#prediction-method-select', 'weighted_moving_average');
    await fillInput('#prediction-forecast-days', '45');
    await fillInput('#prediction-lead-time', '10');
    await page.click('#btn-run-prediction');
    await sleep(1500);

    formulaText = await page.evaluate(() => {
      const el = document.querySelector('.glass-card div[style*="color: white"]');
      return el ? el.innerText.trim() : null;
    });
    console.log('  WMA Formula Explanation:', formulaText);
    const passWMA = formulaText && formulaText.includes('Recommended Restock');
    console.log('  WMA Forecast Completed Successfully:', passWMA ? '✅ YES' : '❌ NO');

    // 5. Test Valid Forecast with SMA (Simple Moving Average)
    console.log('\n5. Testing Valid Forecast with SMA...');
    await page.select('#prediction-method-select', 'moving_average');
    await fillInput('#prediction-forecast-days', '60');
    await fillInput('#prediction-lead-time', '14');
    await page.click('#btn-run-prediction');
    await sleep(1500);

    formulaText = await page.evaluate(() => {
      const el = document.querySelector('.glass-card div[style*="color: white"]');
      return el ? el.innerText.trim() : null;
    });
    console.log('  SMA Formula Explanation:', formulaText);
    const passSMA = formulaText && formulaText.includes('Recommended Restock');
    console.log('  SMA Forecast Completed Successfully:', passSMA ? '✅ YES' : '❌ NO');

    // 6. Test Invalid Forecast Horizon (< 1)
    console.log('\n6. Testing Invalid Forecast Horizon (0 days)...');
    await fillInput('#prediction-forecast-days', '0');
    await page.click('#btn-run-prediction');
    await sleep(800);

    let errBanner = await page.$('#prediction-error-banner');
    let errText = errBanner ? await page.evaluate(el => el.innerText, errBanner) : '';
    console.log('  Error Banner on Horizon 0:', errText);
    const passInvalidHorizon = errText.includes('Forecast horizon must be a positive number between 1 and 180 days');
    console.log('  Invalid Horizon Blocked with Clear Error:', passInvalidHorizon ? '✅ YES' : '❌ NO');

    // 7. Test Invalid Lead Time (> 90)
    console.log('\n7. Testing Invalid Supplier Lead Time (120 days)...');
    await fillInput('#prediction-forecast-days', '30'); // Fix horizon
    await fillInput('#prediction-lead-time', '120');
    await page.click('#btn-run-prediction');
    await sleep(800);

    errBanner = await page.$('#prediction-error-banner');
    errText = errBanner ? await page.evaluate(el => el.innerText, errBanner) : '';
    console.log('  Error Banner on Lead Time 120:', errText);
    const passInvalidLead = errText.includes('Supplier lead time must be a positive number between 1 and 90 days');
    console.log('  Invalid Lead Time Blocked with Clear Error:', passInvalidLead ? '✅ YES' : '❌ NO');

    // 8. Test Dismissing Error Banner
    console.log('\n8. Testing Error Banner Dismissal...');
    const dismissBtn = await page.$('#prediction-error-banner button');
    if (dismissBtn) {
      await dismissBtn.click();
      await sleep(500);
    }
    const errBannerAfterDismiss = await page.$('#prediction-error-banner');
    const passDismiss = errBannerAfterDismiss === null;
    console.log('  Error Banner Dismissed on Click:', passDismiss ? '✅ YES' : '❌ NO');

    // 9. Re-run Valid Forecast to Confirm Recovery
    console.log('\n9. Confirming Recovery with Valid Parameters...');
    await fillInput('#prediction-lead-time', '7');
    await page.click('#btn-run-prediction');
    await sleep(1500);

    const successBanner = await page.$('#prediction-success-banner');
    const successText = successBanner ? await page.evaluate(el => el.innerText, successBanner) : '';
    console.log('  Success Notification:', successText);
    const passRecovery = successText.includes('Demand forecast computed successfully');
    console.log('  Recovery Successful:', passRecovery ? '✅ YES' : '❌ NO');

    console.log('\n===============================================================');
    console.log('ACCEPTANCE SUMMARY');
    console.log('SES:', passSES ? 'PASS' : 'FAIL');
    console.log('WMA:', passWMA ? 'PASS' : 'FAIL');
    console.log('SMA:', passSMA ? 'PASS' : 'FAIL');
    console.log('Validation Horizon:', passInvalidHorizon ? 'PASS' : 'FAIL');
    console.log('Validation Lead Time:', passInvalidLead ? 'PASS' : 'FAIL');
    console.log('Error Dismissal:', passDismiss ? 'PASS' : 'FAIL');
    console.log('Recovery:', passRecovery ? 'PASS' : 'FAIL');
    console.log('Console Errors:', consoleErrors.length);
    console.log('Network Failures:', networkFailures.length);
    console.log('===============================================================');

  } catch (err) {
    console.error('Acceptance test failed with exception:', err);
  } finally {
    await browser.close();
  }
}

runAcceptanceTest();
