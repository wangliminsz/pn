import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8080';
const API_URL = 'http://127.0.0.1:8000';
const USER = 'demo';
const PASSWORD = 'Test123456';

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

test('demo manager can open member edit dialog with reset password button', async ({ page }) => {
	await apiLoginInject(page);
	await page.goto(`${BASE_URL}/#/org`, { waitUntil: 'domcontentloaded' });
	await page.waitForTimeout(3000);

	// tree node that contains demo22 username
	const demo22Node = page.locator('.el-tree-node', { has: page.locator('.t-username:has-text("demo22")') }).first();
	await demo22Node.scrollIntoViewIfNeeded();
	await demo22Node.hover();
	await page.waitForTimeout(400);

	// click 编辑 inside that specific node
	await demo22Node.getByRole('button', { name: '编辑' }).first().click();
	await page.waitForTimeout(800);

	const dlg = page.locator('.el-dialog', { hasText: '编辑成员' });
	await expect(dlg).toBeVisible();
	const resetBtn = dlg.getByRole('button', { name: '重置密码' });
	await expect(resetBtn).toBeVisible();
	console.log('reset password button visible in member dialog =', await resetBtn.isVisible());
});
