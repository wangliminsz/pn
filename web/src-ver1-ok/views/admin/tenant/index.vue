<template>
	<div class="page">
		<!-- 顶栏动作 -->
		<div class="page-bar">
			<el-input v-model="search" class="page-search" :placeholder="$t('message.pages.tenant.actions.searchPh')"
				clearable @keyup.enter="load" @clear="onSearch" @input="onInput">
				<template #prefix>
					<el-icon class="search-ico" @click="onSearch" title="搜索"><ele-Search /></el-icon>
				</template>
			</el-input>
			<el-radio-group v-model="expiredFilter" class="expired-filter" @change="onExpiredFilter">
				<el-radio-button value="">{{ $t('message.pages.tenant.actions.all') }}</el-radio-button>
				<el-radio-button value="1">{{ $t('message.pages.tenant.actions.expired') }}</el-radio-button>
			</el-radio-group>
			<el-button type="primary" @click="openAdd">
				<el-icon style="margin-right:4px"><ele-Plus /></el-icon>{{ $t('message.pages.tenant.dialog.addTitle') }}
			</el-button>
		</div>

		<!-- 卡片网格 -->
		<div class="card-grid">
			<div v-for="row in list" :key="row.id" class="card" @click="openEdit(row)">
				<div class="card-head">
					<div class="card-title">{{ row.name || $t('message.pages.tenant.actions.all') }}</div>
					<div class="card-tags">
						<el-tag v-if="row.is_expired" type="danger" size="small" effect="plain" class="expired-soft">
							{{ $t('message.pages.tenant.actions.expired') }}
						</el-tag>
						<el-tag :type="isPaid(row) ? 'success' : 'warning'" size="small" effect="dark"
							:class="isPaid(row) ? 'paid-soft' : 'trial-soft'">
							{{ planLabel(row.plan_type) }}
						</el-tag>
					</div>
				</div>
				<div class="card-rows">
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.managerAccounts') }}</span><span class="v manager-accounts">{{ managerAccounts(row) }}</span></div>
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.tenantCode') }}</span><span class="v">{{ row.tenant_code || '-' }}</span></div>
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.referralCode') }}</span><span class="v">{{ row.referral_code || '-' }}</span></div>
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.referralSource') }}</span><span class="v">{{ referrerName(row) }}</span></div>
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.contact') }}</span><span class="v">{{ row.contact_name || '-' }}</span></div>
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.phone') }}</span><span class="v">{{ row.contact_phone || '-' }}</span></div>
					
					<div class="row"><span class="k">Line Bot</span><span class="v">{{ botNames(row.line_bots) }}</span></div>
					
					<div class="row"><span class="k">Google ID</span><span class="v">{{ row.google_calendar_id || '-' }}</span></div>
					
					<div class="row"><span class="k">{{ $t('message.pages.tenant.cards.expire') }}</span><span class="v">{{ fmtDate(row.expire_time) }}</span></div>
				</div>
				<div class="card-foot">
					<el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain">
						{{ row.is_active ? $t('message.pages.tenant.actions.enabled') : $t('message.pages.tenant.actions.disabled') }}
					</el-tag>
					<div class="foot-actions">
						<el-button v-if="row.google_calendar_id" class="sync-btn" size="small" text
							:loading="row._syncing" @click.stop="syncCalendar(row)">
							<el-icon style="margin-right:4px"><ele-Refresh /></el-icon>{{ $t('message.pages.tenant.actions.sync') }}
						</el-button>
						<el-button class="org-btn" size="small" text @click.stop="openOrgChart(row)">
							<el-icon style="margin-right:4px"><ele-Share /></el-icon>{{ $t('message.pages.tenant.actions.orgChart') }}
						</el-button>
					</div>
				</div>
			</div>
		</div>

		<!-- 空态 -->
		<div v-if="!list.length && !loading" class="empty">{{ $t('message.pages.tenant.cards.empty') }}</div>

		<!-- 分页 -->
		<div class="page-pagination">
			<el-pagination background layout="total, prev, pager, next" :total="total" :page-size="limit"
				:current-page="page" @current-change="onPageChange" />
		</div>

		<!-- 新增/编辑弹窗 -->
		<el-dialog v-model="dialogVisible" :title="form.id ? $t('message.pages.tenant.dialog.editTitle') : $t('message.pages.tenant.dialog.addTitle')" width="560px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
			<el-form :model="form" label-width="100px" label-position="left">
				<el-form-item :label="$t('message.pages.tenant.dialog.companyName')" required>
					<el-input v-model="form.name" :placeholder="$t('message.pages.tenant.dialog.companyNamePh')" />
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.tenantCode')" required>
					<el-input v-model="form.tenant_code" :placeholder="$t('message.pages.tenant.dialog.tenantCodePh')" />
				</el-form-item>
			    <!-- <div class="flex"> -->
				<el-form-item :label="$t('message.pages.tenant.dialog.contact')">
					<el-input v-model="form.contact_name" :placeholder="$t('message.pages.tenant.dialog.contactPh')" />
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.phone')">
					<el-input v-model="form.contact_phone" :placeholder="$t('message.pages.tenant.dialog.phonePh')" />
				</el-form-item>
				<!-- </div> -->
				<el-form-item :label="$t('message.pages.tenant.dialog.plan')">
					<el-select v-model="form.plan_type" style="width:100%">
						<el-option :label="$t('message.pages.tenant.plan.trial')" value="trial" />
						<el-option :label="$t('message.pages.tenant.plan.paid')" value="paid" />
					</el-select>
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.enabled')">
					<el-switch v-model="form.is_active" />
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.lineBot')">
					<el-select v-model="form.line_bot_ids" multiple clearable filterable :placeholder="$t('message.pages.tenant.dialog.lineBotPh')"
						style="width:100%">
						<el-option v-for="b in bots" :key="b.id" :value="b.id"
							:label="$t('message.pages.tenant.dialog.botLabel', { name: b.name, code: b.bot_code, owner: b.tenant_name || $t('message.pages.tenant.dialog.botOther') })" />
					</el-select>
				</el-form-item>

				<el-form-item label="Google ID">
					<el-input v-model="form.google_calendar_id" :placeholder="$t('message.pages.tenant.dialog.googleIdPh')" />
				</el-form-item>

				<el-form-item :label="$t('message.pages.tenant.dialog.expire')">
					<el-date-picker v-model="form.expire_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss"
						format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.signature')">
					<el-input v-model="form.sign_name" :placeholder="$t('message.pages.tenant.dialog.signaturePh')" />
				</el-form-item>
				<el-form-item :label="$t('message.pages.tenant.dialog.remark')">
					<el-input v-model="form.remark" type="textarea" :rows="3" />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button v-if="form.id" class="footer-del" type="danger" plain @click="del">{{ $t('message.pages.tenant.dialog.delete') }}</el-button>
				<div class="footer-spacer"></div>
				<el-button type="primary" :loading="saving" @click="save">{{ $t('message.pages.tenant.dialog.save') }}</el-button>
				<el-button @click="dialogVisible = false">{{ $t('message.pages.tenant.dialog.cancel') }}</el-button>
			</template>
		</el-dialog>

		<!-- 组织架构 -->
		<el-dialog v-model="orgVisible" :title="$t('message.pages.tenant.actions.orgTitle', { name: orgTenant?.name || '' })" width="900px" top="6vh" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false">
			<OrgChartDialog :model-value="true" :tenant="orgTenant" :inline="true" @imported="load" />
			<template #footer>
				<el-button @click="orgVisible = false">{{ $t('message.pages.tenant.dialog.close') }}</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script lang="ts" setup name="adminTenant">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import * as api from '/@/views/system/tenant/api';
