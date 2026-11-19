import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';

// Requires backend at :8000 with captcha disabled (base.captcha_state=false) for UI login test.
const BASE_URL = 'http://127.0.0.1:8080';
const API_URL = 'http://127.0.0.1:8000';
const SHOT_DIR = '/tmp/page_traversal_shots';
const USER = process.env.TEST_ADMIN_USER || 'superadmin';
const PASSWORD = process.env.TEST_ADMIN_PASSWORD || 'admin123456';

// Router uses createWebHashHistory → real routes are after '#', e.g. /#/property
const PAGES: Array<{ path: string; name: string }> = [
	{ path: '/#/tenant', name: 'tenant' },
	{ path: '/#/property', name: 'property' },
	{ path: '/#/linebot', name: 'linebot' },
	{ path: '/#/messagelog', name: 'messagelog' },
	{ path: '/#/groupdoc', name: 'groupdoc' },
];

async function shot(page: Page, name: string) {
	if (!fs.existsSync(SHOT_DIR)) fs.mkdirSync(SHOT_DIR, { recursive: true });
	await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: false });
	console.log(`  [screenshot] ${SHOT_DIR}/${name}.png`);
}

/** Login via API to get a JWT, inject into localStorage (mirrors web/src/utils/storage.ts). */
async function apiLoginInject(page: Page) {
	const resp = await page.request.post(`${API_URL}/api/login/`, {
		data: { username: USER, password: PASSWORD },
		headers: { 'Content-Type': 'application/json' },
	});
	const body = await resp.json();
	const token = body?.data?.access;
	if (!token) throw new Error(`API login failed: ${JSON.stringify(body)}`);
	await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
	await page.evaluate((t) => {
		window.localStorage.setItem('token', t);
		window.localStorage.setItem('username', 'superadmin');
	}, token);
}

/** UI form login, used to validate the real login flow. */
async function uiLogin(page: Page) {
	await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
	await page.waitForTimeout(1200);
	const form = page.locator('.el-tab-pane:visible .login-content-form').first();
	await form.locator('input').nth(0).fill(USER);
	await form.locator('input').nth(1).fill(PASSWORD);
	await page.locator('.login-content-submit:visible').first().click();
	await page.waitForTimeout(3000);
}

test('UI login flow (superadmin) lands on dashboard', async ({ page }) => {
	await uiLogin(page);
	await page.waitForTimeout(1500);
	const url = page.url();
	console.log('after UI login url =', url);
	await shot(page, 'ui_login_result');
	// Hash-mode SPA: server path stays, but the hash route must leave /login toward home
	expect(url).toMatch(/#\/(home|$)/);
	expect(url).not.toMatch(/#\/login/);
});

for (const { path, name } of PAGES) {
	test(`page ${name} ${path} loads`, async ({ page }) => {
		await apiLoginInject(page);
		await page.goto(`${BASE_URL}${path}`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(3500);
		const url = page.url();
		console.log(`  [${name}] final url =`, url);
		await shot(page, `page_${name}`);
		// Must NOT be bounced back to login (auth broken) or blank
		expect(url).not.toMatch(/\/login/);
		// The hash route must be the intended page (e.g. /#/property)
		expect(url).toContain('#' + path.replace('/#', ''));
		const bodyText = await page.locator('body').innerText();
		expect(bodyText.length).toBeGreaterThan(0);
		// No fatal error overlay
		const err = await page.locator('.el-message-box, .el-overlay-message-box').isVisible().catch(() => false);
		expect(err).toBeFalsy();
	});
}
