import { request } from '/@/utils/service';

export const orgchartPrefix = '/api/tenant/tenant/';

export function GetOrgChart(id: number) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart/`,
		method: 'get',
	});
}

export function GetOrgTemplate(id: number) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_template/`,
		method: 'get',
	});
}

export function ImportOrgChart(id: number, formData: FormData) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_import/`,
		method: 'post',
		data: formData,
		timeout: 60000,
		// 交给浏览器自动生成 multipart boundary
		headers: { 'Content-Type': undefined },
	});
}

export function OrgDeptSave(id: number, data: any) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_dept_save/`,
		method: 'post',
		data,
	});
}

export function OrgDeptDelete(id: number, deptId: number) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_dept_delete/`,
		method: 'post',
		data: { id: deptId },
	});
}

export function OrgMemberSave(id: number, data: any) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_member_save/`,
		method: 'post',
		data,
	});
}

export function OrgMemberDelete(id: number, userId: number) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_member_delete/`,
		method: 'post',
		data: { id: userId },
	});
}

// 清空该租户的组织架构(删全部部门与成员, 保留租户本身)
export function OrgChartClear(id: number) {
	return request({
		url: `${orgchartPrefix}${id}/orgchart_clear/`,
		method: 'post',
		data: {},
	});
}

// 租户经理(或超管)修改公司名称
export function UpdateTenantName(id: number, name: string) {
	return request({
		url: `${orgchartPrefix}${id}/company_name/`,
		method: 'post',
		data: { name },
	});
}

export function OrgMemberResetPwd(userId: number, password: string) {
	return request({
		url: `/api/system/user/${userId}/reset_password/`,
		method: 'post',
		data: { password, force_change: true },
	});
}
