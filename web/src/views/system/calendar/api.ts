import { request } from '/@/utils/service';

// 内置提醒日历: 返回某月的提醒事件(付租/到期)
export function GetCalendarMonth(year: number, month: number) {
	return request({
		url: '/api/tenant/workspace/calendar/',
		method: 'get',
		params: { year, month },
	});
}