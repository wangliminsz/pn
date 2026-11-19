import * as api from './api';
import { dict, UserPageQuery, AddReq, DelReq, EditReq, compute, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
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
					view: { show: false },
					edit: { text: t('message.pages.tenant.buttons.edit'), type: 'text', iconRight: 'Edit' },
					remove: { text: t('message.pages.tenant.buttons.delete'), type: 'text', iconRight: 'Delete' },
				},
			},
			columns: {
				_index: {
					title: t('message.pages.tenant.table.columns.index'),
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
					title: t('message.pages.tenant.table.columns.name'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 140 },
					form: {
						rules: [{ required: true, message: t('message.pages.tenant.validation.nameRequired') }],
						component: { props: { clearable: true } },
					},
				},
				tenant_code: {
					title: t('message.pages.tenant.table.columns.tenantCode'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 120 },
					form: {
						rules: [{ required: true, message: t('message.pages.tenant.validation.codeRequired') }],
						component: { props: { clearable: true } },
					},
				},
				contact_name: {
					title: t('message.pages.tenant.table.columns.contact'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 100 },
					form: { component: { props: { clearable: true } } },
				},
				contact_phone: {
					title: t('message.pages.tenant.table.columns.phone'),
					type: 'input',
					column: { minWidth: 120 },
					form: { component: { props: { clearable: true } } },
				},
				plan_type: {
					title: t('message.pages.tenant.table.columns.plan'),
					type: 'select',
					search: { show: true },
					dict: dict({
						data: [
							{ label: t('message.pages.tenant.plan.trial'), value: 'trial' },
							{ label: t('message.pages.tenant.plan.paid'), value: 'paid' },
						],
					}),
					column: { minWidth: 100 },
					form: {
						value: 'trial',
						rules: [{ required: true, message: t('message.pages.tenant.validation.planRequired') }],
					},
				},
				is_active: {
					title: t('message.pages.tenant.table.columns.status'),
					search: { show: true },
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
				},
				expire_time: {
					title: t('message.pages.tenant.table.columns.expire'),
					type: 'datetime',
					column: { minWidth: 160 },
					form: {
						component: { props: { type: 'datetime', valueFormat: 'YYYY-MM-DD HH:mm:ss', format: 'YYYY-MM-DD HH:mm:ss' } },
					},
				},
				google_calendar_id: {
					title: t('message.pages.tenant.table.columns.calendarId'),
					type: 'input',
					column: { minWidth: 180 },
					form: { component: { props: { clearable: true } } },
				},
				sign_name: {
					title: t('message.pages.tenant.table.columns.signName'),
					type: 'input',
					column: { minWidth: 120 },
					form: { component: { props: { clearable: true, placeholder: t('message.pages.tenant.placeholder.signName') } } },
				},
				remark: {
					title: t('message.pages.tenant.table.columns.remark'),
					type: 'textarea',
					column: { minWidth: 180, show: false },
					form: {
						component: { props: { rows: 3 } },
					},
				},
			},
		},
	};
};
