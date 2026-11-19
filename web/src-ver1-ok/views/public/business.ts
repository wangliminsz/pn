import { request } from '/@/utils/service';

export const BUSINESS = {
	productName: 'proNotify',
	legalName: '[Your registered company name]',
	contactName: '[Contact person]',
	address: '[Registered business address, Thailand]',
	phone: '[+66 XX XXX XXXX]',
	email: 'support@pronotify.site',
	website: 'https://pronotify.site',
	hours: 'Monday–Friday, 09:00–18:00 (ICT)',
	taxId: '[Thai tax ID / company registration number]'
};

export const PLAN = {
	name: 'proNotify Annual Plan',
	priceTHB: 2000,
	billingDays: 365,
	currency: 'THB',
	autoRenew: false,
	paymentMethod: 'PromptPay QR via Omise'
};

export const LEGAL_LINKS = {
	terms: '/legal/terms-of-service.html',
	privacy: '/legal/privacy-policy.html',
	refund: '/legal/refund-cancellation-policy.html',
	contact: '/legal/contact.html',
	index: '/legal/'
};

export const formatTHB = (amount: number) => `฿${amount.toLocaleString('en-US')}`;

export async function fetchPublicPlan() {
	try {
		const json: any = await request({ url: '/api/tenant/payment/public_config/', method: 'get' });
		const data = json?.data || {};
		const amount = Number(data.amount_thb);
		return {
			...PLAN,
			priceTHB: Number.isFinite(amount) && amount > 0 ? amount : PLAN.priceTHB,
			billingDays: Number(data.renew_days) > 0 ? Number(data.renew_days) : PLAN.billingDays,
			currency: data.currency || PLAN.currency,
			autoRenew: Boolean(data.auto_renew),
			paymentMethod: data.payment_method || PLAN.paymentMethod
		};
	} catch {
		return { ...PLAN };
	}
}
