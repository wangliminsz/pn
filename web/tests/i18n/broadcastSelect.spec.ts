import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8080';
const API_URL = 'http://127.0.0.1:8000';
const USER = 'demo';
const PASSWORD = 'Test123456';

/** Login via API to get a JWT, inject into localStorage. */
async function apiLoginInject(page: Page) {
	const resp = await page.request.post(`${API_URL}/api/token/`, {
		data: { username: USER, password: PASSWORD },
		headers: { 'Content-Type': 'application/json' },
	});
	const body = await resp.json();
	const token = body?.data?.access;
	if (!token) throw new Error(`API login failed: ${JSON.stringify(body)}`);
	await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
	await page.evaluate(([t, u]) => {
		window.localStorage.setItem('token', t);
		window.localStorage.setItem('username', u);
	}, [token, USER] as const);
}

test('broadcast select preview reflects chosen property in real time', async ({ page }) => {
	await apiLoginInject(page);
	await page.goto(`${BASE_URL}/#/broadcast`, { waitUntil: 'domcontentloaded' });
	await page.waitForTimeout(2500);

	// switch to 选择房源 (select) mode
	await page.locator('.el-radio-button:has-text("选择房源")').click();
	await page.waitForTimeout(1200);

	// initially nothing selected -> 0 groups
	let groupCount = await page.locator('.pv-stats b').first().innerText();
	console.log('initial select-mode group count =', groupCount);
	expect(groupCount).toBe('0');

	// select property row "Olympus D514" (proNotify_03)
	const row = page.locator('.prop-row', { hasText: 'Olympus D514' });
	await row.click();
	await page.waitForTimeout(800);

	groupCount = await page.locator('.pv-stats b').first().innerText();
	console.log('after selecting D514 group count =', groupCount);
	expect(groupCount).toBe('1');

	// the bot row shown should be proNotify_03
	const bots = await page.locator('.pv-bot-name').allInnerTexts();
	console.log('bots shown =', bots);
	expect(bots.some((b) => b.includes('proNotify_03'))).toBeTruthy();

	// deselect -> back to 0
	await row.click();
	await page.waitForTimeout(800);
	groupCount = await page.locator('.pv-stats b').first().innerText();
	console.log('after deselect group count =', groupCount);
	expect(groupCount).toBe('0');
});
