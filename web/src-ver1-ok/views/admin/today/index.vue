<template>
	<div class="today">
		<!-- 工具栏 -->
		<div class="toolbar">
			<div class="left">
				<span class="title">今日消息</span>
				<span class="count" v-if="total >= 0">{{ $t('message.pages.today.count', { n: total }) }}</span>
			</div>
			<div class="right">
				<el-select v-model="statusFilter" class="status-pick" :placeholder="$t('message.pages.today.statusAll')" clearable>
					<el-option :label="$t('message.pages.today.statusAll')" value="" />
					<el-option :label="$t('message.pages.today.stPending')" value="pending" />
					<el-option :label="$t('message.pages.today.stSent')" value="sent" />
					<el-option :label="$t('message.pages.today.stFailed')" value="failed" />
					<el-option :label="$t('message.pages.today.stBlocked')" value="blocked" />
				</el-select>
				<el-input v-model="keyword" class="search-inp" :placeholder="$t('message.pages.today.searchPlaceholder')" clearable>
					<template #prefix><el-icon class="search-ico"><ele-Search /></el-icon></template>
				</el-input>
				<el-date-picker v-model="qdate" type="date" value-format="YYYY-MM-DD" :clearable="false"
					:disabled-date="(d) => d.getTime() > Date.now()" class="date-pick"
					:placeholder="$t('message.pages.today.pickDate')" />
				<el-button class="reload-btn" :loading="loading" @click="load">
					<el-icon style="margin-right: 4px"><ele-Refresh /></el-icon>{{ $t('message.pages.today.refresh') }}
				</el-button>
			</div>
		</div>

		<!-- 状态统计(点击可筛选) -->
		<div class="stat-row">
			<template v-for="c in statChips" :key="c.key">
				<div class="chip" :class="[`chip-${c.key}`, { active: statusFilter === c.key, 'is-all': c.key === 'total' == !statusFilter }]"
					v-if="c.count > 0 || c.key === 'total'" :title="$t('message.pages.today.filterByStatus')" @click="toggleStatus(c.key)">
					<span class="v">{{ c.count }}</span>
					<span class="l">{{ c.label }}</span>
				</div>
			</template>
		</div>

		<!-- 空态 -->
		<div v-if="!total && !loading" class="empty">
			<div class="empty-ico"><el-icon><ele-CircleCheck /></el-icon></div>
			<div class="empty-txt">{{ $t('message.pages.today.empty') }}</div>
		</div>

		<!-- 列表 -->
		<div v-loading="loading" class="list-wrap" v-else>
			<div v-if="!filtered.length && !loading" class="no-match">{{ $t('message.pages.today.noMatch') }}</div>
			<template v-else>
				<el-table :data="pagedList" size="default" stripe :header-cell-style="listHeaderStyle" class="today-table">
				<el-table-column :label="$t('message.pages.today.tenant')" min-width="150">
					<template #default="{ row }">
						<span class="tname">{{ row.tenant_name }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.property')" min-width="150">
					<template #default="{ row }">
						<span class="pname" :title="row.name">{{ row.name }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.kind')" width="110">
					<template #default="{ row }">
						<span class="kind-tag" :class="`kind-${row.kind}`">{{ kindLabel(row) }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.term')" min-width="170">
					<template #default="{ row }">
						<span class="lt-muted">{{ termText(row) }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.group')" min-width="210">
					<template #default="{ row }">
						<div class="gid-cell">
							<span class="gid" :title="row.group_id || '—'">{{ row.group_id || '—' }}</span>
							<span v-if="row.group_id" class="refresh-btn" :class="{ spinning: row._refreshing }"
								@click="refreshGroupName(row)" :title="$t('message.pages.today.refreshName')">
								<el-icon><ele-Refresh /></el-icon>
							</span>
						</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.groupName')" min-width="150">
					<template #default="{ row }">
						<span class="gname" :class="{ dim: !row.group_name }">{{ row.group_name || '—' }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.bot')" min-width="130">
					<template #default="{ row }">
						<span class="lt-muted" :class="{ dim: !row.bot_name }">{{ row.bot_name || '—' }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.today.status')" width="130" align="center">
					<template #default="{ row }">
						<span class="status-badge" :class="`st-${row.status}`">{{ statusText(row) }}</span>
					</template>
				</el-table-column>
			</el-table>
				<div class="pager" v-if="filtered.length > pageSize">
					<el-pagination background layout="total, sizes, prev, pager, next"
						:total="filtered.length" :page-sizes="[50, 100, 200]"
						v-model:current-page="pageNo" v-model:page-size="pageSize" />
				</div>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts" name="adminToday">
import { ref, computed, watch, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { getTodayMessages, RefreshGroupNameByProperty } from './api';

const { t } = useI18n();
const listHeaderStyle = { background: '#1f1f1f', color: '#b1b4b8', borderColor: '#2a2a2a' };
const loading = ref(false);
const qdate = ref<string>('');
const items = ref<any[]>([]);
const stats = ref<any>({ total: 0, pending: 0, sent: 0, failed: 0, blocked: 0 });
const total = computed<number>(() => Number(stats.value?.total) || items.value.length || 0);

// 搜索 / 状态筛选 / 分页(前端过滤, 不改后端)
const keyword = ref('');
const statusFilter = ref('');
const pageNo = ref(1);
const pageSize = ref(50);

const filtered = computed(() => {
	const kw = keyword.value.trim().toLowerCase();
	const st = statusFilter.value;
	return items.value.filter((it) => {
		if (st && it.status !== st) return false;
		if (!kw) return true;
		return (it.tenant_name || '').toLowerCase().includes(kw)
			|| (it.name || '').toLowerCase().includes(kw)
			|| (it.group_id || '').toLowerCase().includes(kw);
	});
});

const pagedList = computed(() => {
	const start = (pageNo.value - 1) * pageSize.value;
	return filtered.value.slice(start, start + pageSize.value);
});

watch([keyword, statusFilter], () => {
	pageNo.value = 1;
});

const statChips = computed(() => [
	{ key: 'total', count: total.value, label: t('message.pages.today.statTotal') },
	{ key: 'pending', count: stats.value.pending ?? 0, label: t('message.pages.today.statPending') },
	{ key: 'sent', count: stats.value.sent ?? 0, label: t('message.pages.today.statSent') },
	{ key: 'failed', count: stats.value.failed ?? 0, label: t('message.pages.today.statFailed') },
	{ key: 'blocked', count: stats.value.blocked ?? 0, label: t('message.pages.today.statBlocked') },
]);

// 点统计卡牌筛选状态, 再点一次取消
const toggleStatus = (key: string) => {
	if (key === 'total') {
		statusFilter.value = '';
	} else {
		statusFilter.value = statusFilter.value === key ? '' : key;
	}
};

const KIND_LABELS: Record<string, string> = {
	rent: t('message.pages.today.kindRent'),
	maturity: t('message.pages.today.kindMaturity'),
	utility: t('message.pages.today.kindUtility'),
	custom: t('message.pages.today.kindCustom'),
};
const kindLabel = (row: any) => {
	if (row.kind === 'custom' && row.rule_name) return row.rule_name;
	return KIND_LABELS[row.kind] || row.kind;
};

const PAY_LABELS: Record<string, string> = {
	Monthly: t('message.pages.today.payMonthly'),
	Quarterly: t('message.pages.today.payQuarterly'),
	HalfYear: t('message.pages.today.payHalfYear'),
	Yearly: t('message.pages.today.payYearly'),
};
const termText = (row: any) => {
	if (!row.rent_start && !row.rent_end) return '—';
	const s = row.rent_start ? row.rent_start.slice(0, 10) : '?';
	const e = row.rent_end ? row.rent_end.slice(0, 10) : '?';
	const money = row.rent_amount ? ` · ${row.rent_amount}` : '';
	return `${s} ~ ${e}${money}`;
};

const STATUS_TEXT: Record<string, string> = {
	pending: t('message.pages.today.stPending'),
	sent: t('message.pages.today.stSent'),
	failed: t('message.pages.today.stFailed'),
	blocked: t('message.pages.today.stBlocked'),
};
const BLOCK_TXT: Record<string, string> = {
	no_group: t('message.pages.today.blockNoGroup'),
	no_bot: t('message.pages.today.blockNoBot'),
	bot_inactive: t('message.pages.today.blockBotInactive'),
};
const statusText = (row: any) => {
	if (row.status === 'blocked' && row.blocked_reason) {
		return `${STATUS_TEXT.blocked}·${BLOCK_TXT[row.blocked_reason] || row.blocked_reason}`;
	}
	return STATUS_TEXT[row.status] || row.status;
};

const load = async () => {
	loading.value = true;
	pageNo.value = 1;
	try {
		const res: any = await getTodayMessages(qdate.value || undefined);
		if (res.code === 2000 && res.data) {
			items.value = (res.data.items || []).map((it: any) => ({ ...it, _refreshing: false }));
			stats.value = res.data.stats || {};
		}
	} catch (e) {
		ElMessage.error(t('message.pages.today.loadFail'));
	} finally {
		loading.value = false;
	}
};

const refreshGroupName = async (row: any) => {
	if (row._refreshing) return;
	row._refreshing = true;
	try {
		const res: any = await RefreshGroupNameByProperty(row.prop_id);
		if (res.code === 2000 && res.data) {
			const name = res.data.group_name;
			if (name) {
				row.group_name = name;
			} else if (res.data.error === 'network') {
				ElMessage.warning(t('message.pages.today.network'));
			} else if (res.data.error === 'denied') {
				ElMessage.warning(t('message.pages.today.denied'));
			} else {
				ElMessage.warning(t('message.pages.today.refreshOther'));
			}
		}
	} catch (e) {
		ElMessage.error(t('message.pages.today.refreshFail'));
	} finally {
		row._refreshing = false;
	}
};

onMounted(load);
</script>

<style scoped lang="scss">
.today {
	--cn-text: #eaeaea;
	--cn-muted: #b1b4b8;
	--cn-border: #2a2a2a;
	color: var(--cn-text);

	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;

		.left .title { font-size: 18px; font-weight: 600; color: #f4f4f5; }
		.left .count { margin-left: 8px; font-size: 13px; color: #b1b4b8; }
		.right { display: flex; gap: 10px; align-items: center; }

		.search-inp {
			width: 240px;
			:deep(.el-input__wrapper) {
				background: #1a1a1c;
				box-shadow: 0 0 0 1px var(--cn-border) inset;
			}
			:deep(.el-input__inner) { color: var(--cn-text); }
		}

		.search-ico { color: #b1b4b8; }

		.status-pick {
			width: 140px;
			:deep(.el-input__wrapper) {
				background: #1a1a1c;
				box-shadow: 0 0 0 1px var(--cn-border) inset;
			}
			:deep(.el-input__inner) { color: var(--cn-text); }
		}

		.date-pick {
			width: 160px;
			:deep(.el-input__wrapper) {
				background: #1a1a1c;
				box-shadow: 0 0 0 1px var(--cn-border) inset;
				color: var(--cn-text);
			}
			:deep(.el-input__inner) { color: var(--cn-text); }
		}

		.reload-btn {
			background: rgba(64, 158, 255, 0.2);
			border-color: rgba(64, 158, 255, 0.35);
			color: #9ec9ff;
			&:hover, &:focus {
				background: rgba(64, 158, 255, 0.3);
				border-color: rgba(64, 158, 255, 0.5);
				color: #bcd9ff;
			}
		}
	}

	.stat-row {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		margin-bottom: 18px;

		.chip {
			display: inline-flex;
			align-items: baseline;
			gap: 8px;
			padding: 10px 16px;
			border-radius: 12px;
			background: #1a1a1c;
			border: 1px solid var(--cn-border);
			cursor: pointer;
			user-select: none;
			transition: border-color 0.15s, background 0.15s;

			&:hover { border-color: #3a3a3a; }

			&.active {
				border-color: rgba(64, 158, 255, 0.55);
				box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.25) inset;
			}

			.v { font-size: 20px; font-weight: 600; font-family: monospace; }
			.l { font-size: 13px; color: var(--cn-muted); }

			&.chip-total .v { color: #9ec9ff; }
			&.chip-pending .v { color: #e6a23c; }
			&.chip-sent .v { color: #67c23a; }
			&.chip-failed .v { color: #f56c6c; }
			&.chip-blocked .v { color: #f7665b; }
		}
	}

	.empty {
		text-align: center;
		padding: 80px 0;
		color: var(--cn-muted);

		.empty-ico { font-size: 42px; color: #37373a; margin-bottom: 12px; }
		.empty-txt { font-size: 14px; }
	}

	.list-wrap {
		background: #1a1a1c;
		border: 1px solid var(--cn-border);
		border-radius: 12px;
		overflow: hidden;

		.no-match {
			padding: 48px 0;
			text-align: center;
			color: var(--cn-muted);
			font-size: 14px;
		}

		.pager {
			display: flex;
			justify-content: flex-end;
			padding: 14px 16px;
			border-top: 1px solid var(--cn-border);

			:deep(.el-pagination.is-background .el-pager li) {
				background: #212121;
				color: #b1b4b8;
				&.is-active { background: rgba(64, 158, 255, 0.28); color: #9ec9ff; }
			}
			:deep(.el-pagination.is-background .btn-prev),
			:deep(.el-pagination.is-background .btn-next) {
				background: #212121;
				color: #b1b4b8;
			}
			:deep(.el-pagination .el-select .el-input__wrapper) {
				background: #1a1a1c;
				box-shadow: 0 0 0 1px var(--cn-border) inset;
			}
			:deep(.el-pagination__total) { color: var(--cn-muted); }
		}

		:deep(.el-table) {
			--el-table-border-color: #2a2a2a;
			--el-table-bg-color: transparent;
			--el-table-tr-bg-color: transparent;
			--el-table-header-bg-color: transparent;
			--el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
			--el-table-text-color: #d8dade;
			--el-table-header-text-color: #b1b4b8;

			background: transparent;
			.el-table__cell { color: #d8dade; }
		}
	}

	.tname { color: #f4f4f5; font-weight: 500; }
	.pname { color: #d8dade; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.lt-muted { color: #9b9da1; font-size: 13px; }
	.dim { color: #6a6c70; }

	.kind-tag {
		display: inline-block;
		padding: 2px 10px;
		border-radius: 999px;
		font-size: 12px;
		&.kind-rent { background: rgba(64, 158, 255, 0.16); color: #9ec9ff; }
		&.kind-maturity { background: rgba(230, 162, 60, 0.16); color: #e6a23c; }
		&.kind-utility { background: rgba(103, 194, 58, 0.16); color: #95d475; }
		&.kind-custom { background: rgba(124, 93, 250, 0.18); color: #b0a3ff; }
	}

	.gid-cell {
		display: flex;
		align-items: center;
		gap: 6px;

		.gid {
			color: #9ec9ff;
			font-family: monospace;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
		}

		.refresh-btn {
			color: #7d8188;
			cursor: pointer;
			display: inline-flex;
			align-items: center;
			flex-shrink: 0;
			transition: color 0.15s;
			&:hover { color: #409eff; }
			&.spinning svg { animation: today-spin 0.8s linear infinite; }
		}
	}

	.gname { color: #d8dade; }

	.status-badge {
		display: inline-block;
		padding: 3px 10px;
		border-radius: 999px;
		font-size: 12px;
		white-space: nowrap;

		&.st-pending { background: rgba(230, 162, 60, 0.14); color: #e6a23c; }
		&.st-sent { background: rgba(103, 194, 58, 0.14); color: #95d475; }
		&.st-failed { background: rgba(245, 108, 108, 0.14); color: #f56c6c; }
		&.st-blocked { background: rgba(245, 108, 108, 0.22); color: #f78f8f; }
	}
}

@keyframes today-spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}
</style>