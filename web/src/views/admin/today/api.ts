import { request } from '/@/utils/service';

// 超管「今日消息」监控: 指定日期全租户应发提醒清单 + 状态(只读)
export function getTodayMessages(date?: string) {
	return request({
		url: '/api/notify/today/',
		method: 'get',
		params: date ? { date } : {},
	});
}

// 刷新某房源 Line 群名称(绕过缓存强制重拉; 超管不受租户限制)
export function RefreshGroupNameByProperty(property_id: number) {
	return request({
		url: '/api/tenant/workspace/refresh_group_name/',
		method: 'post',
		data: { property_id },
	});
}