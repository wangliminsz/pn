import * as api from './api';
import { UserPageQuery, CreateCrudOptionsProps, CreateCrudOptionsRet } from '@fast-crud/fast-crud';
import { useI18n } from 'vue-i18n';

export const createCrudOptions = function ({ crudExpose }: CreateCrudOptionsProps): CreateCrudOptionsRet {
	const { t } = useI18n();

	const pageRequest = async (query: UserPageQuery) => {
		return await api.GetList(query);
	};

	return {
		crudOptions: {
			request: {
				pageRequest,
			},
			actionbar: { show: false },
			rowHandle: { show: false },
			pagination: { show: true },
			columns: {
				_index: {
					title: t('message.pages.groupdoc.table.columns.index'),
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
					title: t('message.pages.groupdoc.table.columns.name'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 220 },
					form: { show: false },
				},
				tenant_id: {
					title: t('message.pages.groupdoc.table.columns.tenantId'),
					type: 'number',
					column: { minWidth: 90 },
					form: { show: false },
				},
				group_id: {
					title: t('message.pages.groupdoc.table.columns.groupId'),
					type: 'input',
					search: { show: true },
					column: { minWidth: 200 },
					form: { show: false },
				},
				size: {
					title: t('message.pages.groupdoc.table.columns.size'),
					type: 'number',
					column: {
						minWidth: 100,
						formatter: (context) => {
							let size = context.row.size ?? 0;
							if (size > 1024 * 1024) return (size / 1024 / 1024).toFixed(2) + ' MB';
							if (size > 1024) return (size / 1024).toFixed(1) + ' KB';
							return size + ' B';
						},
					},
					form: { show: false },
				},
				mtime: {
					title: t('message.pages.groupdoc.table.columns.mtime'),
					type: 'datetime',
					column: {
						minWidth: 180,
						formatter: (context) => {
							let ts = context.row.mtime;
							if (!ts) return '';
							let d = new Date(ts * 1000);
							let p = (n: number) => (n < 10 ? '0' + n : '' + n);
							return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
						},
					},
					form: { show: false },
				},
				url: {
					title: t('message.pages.groupdoc.table.columns.preview'),
					column: { minWidth: 120, slot: 'url' },
					form: { show: false },
				},
			},
		},
	};
};
