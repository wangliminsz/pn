import { request } from '/@/utils/service';

// 支付配置(金额/续费天数/是否开发模式)
export function GetPaymentConfig() {
	return request({
		url: '/api/tenant/payment/config/',
		method: 'get',
	});
}

// 发起一笔 PromptPay 续费 charge(返回二维码)
export function CreatePaymentCharge() {
	return request({
		url: '/api/tenant/payment/create/',
		method: 'post',
		data: {},
	});
}

// 查询支付状态
export function GetPaymentStatus(charge_id: string) {
	return request({
		url: '/api/tenant/payment/status/',
		method: 'get',
		params: { charge_id },
	});
}

// 开发模式: 模拟支付成功(等价于触发 Omise webhook)
export function SimulatePayment(charge_id: string) {
	return request({
		url: '/api/tenant/payment/simulate/',
		method: 'post',
		data: { charge_id },
	});
}
