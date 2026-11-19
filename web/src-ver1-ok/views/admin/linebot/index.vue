<template>
	<div class="page">
		<!-- 顶栏动作 -->
		<div class="page-bar">
			<el-input v-model="search" class="page-search" placeholder="搜索 Bot 名 / bot_code" clearable
				@keyup.enter="load" @clear="onSearch" @input="onInput">
				<template #prefix><el-icon class="search-ico" @click="onSearch" title="搜索"><ele-Search /></el-icon></template>
			</el-input>
			<el-button v-if="list.length > 1" type="primary" plain :loading="refreshingAll" @click="refreshAll">
				<el-icon style="margin-right:4px"><ele-Refresh /></el-icon>刷新全部
			</el-button>
			<el-button class="run-notify-btn" :loading="runningNotify" @click="runDailyNotify">
				<el-icon style="margin-right:4px"><ele-Promotion /></el-icon>立即执行每日提醒
			</el-button>
			<el-button :loading="exporting" @click="doExport" title="导出全部 Bot(含凭据)，用于迁移/备份">
				<el-icon style="margin-right:4px"><ele-Download /></el-icon>导出
			</el-button>
			<el-button @click="openImport" type="primary" plain title="从导出文件恢复/批量新增 Bot">
				<el-icon style="margin-right:4px"><ele-Upload /></el-icon>导入
			</el-button>
			<el-button type="primary" @click="openAdd">
				<el-icon style="margin-right:4px"><ele-Plus /></el-icon>新增 Bot
			</el-button>
		</div>

		<!-- 卡片网格 -->
		<div class="card-grid">
			<div v-for="row in list" :key="row.id" class="card" @click="openEdit(row)">
				<div class="card-head">
					<div class="card-title">
						<el-icon class="bot-ico"><ele-ChatDotRound /></el-icon>
						{{ row.name || '未命名' }}
					</div>
					<el-tag :type="row.is_default ? 'warning' : 'info'" size="small" effect="dark"
						:class="row.is_default ? 'default-soft' : 'normal-soft'">
						{{ row.is_default ? '默认' : '普通' }}
					</el-tag>
				</div>
				<div class="card-rows">
					<div class="row"><span class="k">Bot Code</span><span class="v">{{ row.bot_code || '-' }}</span></div>
					<div class="row"><span class="k">所属租户</span><span class="v">{{ row.tenant_info || row.tenant_name || '-' }}</span></div>
					<div class="row quota-row">
						<span class="k">本月用量</span>
						<span class="v quota-v">
							<span v-if="row.quota && row.quota.used !== undefined && row.quota.used !== null" class="quota-num">
								{{ row.quota.used }} / {{ row.quota.limit !== undefined && row.quota.limit !== null ? row.quota.limit : '—' }}
							</span>
							<span v-else>—</span>
							<el-progress v-if="row.quota && row.quota.limit" class="quota-bar"
								:percentage="usagePct(row.quota)" :stroke-width="6"
								:color="quotaColor(row.quota)" :show-text="false" />
						</span>
					</div>
					<div class="row"><span class="k">月消息配额</span><span class="v">{{ row.monthly_quota ? row.monthly_quota + ' 条/月' : '全局默认' }}</span></div>
				</div>
				<div class="card-foot">
					<el-tag :type="row.is_active ? 'success' : 'info'" size="small" effect="plain">
						{{ row.is_active ? '启用' : '停用' }}
					</el-tag>
				</div>
			</div>
		</div>

		<!-- 空态 -->
		<div v-if="!list.length && !loading" class="empty">暂无数据</div>

		<!-- 分页 -->
		<div class="page-pagination">
			<el-pagination background layout="total, prev, pager, next" :total="total" :page-size="limit"
				:current-page="page" @current-change="onPageChange" />
		</div>

		<!-- 新增/编辑弹窗 -->
		<el-dialog v-model="dialogVisible" :title="form.id ? '编辑 Bot' : '新增 Bot'" width="560px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
			<el-form :model="form" label-width="100px" label-position="left">
				<el-form-item label="Bot 名称" required>
					<el-input v-model="form.name" placeholder="Bot 名称" />
				</el-form-item>
				<el-form-item label="Bot Code" required>
					<el-input v-model="form.bot_code" placeholder="唯一标识" />
				</el-form-item>
				<el-form-item label="Channel ID">
					<el-input v-model="form.channel_id" placeholder="Channel ID" />
				</el-form-item>
				<el-form-item label="Basic ID">
					<el-input v-model="form.basic_id" placeholder="Basic ID" />
				</el-form-item>
				<el-form-item label="Bot User ID">
					<el-input v-model="form.bot_user_id" placeholder="LINE Bot 用户ID (U...)" />
				</el-form-item>
				<el-form-item label="Ch-Secret">
					<el-input v-model="form.channel_secret" type="password" show-password
						:placeholder="form.id ? (form.has_channel_secret ? `已设置 (末4位 ${form.channel_secret_tail})，留空不修改` : '未设置，请输入') : '必填，请输入'" />
					<div v-if="form.id && !form.has_channel_secret" class="form-tip warn">该 Bot 尚未设置 Channel Secret</div>
				</el-form-item>
				<el-form-item label="Ac-Token">
					<el-input v-model="form.channel_access_token" type="textarea" :rows="2"
						:placeholder="form.id ? (form.has_channel_access_token ? `已设置 (末4位 ${form.channel_access_token_tail})，留空不修改` : '未设置，请输入') : '必填，请输入'" />
					<div v-if="form.id && !form.has_channel_access_token" class="form-tip warn">该 Bot 尚未设置 Access Token</div>
				</el-form-item>
				<el-form-item label="是否默认">
					<el-switch v-model="form.is_default" />
				</el-form-item>
				<el-form-item label="是否启用">
					<el-switch v-model="form.is_active" />
				</el-form-item>
				<el-form-item label="月消息配额">
					<el-input-number v-model="form.monthly_quota" :min="0" :max="9999999" :controls="true"
						style="width:100%" placeholder="留空用全局配置(500)" />
					<div class="form-tip">该 Bot 的月上限；付费档(如 10000)填这里</div>
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button v-if="form.id" class="footer-del" type="danger" plain @click="del">删除</el-button>
				<div class="footer-spacer"></div>
				<el-button type="primary" :loading="saving" @click="save">保存</el-button>
				<el-button @click="dialogVisible = false">取消</el-button>
			</template>
		</el-dialog>

		<!-- 导入弹窗 -->
		<el-dialog v-model="importVisible" title="导入 LineBot" width="560px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
			<el-alert type="info" :closable="false" show-icon
				title="按 Bot Code 匹配：已存在则更新，不存在则新建；租户名不存在会跳过该行。文件含凭据明文，请勿外传。"
				style="margin-bottom:12px" />
			<el-input type="textarea" :rows="12" v-model="importText"
				placeholder='粘贴 JSON（选文件后自动填入），格式：{"bots":[...]}' />
			<div class="import-tip">
				<label class="import-file-btn">
					选择 .json 文件
					<input type="file" accept=".json,application/json,text/plain" style="display:none"
						@change="onPickImportFile" />
				</label>
			</div>
			<template #footer>
				<div class="footer-spacer"></div>
				<el-button type="primary" :loading="importLoading" @click="doImport">导入</el-button>
				<el-button @click="importVisible = false">取消</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script lang="ts" setup name="adminLinebot">
