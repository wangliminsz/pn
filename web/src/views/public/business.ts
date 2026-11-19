import { request } from '/@/utils/service';

export const BUSINESS = {
	productName: 'proNotify',
	legalName: 'Ant Global Property Co., Ltd.',
	contactName: 'Daisy Chan',
	address: 'Interchange 21 Building, Asoke, Bangkok 10110',
	phone: '+66 0800252616',
	email: 'antglobalproperty3@gmail.com',
	website: 'https://pronotify.site',
	hours: 'Monday–Friday, 09:00–18:00 (ICT)',
	taxId: '0105561199314'
};

export const PLAN = {
	name: 'proNotify Annual Plan',
	priceTHB: 3000,
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
