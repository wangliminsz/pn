import { request } from '/@/utils/service';

export const apiPrefix = '/api/notify/groupdoc/';

// 群文档列表(返回扁平文件数组, 含 group_id / name / size / mtime / url)
export function GetList(params: any = {}) {
	return request({
		url: apiPrefix,
		method: 'get',
		params,
	});
}
