<template>
	<div class="gd-page">
		<!-- 工具栏 -->
		<div class="toolbar">
			<div class="left">
				<span class="title">{{ $t('message.pages.groupdoc.title') }}</span>
				<span class="count">{{ $t('message.pages.groupdoc.count', { n: files.length }) }}</span>
			</div>
			<div class="right">
				<el-input v-model="keyword" class="search" clearable :placeholder="$t('message.pages.groupdoc.searchPlaceholder')" @keyup.enter="onSearch"
					@clear="onSearch">
					<template #prefix>
						<el-icon class="search-ico" @click="onSearch" :title="$t('message.pages.groupdoc.search')"><ele-Search /></el-icon>
					</template>
				</el-input>
			</div>
		</div>

		<!-- 列表视图(表格) -->
		<div v-loading="loading" class="list-wrap">
			<el-table :data="filteredList" size="default" stripe :header-cell-style="listHeaderStyle" class="gd-table">
				<el-table-column :label="$t('message.pages.groupdoc.group')" min-width="200">
					<template #default="{ row }">
						<div class="gid-cell">
							<span class="gid" :title="row.group_id">{{ row.group_id }}</span>
							<span class="refresh-btn" :class="{ spinning: row._refreshing }" @click="refreshGroupName(row)"
								:title="row.group_name ? $t('message.pages.groupdoc.refreshName') : $t('message.pages.groupdoc.getName')">
								<el-icon><ele-Refresh /></el-icon>
							</span>
						</div>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.groupName')" min-width="180">
					<template #default="{ row }">
						<span class="gname" :class="{ dim: !row.group_name }">{{ row.group_name || '—' }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.doc')" min-width="240">
					<template #default="{ row }">
						<span class="fname" :title="row.name">{{ row.name }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.bot')" min-width="130">
					<template #default="{ row }">
						<span class="lt-muted" :class="{ dim: !row.bot_name }">{{ row.bot_name || '—' }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.size')" min-width="100" align="right">
					<template #default="{ row }">
						<span class="lt-muted">{{ fmtSize(row.size) }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.storedAt')" min-width="170">
					<template #default="{ row }">
						<span class="lt-muted">{{ row.store_time || fmtTime(row.mtime) }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.actions')" width="180" fixed="right">
					<template #default="{ row }">
						<el-button link type="primary" size="small" @click="openFile(row)">{{ $t('message.pages.groupdoc.download') }}</el-button>
						<el-button link size="small" @click="openFile(row)">{{ $t('message.pages.groupdoc.previewBtn') }}</el-button>
					</template>
				</el-table-column>
			</el-table>
			<div v-if="!loading && filteredList.length === 0" class="list-empty">
				{{ keyword ? $t('message.pages.groupdoc.emptyMatch') : $t('message.pages.groupdoc.empty') }}
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup name="groupdoc">
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { GetList, RefreshGroupName } from './api';
import { getBaseURL } from '/@/utils/baseUrl';

const { t } = useI18n();

const loading = ref(false);
const files = ref<any[]>([]);
const keyword = ref('');
const listHeaderStyle = { background: '#1f1f1f', color: '#b1b4b8', borderColor: '#2a2a2a' };

const filteredList = computed(() => {
	const kw = keyword.value.trim().toLowerCase();
	if (!kw) return files.value;
	return files.value.filter(
		(f) => f.name.toLowerCase().includes(kw) || (f.group_id || '').toLowerCase().includes(kw)
	);
});

const fmtSize = (size: any) => {
	const s = Number(size) || 0;
	if (s > 1024 * 1024) return (s / 1024 / 1024).toFixed(2) + ' MB';
	if (s > 1024) return (s / 1024).toFixed(1) + ' KB';
	return s + ' B';
};

const fmtTime = (ts: any) => {
	if (!ts) return '';
	const d = new Date(ts * 1000);
	const p = (n: number) => (n < 10 ? '0' + n : '' + n);
	return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

const refreshGroupName = async (row: any) => {
	if (row._refreshing) return;
	row._refreshing = true;
	try {
		const res: any = await RefreshGroupName(row.group_id);
		if (res.code === 2000 && res.data) {
			const name = res.data.group_name;
			if (name) {
				row.group_name = name;
				ElMessage.success(t('message.pages.groupdoc.refreshed'));
			} else if (res.data.error === 'network') {
				ElMessage.warning(t('message.pages.groupdoc.network'));
			} else if (res.data.error === 'denied') {
				ElMessage.warning(t('message.pages.groupdoc.denied'));
			} else {
				ElMessage.warning(t('message.pages.groupdoc.other'));
			}
		}
	} catch (e) {
		ElMessage.error(t('message.pages.groupdoc.refreshFail'));
	} finally {
		row._refreshing = false;
	}
};

const openFile = (f: any) => {
	window.open(getBaseURL(f.url), '_blank');
};

const onSearch = () => {
	// computed 已实时过滤
};

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetList({});
		if (res.code === 2000) files.value = res.data || [];
	} finally {
		loading.value = false;
	}
};

onMounted(load);
</script>

<style scoped lang="scss">
.gd-page {
	color: #eaeaea;

	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 16px;

		.left .title { font-size: 18px; font-weight: 600; color: #f4f4f5; }
		.left .count { margin-left: 8px; font-size: 13px; color: #b1b4b8; }
		.right { display: flex; gap: 10px; align-items: center; }
		.search { width: 280px; }
		.search-ico {
			cursor: pointer;
			color: #b1b4b8;
			transition: color 0.2s;
			&:hover { color: #409eff; }
		}
	}

	.list-wrap {
		background: #1a1a1c;
		border: 1px solid #2a2a2a;
		border-radius: 12px;
		overflow: hidden;

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
				&.spinning { color: #409eff; animation: gd-spin 1s linear infinite; }
			}
		}

		.gname {
			color: #d8dade;
			&.dim { color: #94979c; }
		}

		.fname {
			color: #f0f0f1;
			font-weight: 500;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
			max-width: 100%;
			display: inline-block;
			vertical-align: middle;
		}

		.lt-muted { color: #b1b4b8; }

		.list-empty {
			text-align: center;
			color: #94979c;
			padding: 60px 0;
		}
	}
}

@keyframes gd-spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}
</style>
