import { request } from '/@/utils/service';

// select 模式: 传显式 property_ids 数组(空数组=选中0个, 后端返回0群)
// all 模式: 不传 property_ids(后端视为全部群)
// 注意: 用 POST + body 而非 GET query, 避免空数组被 paramsSerializer 丢弃成"全部群"
export function GetBroadcastPreview(property_ids?: number[] | null) {
	return request({
		url: '/api/tenant/broadcast/preview/',
		method: 'post',
		data: property_ids === null || property_ids === undefined ? {} : { property_ids },
	});
}

export function SendBroadcast(message: string, property_ids?: number[] | null) {
	return request({
		url: '/api/tenant/broadcast/send/',
		method: 'post',
		data: property_ids === null || property_ids === undefined
			? { message }
			: { message, property_ids },
	});
}

// 本租户所有带 group_id 的房源(供选择)
export function GetBroadcastableProperties() {
	return request({
		url: '/api/property/property/',
		method: 'get',
		params: { page: 1, limit: 500 },
	});
}

export function GetBroadcastStatus(task_id: number) {
	return request({
		url: '/api/tenant/broadcast/status/',
		method: 'get',
		params: { task_id },
	});
}

export function CleanBroadcast() {
	return request({
		url: '/api/tenant/broadcast/clean/',
		method: 'post',
	});
}