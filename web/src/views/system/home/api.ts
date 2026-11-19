import { request } from '/@/utils/service';

export function GetWorkspace() {
	return request({
		url: '/api/tenant/workspace/',
		method: 'get',
	});
}

export function RefreshGroupName(property_id: number) {
	return request({
		url: '/api/tenant/workspace/refresh_group_name/',
		method: 'post',
		data: { property_id },
	});
}

export function SendReminderNow(property_id: number, kind: string, rule_id?: number) {
	return request({
		url: '/api/tenant/workspace/send_reminder_now/',
		method: 'post',
		data: { property_id, kind, rule_id },
	});
}

// 租户经理更新本租户的 Google 日历ID(后端会自动同步本租户房源)
export function UpdateTenantGoogleCalendar(tenant_id: number, google_calendar_id: string) {
	return request({
		url: `/api/tenant/tenant/${tenant_id}/google_calendar/`,
		method: 'post',
		data: { google_calendar_id },
	});
}

// 租户经理更新本租户的落款签名(提醒消息末尾的公司名; 空串=恢复默认用公司名/全局签名)
export function UpdateTenantSignName(tenant_id: number, sign_name: string) {
	return request({
		url: `/api/tenant/tenant/${tenant_id}/sign_name/`,
		method: 'post',
		data: { sign_name },
	});
}