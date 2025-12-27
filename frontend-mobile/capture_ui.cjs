const { chromium } = require('playwright');
const path = require('path');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 390, height: 844 },
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
    });
    const page = await context.newPage();

    const screenshotsDir = path.join(__dirname, 'screenshots');
    const fs = require('fs');
    if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir);
    }

    const capture = async (name, url) => {
        console.log(`Navigating to ${url}...`);
        await page.goto(url, { waitUntil: 'networkidle' });
        // Wait for ECharts or other animations
        await page.waitForTimeout(2000);
        const screenshotPath = path.join(screenshotsDir, `${name}.png`);
        await page.screenshot({ path: screenshotPath });
        console.log(`Saved screenshot: ${screenshotPath}`);
    };

    try {
        await capture('01_dashboard', 'http://localhost:8080/dashboard');
        await capture('02_screener', 'http://localhost:8080/screener');
        await capture('03_console', 'http://localhost:8080/console');

        // Try to go to a stock detail page (assuming 600519 is valid)
        await capture('04_detail', 'http://localhost:8080/stock/600519');

    } catch (err) {
        console.error('Error during capture:', err);
    } finally {
        await browser.close();
    }
})();
