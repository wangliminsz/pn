import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/notify/linebot/';

export function GetList(query: PageQuery) {
	return request({
		url: apiPrefix,
		method: 'get',
		params: query,
	});
}

export function GetObj(id: InfoReq) {
	return request({
		url: apiPrefix + id,
		method: 'get',
	});
}

export function GetUsage(id: number, force = false) {
	return request({
		url: apiPrefix + id + '/usage/',
		method: 'get',
		params: { force: force ? '1' : '' },
	});
}

export function AddObj(obj: AddReq) {
	return request({
		url: apiPrefix,
		method: 'post',
		data: obj,
	});
}

export function UpdateObj(obj: EditReq) {
	return request({
		url: apiPrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

export function DelObj(id: DelReq) {
	return request({
		url: apiPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

// 超管手动触发每日提醒任务(立即发送, 不等待定时时间)
export function RunDailyNotify(params: any = {}) {
	return request({
		url: apiPrefix + 'run_daily_notify/',
		method: 'post',
		data: params,
	});
}

// 导出全部 LineBot(JSON, 含凭据明文, 仅超管)
export function ExportBots() {
	return request({
		url: apiPrefix + 'export_bots/',
		method: 'get',
		responseType: 'blob',
	});
}

// 导入 LineBot(JSON, upsert by bot_code): data = {bots:[...]} 或数组
export function ImportBots(data: any) {
	return request({
		url: apiPrefix + 'import_bots/',
		method: 'post',
		data,
	});
}