import { ref, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { downloadFile } from '/@/utils/service';
import * as api from '/@/views/system/linebot/api';

const list = ref<any[]>([]);
const total = ref(0);
const page = ref(1);
const limit = ref(20);
const search = ref('');
const loading = ref(false);
const saving = ref(false);
const refreshingAll = ref(false);
const runningNotify = ref(false);
const exporting = ref(false);
const importVisible = ref(false);
const importText = ref('');
const importLoading = ref(false);

const dialogVisible = ref(false);
const emptyForm = () => ({
	id: undefined as number | undefined,
	name: '',
	bot_code: '',
	channel_id: '',
	basic_id: '',
	bot_user_id: '',
	tenant: undefined as number | undefined,
	channel_secret: '',
	channel_access_token: '',
	has_channel_secret: false,
	has_channel_access_token: false,
	channel_secret_tail: '',
	channel_access_token_tail: '',
	is_default: false,
	is_active: true,
	monthly_quota: undefined as number | undefined,
});
const form = ref<any>(emptyForm());

const load = async () => {
	loading.value = true;
	try {
		const res = await api.GetList({ page: page.value, limit: limit.value, name: search.value });
		list.value = res.data || [];
		total.value = res.total ?? res.data?.length ?? 0;
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
};

const usagePct = (q: any) => {
	if (!q || !q.limit) return 0;
	return Math.min(100, Math.round(((q.used || 0) / q.limit) * 100));
};
const quotaColor = (q: any) => {
	const pct = usagePct(q);
	if (pct >= 90) return '#f56c6c';
	if (pct >= 70) return '#e6a23c';
	return '#67c23a';
};

const onPageChange = (p: number) => {
	page.value = p;
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

const openEdit = (row: any) => {
	form.value = { ...emptyForm(), ...row };
	dialogVisible.value = true;
};

const save = async () => {
	if (!form.value.name || !form.value.bot_code) {
		ElMessage.warning('请填写 Bot 名称和 Bot Code');
		return;
	}
	// 新增必填凭据; 编辑时已有凭据可留空(保留原值)
	if (!form.value.id || (!form.value.has_channel_secret && !form.value.channel_secret)) {
		if (!form.value.channel_secret) {
			ElMessage.warning('请填写 Channel Secret');
			return;
		}
	}
	if (!form.value.id || (!form.value.has_channel_access_token && !form.value.channel_access_token)) {
		if (!form.value.channel_access_token) {
			ElMessage.warning('请填写 Access Token');
			return;
		}
	}
	saving.value = true;
	try {
		if (form.value.id) {
			await api.UpdateObj({ ...form.value, id: form.value.id });
		} else {
			await api.AddObj(form.value);
		}
		ElMessage.success('保存成功');
		dialogVisible.value = false;
		load();
	} catch (e) {
		console.error(e);
	} finally {
		saving.value = false;
	}
};

const del = async () => {
	await ElMessageBox.confirm('确定删除该 Bot 吗？', '删除提示', { type: 'warning' });
	await api.DelObj(form.value.id);
	ElMessage.success('删除成功');
	dialogVisible.value = false;
	load();
};

const refreshAll = async () => {
	if (refreshingAll.value) return;
	refreshingAll.value = true;
	let ok = 0;
	let fail = 0;
	const failNames: string[] = [];
	try {
		const res: any = await api.GetList({ page: 1, limit: 100 });
		const all = (res.data || []) as any[];
		for (const bot of all) {
			try {
				const q: any = await api.GetUsage(bot.id, true);
				if (q.code === 2000 && q.data) {
					const row = list.value.find((r) => r.id === bot.id);
					if (row) row.quota = q.data;
					ok++;
				} else {
					const row = list.value.find((r) => r.id === bot.id);
					if (row) row.quota = null;
					fail++;
					failNames.push(bot.name || bot.bot_code);
				}
			} catch (e) {
				const row = list.value.find((r) => r.id === bot.id);
				if (row) row.quota = null;
				fail++;
				failNames.push(bot.name || bot.bot_code);
			}
		}
	} finally {
		refreshingAll.value = false;
	}
	if (fail === 0) {
		ElMessage.success(`已刷新全部 ${ok} 个 Bot 配额`);
	} else {
		ElMessage.warning(`刷新完成：成功 ${ok} 个，失败 ${fail} 个（${failNames.join('、')}）无法连接 LINE，配额暂不可用`);
	}
};

const runDailyNotify = async () => {
		if (runningNotify.value) return;
		try {
			await ElMessageBox.confirm(
				'立即对所有到期提醒执行一次发送（不等定时时间）？会按今日日期扫描全部租户的付租/到期提醒。',
				'立即执行每日提醒',
				{ type: 'warning', confirmButtonText: '立即执行', cancelButtonText: '取消' }
			);
		} catch (e) {
			return; // 取消
		}
		runningNotify.value = true;
		try {
			const res: any = await api.RunDailyNotify({});
			if (res.code === 2000) {
				const sent = res.data?.sent ?? 0;
				ElMessage.success(res.msg || `已完成，共发送 ${sent} 条提醒`);
			} else {
				ElMessage.warning(res.msg || '执行失败');
			}
		} catch (e) {
			ElMessage.error('执行失败');
		} finally {
			runningNotify.value = false;
		}
	};

	const doExport = async () => {
		if (exporting.value) return;
		exporting.value = true;
		try {
			await downloadFile({
				url: api.apiPrefix + 'export_bots/',
				method: 'get',
				filename: 'linebot_export.json',
			});
		} catch (e) {
			console.error(e);
		} finally {
			exporting.value = false;
		}
	};

	const openImport = () => {
		importText.value = '';
		importVisible.value = true;
	};

	const onPickImportFile = (e: Event) => {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			importText.value = String(reader.result || '');
		};
		reader.readAsText(file);
		input.value = '';
	};

	const doImport = async () => {
		let payload: any;
		try {
			payload = JSON.parse(importText.value);
		} catch (e) {
			ElMessage.error('JSON 解析失败，请检查格式');
			return;
		}
		importLoading.value = true;
		try {
			const res: any = await api.ImportBots(payload);
			if (res.code === 2000) {
				const d = res.data || {};
				const msg = `导入完成：新增 ${d.created ?? 0}，更新 ${d.updated ?? 0}，跳过 ${d.skipped ?? 0}`;
				if (d.errors && d.errors.length) {
					const detail = (d.errors as any[])
						.slice(0, 3)
						.map((x) => `第${x.row}行: ${x.msg}`)
						.join('；');
					ElMessage.warning(`${msg}。${detail}`);
				} else {
					ElMessage.success(msg);
				}
				importVisible.value = false;
				load();
			} else {
				ElMessage.warning(res.msg || '导入失败');
			}
		} catch (e) {
			ElMessage.error('导入失败');
		} finally {
			importLoading.value = false;
		}
	};

onMounted(() => {
	load();
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
		color: #b1b4b8;
		transition: color 0.2s;
		&:hover { color: #409eff; }
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

/* 弹窗底栏: 删除靠左, 保存/取消靠右(与租户管理一致) */
:deep(.el-dialog__footer) {
	display: flex;
	align-items: center;
	gap: 8px;
}

.footer-spacer {
	flex: 1;
}

/* 表单提示文字(如 月配额说明): 需 width:100% 使 text-align 生效 */
.form-tip {
	width: 100%;
	font-size: 12px;
	line-height: 1.5;
	color: var(--cn-muted);

	&.warn {
		color: #e6a23c;
	}
}

/* 月消息配额输入框: 文本(含 placeholder)左对齐 */
:deep(.el-input-number .el-input__inner) {
	text-align: left;
}

:deep(.el-input-number) {
	input {
		text-align: left;
	}
}

/* 标签柔化: 默认=低饱和琥珀, 普通=中性灰 */
.default-soft {
	--el-tag-bg-color: rgba(228, 175, 96, 0.16);
	--el-tag-border-color: rgba(228, 175, 96, 0.38);
	--el-tag-text-color: #c9a86a;
}

.normal-soft {
	--el-tag-bg-color: rgba(144, 147, 153, 0.14);
	--el-tag-border-color: rgba(144, 147, 153, 0.34);
	--el-tag-text-color: #a2a4a8;
}

.card-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(345px, 1fr));
	gap: 16px;
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
			display: flex;
			align-items: center;
			gap: 8px;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;

			.bot-ico {
				color: #409eff;
			}
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

			.quota-row .v {
				max-width: 70%;
			}

			.quota-v {
				display: inline-flex;
				align-items: center;
				gap: 6px;
				justify-content: flex-end;
				max-width: 70%;
				white-space: normal;

				.quota-num {
					color: #f0f0f1;
					font-weight: 600;
					flex-shrink: 0;
				}

				.quota-bar {
					width: 90px;
					flex-shrink: 0;
				}
			}
		}
	}

	.card-foot {
		margin-top: 14px;
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
