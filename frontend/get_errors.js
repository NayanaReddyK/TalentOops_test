const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') console.log('PAGE ERROR:', msg.text());
  });
  
  page.on('pageerror', error => {
    console.log('UNCAUGHT EXCEPTION:', error.message);
  });

  await page.goto('http://localhost:5175', { waitUntil: 'networkidle2' });
  await browser.close();
})();