import { GetList as GetLineBots } from '/@/views/system/linebot/api';
import OrgChartDialog from './components/OrgChartDialog.vue';

const { t } = useI18n();

const list = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const limit = ref(20);
const search = ref('');
const expiredFilter = ref('');
const loading = ref(false);
const saving = ref(false);

const orgVisible = ref(false);
const orgTenant = ref<any>(null);
const bots = ref<any[]>([]);

const loadBots = async () => {
	try {
		const res: any = await GetLineBots({ page: 1, limit: 10000, name: '' });
		bots.value = (res.data || []).map((b: any) => ({ ...b, tenant_name: b.tenant_info || '' }));
	} catch (e) {
		console.error(e);
	}
};

const dialogVisible = ref(false);
const emptyForm = () => ({
	id: undefined as number | undefined,
	name: '',
	tenant_code: '',
	contact_name: '',
	contact_phone: '',
	plan_type: 'trial',
	is_active: true,
	expire_time: undefined as string | undefined,
	google_calendar_id: '',
	sign_name: '',
	remark: '',
	line_bot_ids: [] as number[],
});
const form = ref<any>(emptyForm());

// 序列化器返回的是显示标签(试用客户/正式客户), 这里做兼容
const planLabel = (v: string) => {
	if (v === 'trial' || v === '试用客户') return t('message.pages.tenant.plan.trial');
	if (v === 'paid' || v === '正式客户') return t('message.pages.tenant.plan.paid');
	return v || t('message.pages.tenant.plan.trial');
};
const isPaid = (row: any) => planLabel(row.plan_type) === t('message.pages.tenant.plan.paid');
const planToRaw = (v: string) => (v === '正式客户' || v === 'paid' ? 'paid' : 'trial');

