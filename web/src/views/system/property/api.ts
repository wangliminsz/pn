import { request } from '/@/utils/service';
import { PageQuery, AddReq, DelReq, EditReq, InfoReq } from '@fast-crud/fast-crud';

export const apiPrefix = '/api/property/property/';

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

// 房源负责人变更记录
export function GetOwnerLogs(id: number) {
	return request({
		url: apiPrefix + id + '/owner_logs/',
		method: 'get',
	});
}

// ---------------- 房源批量导入 ----------------
export function ImportProperty(formData: FormData, dryRun: boolean) {
	formData.append('dry_run', String(dryRun));
	return request({
		url: `${apiPrefix}property_import/`,
		method: 'post',
		data: formData,
		timeout: 60000,
		// 交给浏览器生成 multipart boundary
		headers: { 'Content-Type': undefined },
	});
}

// 下载房源导入模板 CSV (lang: 'zh-cn' | 'en', 仅表头不同, 内容一致)
export function DownloadPropertyTemplate(lang: 'zh-cn' | 'en' = 'zh-cn') {
	const headers = lang === 'en'
		? ['Property Name', 'Rent', 'Pay Period', 'Remind Day', 'Start Date', 'End Date', 'Remark', 'Line Bot', 'Group ID']
		: ['房间名称', '租金', '付租周期', '提醒日', '起租日期', '结束日期', '备注', 'Line Bot', 'Group ID'];
	const sample = lang === 'en'
		? [
			['A1 Property', '10000', 'Monthly', '5', '2026-01-05', '2027-01-04', 'Water & electricity', '', ''],
			['B2 Property', '15000', 'Quarterly', '15', '2026-02-15', '2027-02-14', '2 months deposit', '', ''],
			['C3 Property', '30000', 'Half Year', '10', '2026-03-10', '2027-03-09', 'Pay every 6 months', '', ''],
			['D4 Property', '60000', 'Yearly', '1', '2026-06-01', '2027-06-01', 'Pay once a year', '', ''],
		]
		: [
			['A1 Property', '10000', 'Monthly', '5', '2026-01-05', '2027-01-04', 'Water & electricity', '', ''],
			['B2 Property', '15000', 'Quarterly', '15', '2026-02-15', '2027-02-14', '2 months deposit', '', ''],
			['C3 Property', '30000', 'Half Year', '10', '2026-03-10', '2027-03-09', 'Pay every 6 months', '', ''],
			['D4 Property', '60000', 'Yearly', '1', '2026-06-01', '2027-06-01', 'Pay once a year', '', ''],
		];
	const csv = '\uFEFF' + [headers, ...sample].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n');
	// 所有单元格都用双引号包裹并对齐(每行每列均引号, 避免 Excel 中文/逗号乱列)
	const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
	const el = document.createElement('a');
	el.href = URL.createObjectURL(blob);
	const suffix = lang === 'en' ? '_en' : '';
	el.download = `property_import_template${suffix}.csv`;
	el.click();
	URL.revokeObjectURL(el.href);
}

// ---------------- 附件(合同/收据等) ----------------
const attPrefix = '/api/property/attachment/';

export function ListAttachments(property_id: number) {
	return request({
		url: attPrefix,
		method: 'get',
		params: { property_id },
	});
}

export function UploadAttachments(property_id: number, files: File[]) {
	const fd = new FormData();
	fd.append('property_id', String(property_id));
	files.forEach((f) => fd.append('files', f));
	return request({
		url: attPrefix,
		method: 'post',
		data: fd,
		// 交给浏览器生成 multipart boundary
		headers: { 'Content-Type': undefined },
		timeout: 120000,
	});
}

export function DelAttachment(id: number) {
	return request({
		url: attPrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

// ---------------- 自定义提醒规则 ----------------
const rulePrefix = '/api/property/reminder_rule/';

export function ListReminderRules(property_id: number) {
	return request({
		url: rulePrefix,
		method: 'get',
		params: { property_id },
	});
}

export function AddReminderRule(obj: any) {
	return request({
		url: rulePrefix,
		method: 'post',
		data: obj,
	});
}

export function UpdateReminderRule(obj: any) {
	return request({
		url: rulePrefix + obj.id + '/',
		method: 'put',
		data: obj,
	});
}

export function DelReminderRule(id: number) {
	return request({
		url: rulePrefix + id + '/',
		method: 'delete',
		data: { id },
	});
}

// ---------------- AI 助手(一句话 -> 房源草稿预览) ----------------
export function AIAssist(text: string) {
	return request({
		url: '/api/property/ai/assist/',
		method: 'post',
		data: { text },
		timeout: 60000,
	});
}

export function GetAIConfig() {
	return request({
		url: '/api/property/ai/config/',
		method: 'get',
	});
}

export function UpdateAIConfig(obj: any) {
	return request({
		url: '/api/property/ai/config/',
		method: 'put',
		data: obj,
	});
}
