import { request } from '/@/utils/service';

// 房源变更记录(负责人改派) 列表 - 全员可见(能看房源的人 + 被改派的原负责人)
export function GetChangeLogs() {
	return request({
		url: '/api/property/property/change_logs/',
		method: 'get',
	});
}