// 卡片展示: 该租户已分配的 Line Bot 名称
const botNames = (arr: any[] | undefined) => {
	if (!arr || !arr.length) return '—';
	return arr.map((b: any) => b.name || b.bot_code).join(', ');
};

// 卡片展示: 该租户的经理登录账号列表
const managerAccounts = (row: any) => {
	const arr = row.manager_accounts;
	if (!arr || !arr.length) return '-';
	return arr.join(', ');
};

// 推荐来源租户名称
const referrerName = (row: any) => {
	const r = row.referrer_tenant_info || row.referrer_tenant;
	if (!r) return '-';
	return typeof r === 'object' ? r.name : r;
};

const fmtDate = (v: string | undefined) => {
	if (!v) return '-';
	return v.replace('T', ' ').slice(0, 16);
};

const load = async () => {
	loading.value = true;
	try {
		const res = await api.GetList({
			page: page.value,
			limit: limit.value,
			name: search.value,
			expired: expiredFilter.value,
		});
		list.value = res.data || [];
		total.value = res.total ?? res.data?.length ?? 0;
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
};

const onPageChange = (p: number) => {
	page.value = p;
	load();
};

// 切换"已到期"过滤 → 回到第一页并刷新
const onExpiredFilter = () => {
	page.value = 1;
	load();
};

// 清除搜索(点击清除图标) → 回到第一页并刷新
const onSearch = () => {
	page.value = 1;
	load();
};

// 输入过程中若清空, 也刷新回全量
const onInput = (val: string) => {
	if (val === '' && !search.value) {
		if (page.value !== 1) page.value = 1;
		load();
	}
};

const openAdd = () => {
	form.value = emptyForm();
	dialogVisible.value = true;
};

const openEdit = async (row: any) => {
	// 每次编辑前刷新 bot 列表, 保证"已分配给本租户的 bot"能准确预选(避免旧列表导致误清空)
	await loadBots();
	form.value = { ...emptyForm(), ...row, plan_type: planToRaw(row.plan_type) };
	// 预选该租户已分配的 LINE Bot
	form.value.line_bot_ids = bots.value.filter((b: any) => b.tenant === row.id).map((b: any) => b.id);
	dialogVisible.value = true;
};

const openOrgChart = (row: any) => {
	orgTenant.value = row;
	orgVisible.value = true;
};

const save = async () => {
	if (!form.value.name || !form.value.tenant_code) {
		ElMessage.warning(t('message.pages.tenant.actions.nameCodeRequired'));
		return;
	}
	saving.value = true;
	try {
		if (form.value.id) {
			await api.UpdateObj({ ...form.value, id: form.value.id });
		} else {
			await api.AddObj(form.value);
		}
		ElMessage.success(t('message.pages.tenant.actions.saveSuccess'));
		dialogVisible.value = false;
		load();
	} catch (e) {
		console.error(e);
	} finally {
		saving.value = false;
	}
};

// 超管手动同步该租户已开启日历的房源到 Google 日历(配好服务账号后一键补写老房源)
const syncCalendar = async (row: any) => {
	if (row._syncing) return;
	try {
		await ElMessageBox.confirm(
			t('message.pages.tenant.actions.syncConfirmDetail', { name: row.name, cal: row.google_calendar_id }),
			t('message.pages.tenant.actions.syncTitle'),
			{ confirmButtonText: t('message.pages.tenant.actions.syncStart'), cancelButtonText: t('message.pages.tenant.actions.cancel'), type: 'info' }
		);
	} catch (e) {
		return; // 用户取消
	}
	row._syncing = true;
	try {
		const res: any = await api.SyncTenantCalendar(row.id);
		if (res.code === 2000) {
			const parts = [t('message.pages.tenant.actions.syncOk', { n: res.data.synced })];
			if (res.data.failed) parts.push(t('message.pages.tenant.actions.syncFailN', { n: res.data.failed }));
			ElMessage.success(parts.join('，'));
			if (res.data.msgs && res.data.msgs.length) {
				console.warn('同步失败项:', res.data.msgs);
			}
		} else {
			ElMessage.error(res.msg || t('message.pages.tenant.actions.syncFail'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.tenant.actions.syncFail'));
	} finally {
		row._syncing = false;
	}
};

const del = async () => {
	try {
		// 此操作将永久删除租户「${form.value.name}」及其名下全部数据，
		// inputPlaceholder: form.value.name,
		await ElMessageBox.prompt(
			t('message.pages.tenant.actions.deleteConfirmInput', { name: form.value.name }),
			t('message.pages.tenant.actions.deleteTitle'),
			{
				confirmButtonText: t('message.pages.tenant.actions.deleteConfirm'),
				cancelButtonText: t('message.pages.tenant.actions.cancel'),
				inputPlaceholder: '',
				inputValidator: (v) => (v === form.value.name ? true : t('message.pages.tenant.actions.inputNameMismatch')),
			}
		);
	} catch (e) {
		return; // 用户取消
	}
	await api.DelObj(form.value.id);
	ElMessage.success(t('message.pages.tenant.actions.deleteSuccess'));
	dialogVisible.value = false;
	load();
};

onMounted(() => {
	load();
	loadBots();
});
</script>

<style scoped lang="scss">
.page {
	--cn-border: #2a2a2a;
	--cn-text: #eaeaea;
	--cn-muted: #b1b4b8;
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.page-bar {
	display: flex;
	align-items: center;
	gap: 12px;

	.page-search {
		width: 360px;
	}

	.search-ico {
		cursor: pointer;
		color: var(--cn-muted);
		transition: color 0.2s;
	}

	.search-ico:hover {
		color: #409eff;
	}
}

/* 已到期筛选(柔和) */
.expired-filter {
	:deep(.el-radio-button__inner) {
		background: transparent;
		border-color: #2a2a2a;
		color: #b1b4b8;
		box-shadow: none;
	}
	:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
		background: rgba(245, 108, 108, 0.12);
		border-color: rgba(245, 108, 108, 0.5);
		color: #f56c6c;
	}
	:deep(.el-radio-button__inner:hover) {
		color: #c0c4cc;
	}
}

/* 「删除」按钮：固定深色底+红字，不随 light/dark 变白（弹窗 footer 不在 .page-bar 下，需独立选择器） */
.footer-del {
	background: rgba(245, 108, 108, 0.12) !important;
	border-color: rgba(245, 108, 108, 0.5) !important;
	color: #f56c6c !important;

	&:hover,
	&:focus {
		background: rgba(245, 108, 108, 0.2) !important;
		border-color: rgba(245, 108, 108, 0.7) !important;
		color: #f87171 !important;
	}
}

/* 弹窗底栏: 删除靠左, 保存/取消靠右 */
:deep(.el-dialog__footer) {
	display: flex;
	align-items: center;
	gap: 8px;
}

.footer-spacer {
	flex: 1;
}

.card-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(345px, 1fr));
	gap: 16px;
}

/* 标签柔化(统一柔和/低饱和色, 替代刺眼高亮): 试用=琥珀, 正式=绿, 已到期=红 */
.trial-soft {
	--el-tag-bg-color: rgba(228, 175, 96, 0.16);
	--el-tag-border-color: rgba(228, 175, 96, 0.38);
	--el-tag-text-color: #c9a86a;
}

.paid-soft {
	--el-tag-bg-color: rgba(103, 194, 58, 0.14);
	--el-tag-border-color: rgba(103, 194, 58, 0.34);
	--el-tag-text-color: #93c989;
}

.expired-soft {
	--el-tag-bg-color: rgba(245, 108, 108, 0.12) !important;
	--el-tag-border-color: rgba(245, 108, 108, 0.5) !important;
	--el-tag-text-color: #f56c6c !important;
}

.card-tags {
	display: flex;
	align-items: center;
	gap: 6px;
}

.card {
	background: #1a1a1c;
	border: 1px solid var(--cn-border);
	border-radius: 12px;
	padding: 18px;
	cursor: pointer;

	&:hover {
		border-color: #409eff;
	}

	.card-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 14px;

		.card-title {
			font-size: 16px;
			font-weight: 600;
			color: var(--cn-text);
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}
	}

	.card-rows {
		display: flex;
		flex-direction: column;
		gap: 8px;

		.row {
			display: flex;
			justify-content: space-between;
			font-size: 13px;

			.k {
				color: var(--cn-muted);
			}

			.v {
				color: var(--cn-text);
				max-width: 60%;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			}

			.v.manager-accounts {
				white-space: normal;
				word-break: break-all;
				text-align: right;
			}
		}
	}

	.card-foot {
		margin-top: 14px;
		display: flex;
		align-items: center;
		justify-content: space-between;

		.foot-actions {
			display: flex;
			align-items: center;
			gap: 2px;
		}

		.sync-btn {
			color: #e6a23c;

			&:hover {
				color: #f0b661;
			}
		}

		.org-btn {
			color: #66b1ff;

			&:hover {
				color: #9ec9ff;
			}
		}
	}
}

.empty {
	text-align: center;
	color: var(--cn-muted);
	padding: 60px 0;
}

/* 柔和主按钮（低饱和淡蓝，护眼） */
:deep(.el-button--primary) {
	background: rgba(64, 158, 255, 0.2);
	border-color: rgba(64, 158, 255, 0.35);
	color: #9ec9ff;

	&:hover,
	&:focus {
		background: rgba(64, 158, 255, 0.3);
		border-color: rgba(64, 158, 255, 0.5);
		color: #bcd9ff;
	}
}

/* 柔和分页 */
:deep(.el-pagination.is-background .el-pager li) {
	background-color: #1a1a1c !important;
	color: var(--cn-muted) !important;
}

:deep(.el-pagination.is-background .el-pager li.is-active) {
	background: rgba(64, 158, 255, 0.2) !important;
	border: 1px solid rgba(64, 158, 255, 0.35);
	color: #9ec9ff !important;
}

.page-pagination {
	display: flex;
	justify-content: flex-start;
}
</style>
