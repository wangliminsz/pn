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
					view: { show: true, text: t('message.pages.linebot.buttons.view') },
					edit: { text: t('message.pages.linebot.buttons.edit'), type: 'text', iconRight: 'Edit' },
					remove: { text: t('message.pages.linebot.buttons.delete'), type: 'text', iconRight: 'Delete' },
				},
			},
			columns: {
				_index: {
					title: t('message.pages.linebot.table.columns.index'),
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
					title: t('message.pages.linebot.table.columns.name'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 130 },
					form: {
						rules: [{ required: true, message: t('message.pages.linebot.validation.nameRequired') }],
						component: { props: { clearable: true } },
					},
				},
				bot_code: {
					title: t('message.pages.linebot.table.columns.botCode'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 130 },
					form: {
						rules: [{ required: true, message: t('message.pages.linebot.validation.botCodeRequired') }],
						component: { props: { clearable: true } },
					},
				},
				channel_id: {
					title: t('message.pages.linebot.table.columns.channelId'),
					type: 'input',
					column: { minWidth: 120 },
					form: { component: { props: { clearable: true } } },
				},
				basic_id: {
					title: t('message.pages.linebot.table.columns.basicId'),
					type: 'input',
					column: { minWidth: 120 },
					form: { component: { props: { clearable: true } } },
				},
				bot_user_id: {
					title: t('message.pages.linebot.table.columns.botUserId'),
					type: 'input',
					column: { minWidth: 170 },
					form: { component: { props: { clearable: true } } },
				},
				tenant: {
					title: t('message.pages.linebot.table.columns.tenant'),
					type: 'select',
					column: { minWidth: 140 },
					form: {
						component: { props: { clearable: true, filterable: true } },
					},
					dict: dict({
						url: '/api/tenant/tenant/options/',
						value: 'id',
						label: 'name',
					}),
				},
				channel_secret: {
					title: t('message.pages.linebot.table.columns.channelSecret'),
					type: 'input',
					column: { minWidth: 150, show: false },
					form: { component: { props: { clearable: true } } },
				},
				channel_access_token: {
					title: t('message.pages.linebot.table.columns.channelAccessToken'),
					type: 'textarea',
					column: { minWidth: 150, show: false },
					form: { component: { props: { rows: 2 } } },
				},
				is_default: {
					title: t('message.pages.linebot.table.columns.isDefault'),
					type: 'dict-radio',
					column: { minWidth: 90 },
					dict: dict({ data: [
						{ label: '默认', value: true },
						{ label: '普通', value: false },
					]}),
					form: { value: false },
				},
				is_active: {
					title: t('message.pages.linebot.table.columns.isActive'),
					type: 'dict-radio',
					column: { minWidth: 90 },
					dict: dict({ data: [
						{ label: '启用', value: true },
						{ label: '停用', value: false },
					]}),
					form: { value: true },
				},
				monthly_quota: {
					title: t('message.pages.linebot.table.columns.monthlyQuota'),
					type: 'number',
					column: { minWidth: 120 },
					form: {
						component: {
							props: { min: 0, placeholder: t('message.pages.linebot.placeholder.monthlyQuota') },
						},
					},
				},
			},
		},
	};
};
