<template>
	<div class="bd-page">
		<div class="bd-head">
			<h2 class="title">{{ $t('message.pages.broadcast.title') }}</h2>
			<p class="note">{{ $t('message.pages.broadcast.note') }}</p>
			<div class="head-actions">
				<el-button size="small" class="footer-del" plain type="danger" @click="doClean" :loading="cleanLoading">
					{{ $t('message.pages.broadcast.clean') }}
				</el-button>
			</div>
		</div>

		<div class="panel">
			<!-- 群发范围 -->
			<div class="scope">
				<div class="scope-label">{{ $t('message.pages.broadcast.scope') }}</div>
				<el-radio-group v-model="scopeMode">
					<el-radio-button value="all">{{ $t('message.pages.broadcast.allGroups') }}</el-radio-button>
					<el-radio-button value="select">{{ $t('message.pages.broadcast.selectProperties') }}</el-radio-button>
				</el-radio-group>
				<span v-if="scopeMode === 'select'" class="scope-count">
					{{ $t('message.pages.broadcast.selected') }} <b class="sel">{{ selectedIds.length }}</b> {{ $t('message.pages.broadcast.properties') }}
					<el-button link type="primary" size="small" @click="clearSel">{{ $t('message.pages.broadcast.clear') }}</el-button>
				</span>
			</div>

			<!-- 选择房源(仅显示有 Group ID 的) -->
			<div v-if="scopeMode === 'select'" class="prop-pick" v-loading="propsLoading">
				<div v-if="!propsLoading && broadProps.length === 0" class="prop-empty">{{ $t('message.pages.broadcast.noProperties') }}</div>
				<div v-else class="prop-head">
					<el-checkbox :model-value="allChecked" :indeterminate="someChecked" @change="toggleAll" class="prop-check-all">{{ $t('message.pages.broadcast.selectAll') }}</el-checkbox>
					<span class="prop-head-count">{{ $t('message.pages.broadcast.total') }} <b class="sel">{{ broadProps.length }}</b> {{ $t('message.pages.broadcast.broadcastableProperties') }}</span>
				</div>
				<div class="prop-list">
					<div v-for="p in broadProps" :key="p.id" class="prop-row"
						:class="{ 'is-checked': selectedIds.includes(p.id) }" @click="toggle(p.id)">
						<el-checkbox :model-value="selectedIds.includes(p.id)" @click.stop @change="() => toggle(p.id)"
							class="prop-cb" />
						<span class="prop-name">{{ p.name }}</span>
						<span class="prop-bot">
							<el-tag v-if="p.pay_period === 'Quarterly'" size="small" effect="plain" type="warning" class="pd">{{ $t('message.pages.broadcast.quarterly') }}</el-tag>
							<el-tag v-else-if="p.pay_period === 'HalfYear'" size="small" effect="plain" type="success" class="pd">{{ $t('message.pages.broadcast.halfYear') }}</el-tag>
							<el-tag v-else-if="p.pay_period === 'Yearly'" size="small" effect="plain" class="pd-y">{{ $t('message.pages.broadcast.yearly') }}</el-tag>
							<el-tag v-else size="small" effect="plain" class="pd-m">{{ $t('message.pages.broadcast.monthly') }}</el-tag>
						</span>
						<span class="prop-bot">{{ p.line_bot_name || $t('message.pages.broadcast.noBot') }}</span>
						<span class="prop-gid" :title="p.group_id">{{ p.group_id }}</span>
					</div>
				</div>
				<div class="prop-foot">
					<span class="prop-foot-sel">{{ $t('message.pages.broadcast.selected') }} <b class="sel">{{ selectedIds.length }}</b> {{ $t('message.pages.broadcast.properties') }}</span>
					<el-button link type="primary" size="small" @click="clearSel">{{ $t('message.pages.broadcast.clear') }}</el-button>
				</div>
			</div>

			<el-input
				v-model="message"
				type="textarea"
				:rows="scopeMode === 'select' ? 8 : 12"
				maxlength="800"
				show-word-limit
				:placeholder="$t('message.pages.broadcast.messagePlaceholder')"
			/>

			<div class="actions">
				<el-button :loading="previewLoading" @click="doPreview">{{ $t('message.pages.broadcast.preview') }}</el-button>
				<el-button type="primary" :disabled="!message.trim() || !preview" @click="confirmSend">
					{{ $t('message.pages.broadcast.send') }}
				</el-button>
			</div>

			<div v-if="preview" class="preview">
				<div class="pv-title">{{ $t('message.pages.broadcast.previewTitle') }}</div>
				<div class="pv-stats">
					<span>{{ $t('message.pages.broadcast.willSendTo') }} <b>{{ preview.group_count }}</b> {{ $t('message.pages.broadcast.groups') }}</span>
					<span>{{ $t('message.pages.broadcast.quotaNote') }}</span>
				</div>
				<div v-if="preview.bots && preview.bots.length" class="pv-bots">
					<div v-for="b in preview.bots" :key="b.bot_id" class="pv-bot">
						<span class="pv-bot-name">{{ b.bot_name }}</span>
						<span>{{ b.groups }} {{ $t('message.pages.broadcast.groups') }}</span>
					</div>
				</div>
			</div>
		</div>

		<!-- 发送中/已完成 -->
		<div v-if="task" class="panel task">
			<div class="task-title">
				<span>{{ $t('message.pages.broadcast.progress') }}</span>
				<span class="task-status" :class="task.status">{{ statusText(task.status) }}</span>
			</div>
			<el-progress :percentage="progressPct" :stroke-width="12"
				:color="'#7aa5ff'" :status="task.status === 'done' ? 'success' : undefined" />
			<div class="task-stats">
				<span>{{ $t('message.pages.broadcast.sent') }} <b class="ok">{{ task.sent }}</b></span>
				<span>{{ $t('message.pages.broadcast.failed') }} <b class="bad">{{ task.failed }}</b></span>
				<span>{{ $t('message.pages.broadcast.skipped') }} <b>{{ task.skipped }}</b></span>
				<span v-if="task.total">{{ $t('message.pages.broadcast.ofTotal') }} {{ task.total }} {{ $t('message.pages.broadcast.groups') }}</span>
			</div>
			<div v-if="task.status === 'done'" class="task-done">
				<el-alert type="success" :closable="false"
					:title="$t('message.pages.broadcast.doneAlert', { sent: task.sent, failed: task.failed, skipped: task.skipped })" />
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup name="broadcast">
import { ref, computed, watch, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { GetBroadcastPreview, SendBroadcast, GetBroadcastStatus, CleanBroadcast, GetBroadcastableProperties } from './api';

const { t } = useI18n();

const message = ref('');
const preview = ref<any>(null);
const previewLoading = ref(false);
const task = ref<any>(null);
const cleanLoading = ref(false);
let pollTimer: any = null;

// 群发范围
const scopeMode = ref<'all' | 'select'>('all');
const broadProps = ref<any[]>([]);
const selectedIds = ref<number[]>([]);
const propsLoading = ref(false);

const curIds = computed(() => {
	if (scopeMode.value === 'all') return null;
	return selectedIds.value.length ? selectedIds.value : null;
});

const loadProps = async () => {
	propsLoading.value = true;
	try {
		const res: any = await GetBroadcastableProperties();
		const all: any[] = (res.data || []).filter((p: any) => p.group_id);
		broadProps.value = all;
	} catch (e) {
		console.error(e);
	} finally {
		propsLoading.value = false;
	}
};

const clearSel = () => { selectedIds.value = []; };

// 列表视图选择
const allChecked = computed(() => broadProps.value.length > 0 && selectedIds.value.length === broadProps.value.length);
const someChecked = computed(() => selectedIds.value.length > 0 && selectedIds.value.length < broadProps.value.length);
const toggle = (id: number) => {
	const i = selectedIds.value.indexOf(id);
	if (i >= 0) selectedIds.value.splice(i, 1);
	else selectedIds.value.push(id);
};
const toggleAll = (val: any) => {
	if (val) selectedIds.value = broadProps.value.map((p) => p.id);
	else selectedIds.value = [];
};

const effectiveIds = () => {
	if (scopeMode.value === 'all') return null;
	return selectedIds.value.length ? [...selectedIds.value] : [];
};

const progressPct = computed(() => {
	if (!task.value || !task.value.total) return 0;
	const done = (task.value.sent || 0) + (task.value.failed || 0) + (task.value.skipped || 0);
	return Math.min(100, Math.round((done / task.value.total) * 100));
});

const statusText = (s: string) =>
	({
		pending: t('message.pages.broadcast.status.pending'),
		running: t('message.pages.broadcast.status.running'),
		done: t('message.pages.broadcast.status.done'),
		failed: t('message.pages.broadcast.status.failed'),
	}[s] || s);

const doPreview = async () => {
	previewLoading.value = true;
	try {
		const res: any = await GetBroadcastPreview(effectiveIds());
		if (res.code === 2000 && res.data && res.data.ok) {
			preview.value = res.data;
			if (!res.data.group_count) ElMessage.warning(t('message.pages.broadcast.noBroadcastable'));
		} else {
			ElMessage.warning((res.data && res.data.error) || t('message.pages.broadcast.previewFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.broadcast.previewFailed'));
	} finally {
		previewLoading.value = false;
	}
};

const confirmSend = async () => {
	if (scopeMode.value === 'select' && selectedIds.value.length === 0) {
		ElMessage.warning(t('message.pages.broadcast.selectFirst'));
		return;
	}
	const n = preview.value ? preview.value.group_count : 0;
	const scopeNote = scopeMode.value === 'select'
		? t('message.pages.broadcast.selectedPropertiesNote', { n: selectedIds.value.length, m: n })
		: t('message.pages.broadcast.groupsNote', { n });
	ElMessageBox.confirm(
		t('message.pages.broadcast.confirmMessage', { scope: scopeNote }),
		t('message.pages.broadcast.confirmTitle'),
		{ type: 'warning', confirmButtonText: t('message.pages.broadcast.confirmSend'), cancelButtonText: t('message.pages.broadcast.cancel') }
	)
		.then(async () => {
			const res: any = await SendBroadcast(message.value.trim(), effectiveIds());
			if (res.code === 2000 && res.data && res.data.ok) {
				ElMessage.success(t('message.pages.broadcast.started'));
				startPoll(res.data.task_id);
			} else {
				ElMessage.warning((res.data && res.data.error) || t('message.pages.broadcast.sendFailed'));
			}
		})
		.catch(() => {});
};

const startPoll = (task_id: number) => {
	clearInterval(pollTimer);
	pollTimer = setInterval(async () => {
		try {
			const res: any = await GetBroadcastStatus(task_id);
			if (res.code === 2000 && res.data && res.data.ok) {
				task.value = res.data.task;
				if (res.data.task.status === 'done' || res.data.task.status === 'failed') {
					clearInterval(pollTimer);
					pollTimer = null;
				}
			}
		} catch (e) {
			clearInterval(pollTimer);
			pollTimer = null;
		}
	}, 2000);
};

const doClean = () => {
	ElMessageBox.confirm(
		t('message.pages.broadcast.cleanConfirmMessage'),
		t('message.pages.broadcast.cleanConfirmTitle'),
		{ type: 'warning', confirmButtonText: t('message.pages.broadcast.confirmClean'), cancelButtonText: t('message.pages.broadcast.cancel') }
	).then(async () => {
		cleanLoading.value = true;
		try {
			const res: any = await CleanBroadcast();
			if (res.code === 2000 && res.data && res.data.ok) {
				task.value = null;
				preview.value = null;
				if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
				ElMessage.success(t('message.pages.broadcast.cleanSuccess', { deleted: res.data.deleted, revoked: res.data.revoked }));
			} else {
				ElMessage.warning((res.data && res.data.error) || t('message.pages.broadcast.cleanFailed'));
			}
		} catch (e) {
			ElMessage.error(t('message.pages.broadcast.cleanFailed'));
		} finally {
			cleanLoading.value = false;
		}
	}).catch(() => {});
};

onMounted(() => {
	doPreview();
});

watch(scopeMode, (mode) => {
	if (mode === 'select' && broadProps.value.length === 0) loadProps();
	doPreview();
});

watch(selectedIds, (ids) => {
	if (scopeMode.value === 'select') doPreview();
}, { deep: true });

onBeforeUnmount(() => clearInterval(pollTimer));
</script>

<script lang="ts">
import { onBeforeUnmount } from 'vue';
export default { name: 'broadcast' };
</script>

<style scoped lang="scss">
.bd-page {
	max-width: 860px;
	color: #eaeaea;

	.bd-head {
		.title { font-size: 20px; font-weight: 600; color: #f4f4f5; margin: 0 0 6px; }
		.note { font-size: 13px; color: #b1b4b8; margin: 0 0 18px; }
		.head-actions { margin-bottom: 14px; }
	}

	/* 柔和主按钮(低饱和蓝, 与全站一致) */
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

	/* 危险/清理按钮柔化(与房源编辑弹窗 .dlg-del / 全站 .footer-del 一致) */
	.footer-del {
		background: rgba(245, 108, 108, 0.12) !important;
		border-color: rgba(245, 108, 108, 0.5) !important;
		color: #f56c6c !important;
		font-weight: 400 !important;

		&:hover,
		&:focus {
			background: rgba(245, 108, 108, 0.22) !important;
			border-color: rgba(245, 108, 108, 0.7) !important;
			color: #f87171 !important;
		}
	}

	.panel {
		background: #1a1a1c;
		border: 1px solid #2a2a2a;
		border-radius: 12px;
		padding: 20px;

		.scope {
			display: flex;
			align-items: center;
			gap: 12px;
			margin-bottom: 16px;

			.scope-label { font-size: 13px; color: #b1b4b8; flex-shrink: 0; }
			.scope-count { font-size: 13px; color: #b1b4b8; b.sel { color: #e6a23c; } }
		}

		.prop-pick {
			border: 1px solid #2a2a2a;
			border-radius: 10px;
			margin-bottom: 14px;
			overflow: hidden;

			.prop-empty { color: #94979c; font-size: 13px; padding: 22px 0; text-align: center; }

			.prop-head {
				display: flex; align-items: center; gap: 12px;
				padding: 10px 14px;
				background: rgba(255, 255, 255, 0.03);
				border-bottom: 1px solid #2a2a2a;
				.prop-check-all { margin-right: 4px; }
				.prop-head-count { font-size: 12px; color: #b1b4b8; b.sel { color: #e6a23c; } }
			}

			.prop-list {
				max-height: 320px;
				overflow-y: auto;

				.prop-row {
					display: flex; align-items: center; gap: 10px;
					padding: 9px 14px;
					border-bottom: 1px solid rgba(42, 42, 42, 0.6);
					cursor: pointer;
					transition: background 0.15s;

					&:last-child { border-bottom: none; }
					&:hover { background: rgba(255, 255, 255, 0.04); }
					&.is-checked { background: rgba(64, 158, 255, 0.07); }

					.prop-cb { margin-right: 2px; }
					.prop-name { flex: 1; min-width: 0; color: #eaeaea; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
					.prop-bot { flex-shrink: 0; font-size: 12px; color: #b1b4b8; }
					.pd, .pd-m { font-size: 11px; }
					.prop-gid {
						flex-shrink: 0; max-width: 220px;
						font-size: 11px; color: #94979c;
						overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
					}
				}
			}

			.prop-foot {
				display: flex; align-items: center; justify-content: flex-end; gap: 6px;
				padding: 8px 14px;
				border-top: 1px solid #2a2a2a;
				background: rgba(255, 255, 255, 0.02);
				.prop-foot-sel { font-size: 12px; color: #b1b4b8; b.sel { color: #e6a23c; } }
			}
		}

		.actions {
			margin-top: 14px;
			display: flex;
			gap: 10px;
		}

		.preview {
			margin-top: 18px;
			border-top: 1px dashed rgba(255, 255, 255, 0.1);
			padding-top: 16px;

			.pv-title { font-size: 15px; font-weight: 600; color: #f0f0f1; margin-bottom: 10px; }
			.pv-stats {
				display: flex; gap: 18px; flex-wrap: wrap;
				font-size: 13px; color: #b1b4b8;
				b { color: #f0f0f1; }
			}
			.pv-bots {
				margin-top: 12px;
				display: flex; flex-direction: column; gap: 8px;
				.pv-bot {
					display: flex; gap: 16px; font-size: 13px;
					.pv-bot-name { font-weight: 600; color: #f0f0f1; min-width: 140px; }
					span { color: #b1b4b8; }
				}
			}
		}

		&.task { margin-top: 16px; }

		.task-title {
			display: flex; justify-content: space-between; align-items: center;
			font-size: 15px; font-weight: 600; color: #f0f0f1; margin-bottom: 12px;

			.task-status {
				font-size: 12px;
				&.done { color: #67c23a; }
				&.running, &.pending { color: #9ec9ff; }
				&.failed { color: #f56c6c; }
			}
		}

		.task-stats {
			margin-top: 10px;
			display: flex; gap: 16px; flex-wrap: wrap;
			font-size: 13px; color: #b1b4b8;
			b.ok { color: #67c23a; }
			b.bad { color: #f56c6c; }
			b { color: #f0f0f1; }
		}

		.task-done { margin-top: 14px; }
	}
}
</style>