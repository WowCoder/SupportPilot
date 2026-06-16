/**
 * 页面验证脚本 — 无头浏览器截图 + 元素检查
 * 用法: node scripts/page-check.js <url> [--screenshot <path>] [--text] [--title]
 */
const { chromium } = require('playwright');

(async () => {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log('用法: node scripts/page-check.js <url> [--screenshot <path>] [--text] [--title]');
    process.exit(1);
  }

  const url = args[0];
  const screenshot = args.includes('--screenshot') ? args[args.indexOf('--screenshot') + 1] : null;
  const showText = args.includes('--text');
  const showTitle = args.includes('--title');

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
    console.log(`✓ ${page.url()} (${response.status()})`);

    if (showTitle || !screenshot) {
      const title = await page.title();
      console.log(`  标题: ${title}`);
    }

    if (showText) {
      const text = await page.textContent('body');
      console.log('  内容预览:', text.trim().slice(0, 300));
    }

    if (screenshot) {
      await page.screenshot({ path: screenshot, fullPage: true });
      console.log(`  截图: ${screenshot}`);
    }
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
