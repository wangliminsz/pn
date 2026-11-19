import { request } from '/@/utils/service';

export const apiPrefix = '/api/notify/groupdoc/';

// 群文档列表(返回扁平文件数组, 含 group_id / group_name / name / size / mtime / url)
export function GetList(params: any = {}) {
	return request({
		url: apiPrefix,
		method: 'get',
		params,
	});
}

// 精确刷新某群名称(调 LINE API, force=True)
export function RefreshGroupName(group_id: string) {
	return request({
		url: `${apiPrefix}refresh_group_name/`,
		method: 'get',
		params: { group_id },
	});
}
