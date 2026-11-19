import { request } from '/@/utils/service';

// 自助注册: 发送邮箱验证邮件
export function SendSignup(data: { email: string; company: string; contact_phone?: string; password: string }) {
	return request({
		url: '/api/tenant/signup/send/',
		method: 'post',
		data,
	});
}

// 邮箱验证
export function VerifySignup(token: string) {
	return request({
		url: '/api/tenant/signup/verify/',
		method: 'post',
		data: { token },
	});
}

// 发起注册付费订单(返回二维码)
export function CreateSignupPayment() {
	return request({
		url: '/api/tenant/signup/payment/',
		method: 'post',
		data: {},
	});
}

// 查询支付状态(续费与注册共用同一个 status 接口)
export function GetPaymentStatus(charge_id: string) {
	return request({
		url: '/api/tenant/payment/status/',
		method: 'get',
		params: { charge_id },
	});
}

// 开发/测试模式: 模拟支付成功
export function SimulatePayment(charge_id: string) {
	return request({
		url: '/api/tenant/payment/simulate/',
		method: 'post',
		data: { charge_id },
	});
}

// 支付配置(金额/续费天数/超时)
export function GetPaymentConfig() {
	return request({
		url: '/api/tenant/payment/config/',
		method: 'get',
	});
}

// 免付费直接开通租户(超管关闭"付费开通"开关后可用)
export function ActivateFree() {
	return request({
		url: '/api/tenant/signup/activate_free/',
		method: 'post',
		data: {},
	});
}