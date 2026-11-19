import * as api from './api';
import {
	dict,
	UserPageQuery,
	DelReq,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { useI18n } from 'vue-i18n';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const { t } = useI18n();

	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};
	const delRequest = async ({ row }: DelReq) => {
		return await api.DelObj(row.id);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				delRequest,
			},
			rowHandle: {
				fixed: 'right',
				width: 90,
				buttons: {
					view: { show: true, text: t('message.pages.messagelog.buttons.view') },
					remove: { show: false },
					edit: { show: false },
				},
			},
			columns: {
				_index: {
					title: t('message.pages.messagelog.table.columns.index'),
					form: { show: false },
					column: {
						align: 'center',
						width: '70px',
						columnSetDisabled: true,
						formatter: (context) => {
							let index = context.index ?? 1;
							let pagination = crudExpose!.crudBinding.value.pagination;
							return ((pagination!.currentPage ?? 1) - 1) * pagination!.pageSize + index + 1;
						},
					},
				},
				tenant_name: {
					title: t('message.pages.messagelog.table.columns.tenantName'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 140 },
					form: { show: false },
				},
				bot_name: {
					title: t('message.pages.messagelog.table.columns.botName'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 130 },
					form: { show: false },
				},
				property_name: {
					title: t('message.pages.messagelog.table.columns.propertyName'),
					type: 'input',
					column: { minWidth: 120 },
					form: { show: false },
				},
				msg_type: {
					title: t('message.pages.messagelog.table.columns.msgType'),
					type: 'select',
					search: { show: true },
					dict: dict({ data: [
						{ label: '付租提醒', value: 'rent' },
						{ label: '到期提醒', value: 'maturity' },
						{ label: '年度提醒', value: 'annual' },
					]}),
					column: { minWidth: 90 },
					form: { show: false },
				},
				group_size: {
					title: t('message.pages.messagelog.table.columns.groupSize'),
					type: 'number',
					column: { minWidth: 90 },
					form: { show: false },
				},
				count: {
					title: t('message.pages.messagelog.table.columns.count'),
					type: 'number',
					column: { minWidth: 90 },
					form: { show: false },
				},
				result: {
					title: t('message.pages.messagelog.table.columns.result'),
					type: 'dict-radio',
					search: { show: true },
					dict: dict({ data: [
						{ label: '成功', value: 'success' },
						{ label: '失败', value: 'failed' },
					]}),
					column: { minWidth: 90 },
					form: { show: false },
				},
				content: {
					title: t('message.pages.messagelog.table.columns.content'),
					type: 'textarea',
					column: { width: 200, show: false },
					form: { show: false },
				},
				create_datetime: {
					title: t('message.pages.messagelog.table.columns.createDatetime'),
					type: 'datetime',
					column: { minWidth: 170 },
					form: { show: false },
				},
			},
		},
	};
};
