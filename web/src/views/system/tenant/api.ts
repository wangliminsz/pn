import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/tenant/tenant/';

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

/**
 * 获取租户下拉选项(用户管理绑定租户时使用)
 */
export function getTenantOptions() {
	return request({
		url: apiPrefix + 'options/',
		method: 'get',
	});
}

/**
 * 超管手动同步某租户全部已开启日历的房源到 Google 日历(配好服务账号后一键补写)
 */
export function SyncTenantCalendar(id: number) {
	return request({
		url: apiPrefix + id + '/sync_calendar/',
		method: 'post',
		timeout: 120000,
	});
}
