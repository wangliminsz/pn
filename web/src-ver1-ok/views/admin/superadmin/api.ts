import { request } from '/@/utils/service';

const apiPrefix = '/api/system/superadmin/';

// 全量(不嫌弃直接拉全部, 超管个数一般个位数)
export function GetList(params: any = {}) {
	return request({
		url: apiPrefix,
		method: 'get',
		params: { ...params },
	});
}

export function Create(data: any) {
	return request({
		url: apiPrefix,
		method: 'post',
		data,
	});
}

export function ToggleActive(id: number, is_active: boolean) {
	return request({
		url: `${apiPrefix}${id}/toggle_active/`,
		method: 'post',
		data: { is_active },
	});
}

export function ResetPassword(id: number, data: any) {
	return request({
		url: `${apiPrefix}${id}/reset_password/`,
		method: 'post',
		data,
	});
}

export function LookupUsers(q: string) {
	return request({
		url: `${apiPrefix}lookup/`,
		method: 'get',
		params: { q },
	});
}

export function UnlockUser(data: any) {
	return request({
		url: `${apiPrefix}unlock_user/`,
		method: 'post',
		data,
	});
}

export function GetLoginSettings() {
	return request({
		url: `${apiPrefix}login_settings/`,
		method: 'get',
	});
}

export function SaveLoginSettings(data: any) {
	return request({
		url: `${apiPrefix}login_settings/save/`,
		method: 'post',
		data,
	});
}

export function GetSignupSettings() {
	return request({
		url: `${apiPrefix}signup_settings/`,
		method: 'get',
	});
}

export function SaveSignupSettings(data: any) {
	return request({
		url: `${apiPrefix}signup_settings/save/`,
		method: 'post',
		data,
	});
}

export function GetDefaultPassword() {
	return request({
		url: `${apiPrefix}default_password_settings/`,
		method: 'get',
	});
}

export function SaveDefaultPassword(data: any) {
	return request({
		url: `${apiPrefix}default_password_settings/save/`,
		method: 'post',
		data,
	});
}
