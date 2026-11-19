import * as api from './api';
import {
	dict,
	UserPageQuery,
	AddReq,
	DelReq,
	EditReq,
	compute,
	CreateCrudOptionsProps,
	CreateCrudOptionsRet,
} from '@fast-crud/fast-crud';
import { dictionary } from '/@/utils/dictionary';
import { useI18n } from 'vue-i18n';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const { t } = useI18n();

	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};
	const editRequest = async ({ form, row }: EditReq) => {
		form.id = row.id;
		return await api.UpdateObj(form);
	};
	const delRequest = async ({ row }: DelReq) => {
		return await api.DelObj(row.id);
	};
	const addRequest = async ({ form }: AddReq) => {
		return await api.AddObj(form);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
				addRequest,
				editRequest,
				delRequest,
			},
			rowHandle: {
				fixed: 'right',
				width: 200,
				buttons: {
					view: { show: true, text: t('message.pages.property.buttons.view') },
					edit: { text: t('message.pages.property.buttons.edit'), type: 'text', iconRight: 'Edit' },
					remove: { text: t('message.pages.property.buttons.delete'), type: 'text', iconRight: 'Delete' },
				},
			},
			columns: {
				_index: {
					title: t('message.pages.property.table.columns.index'),
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
				name: {
					title: t('message.pages.property.table.columns.name'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 140 },
					form: {
						rules: [{ required: true, message: t('message.pages.property.validation.nameRequired') }],
						component: { props: { clearable: true } },
					},
				},
				rent_amount: {
					title: t('message.pages.property.table.columns.rentAmount'),
					type: 'number',
					column: { minWidth: 110 },
					form: { component: { props: { min: 0, precision: 2 } } },
				},
				remind_day: {
					title: t('message.pages.property.table.columns.remindDay'),
					type: 'number',
					search: { show: false },
					column: { minWidth: 100 },
					form: {
						value: 1,
						rules: [{ required: true, message: t('message.pages.property.validation.remindDayRequired') }],
						component: { props: { min: 1, max: 31 } },
					},
				},
				pay_period: {
					title: t('message.pages.property.table.columns.payPeriod'),
					type: 'select',
					search: { show: true },
					dict: dict({
						data: [
							{ label: t('message.pages.property.period.monthly'), value: 'Monthly' },
							{ label: t('message.pages.property.period.quarterly'), value: 'Quarterly' },
							{ label: t('message.pages.property.period.halfyear'), value: 'HalfYear' },
							{ label: t('message.pages.property.period.yearly'), value: 'Yearly' },
						],
					}),
					column: { minWidth: 100 },
					form: {
						value: 'Monthly',
						component: { props: { clearable: false } },
					},
				},
				rent_start: {
					title: t('message.pages.property.table.columns.rentStart'),
					type: 'date',
					column: { minWidth: 130 },
					form: {
						component: { props: { type: 'date', valueFormat: 'YYYY-MM-DD' } },
					},
				},
				rent_end: {
					title: t('message.pages.property.table.columns.rentEnd'),
					type: 'date',
					column: { minWidth: 130 },
					form: {
						component: { props: { type: 'date', valueFormat: 'YYYY-MM-DD' } },
					},
				},
				group_id: {
					title: t('message.pages.property.table.columns.groupId'),
					type: 'input',
					column: { minWidth: 130 },
					form: { component: { props: { clearable: true } } },
				},
				owner: {
					title: t('message.pages.property.table.columns.owner'),
					type: 'select',
					column: { minWidth: 130 },
					form: {
						component: { props: { clearable: true, filterable: true } },
					},
					dict: dict({
						url: '/api/system/user/options/',  // 限本租户用户
						value: 'id',
						label: 'name',
					}),
				},
				group_size: {
					title: t('message.pages.property.table.columns.groupSize') + '（可选）',
					type: 'number',
					column: { minWidth: 100 },
					form: {
						value: 0,
						component: { props: { min: 0, max: 100, placeholder: '0=自动(缺省5)' } },
					},
				},
				line_bot: {
					title: t('message.pages.property.table.columns.lineBot'),
					type: 'select',
					column: { minWidth: 130 },
					form: {
						component: { props: { clearable: true, filterable: true } },
					},
					dict: dict({
						url: '/api/notify/linebot/options/',
						value: 'id',
						label: 'name',
					}),
				},
				calendar_in: {
					title: t('message.pages.property.table.columns.calendarIn'),
					type: 'dict-radio',
					column: {
						minWidth: 90,
						component: {
							name: 'fs-dict-switch',
							activeText: '',
							inactiveText: '',
							style: '--el-switch-on-color: var(--el-color-primary); --el-switch-off-color: #dcdfe6',
							onChange: compute((context) => {
								return () => {
									api.UpdateObj(context.row).then((res: any) => {});
								};
							}),
						},
					},
					dict: dict({ data: dictionary('button_status_bool') }),
					form: { value: true },
				},
				if_annual_notify: {
					title: t('message.pages.property.table.columns.annualNotify'),
					type: 'dict-radio',
					column: { minWidth: 90 },
					dict: dict({ data: dictionary('button_status_bool') }),
					form: { value: false },
				},
				memo: {
					title: t('message.pages.property.table.columns.memo'),
					type: 'textarea',
					column: { width: 180, show: false },
					form: { component: { props: { rows: 3 } } },
				},
				event_id_01: {
					title: t('message.pages.property.table.columns.event01'),
					column: { minWidth: 160, show: false },
					form: { show: false },
				},
				event_id_02: {
					title: t('message.pages.property.table.columns.event02'),
					column: { minWidth: 160, show: false },
					form: { show: false },
				},
			},
		},
	};
};
