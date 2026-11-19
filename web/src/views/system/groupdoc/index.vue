<template>
	<div class="gd-page">
		<!-- 工具栏 -->
		<div class="toolbar">
			<div class="left">
				<span class="title">{{ $t('message.pages.groupdoc.title') }}</span>
				<span class="count">{{ $t('message.pages.groupdoc.count', { n: total }) }}</span>
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
			<el-table :data="files" size="default" stripe :header-cell-style="listHeaderStyle" class="gd-table">
				<el-table-column :label="$t('message.pages.groupdoc.table.columns.groupId')" min-width="340">
					<template #default="{ row }">
						<span class="gid" :title="row.group_id">{{ row.group_id }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.groupdoc.doc')" min-width="240">
					<template #default="{ row }">
						<span class="fname" :title="row.name">{{ row.name }}</span>
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
			<div v-if="!loading && files.length === 0" class="list-empty">
				{{ keyword ? $t('message.pages.groupdoc.emptyMatch') : $t('message.pages.groupdoc.empty') }}
			</div>
		</div>

		<!-- 分页 -->
		<div v-if="total > pageSizeOptions[0]" class="pager">
			<el-pagination background layout="total, sizes, prev, pager, next, jumper"
				:total="total" :page-sizes="pageSizeOptions"
				v-model:current-page="page" v-model:page-size="limit"
				@current-change="load" @size-change="onSizeChange" />
		</div>
	</div>
</template>

<script lang="ts" setup name="groupdoc">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { GetList } from './api';
import { getBaseURL } from '/@/utils/baseUrl';

const loading = ref(false);
const files = ref<any[]>([]);
const total = ref(0);
const keyword = ref('');
const page = ref(1);
const limit = ref(12);
const pageSizeOptions = [12, 24, 48, 100];
const listHeaderStyle = { background: '#1f1f1f', color: '#b1b4b8', borderColor: '#2a2a2a' };

let searchTimer: any = null;
let reqSeq = 0;

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

const openFile = (f: any) => {
	window.open(getBaseURL(f.url), '_blank');
};

const onSearch = () => {
	if (searchTimer) clearTimeout(searchTimer);
	page.value = 1;
	load();
};

const onSizeChange = () => {
	page.value = 1;
	load();
};

// 输入搜索: 300ms 防抖, 避免每个字符都请求后端
watch(keyword, () => {
	if (searchTimer) clearTimeout(searchTimer);
	searchTimer = setTimeout(() => {
		page.value = 1;
		load();
	}, 300);
});

const load = async () => {
	const seq = ++reqSeq;
	loading.value = true;
	try {
		const res: any = await GetList({
			page: page.value,
			limit: limit.value,
			keyword: keyword.value.trim(),
		});
		if (seq !== reqSeq) return;
		if (res.code === 2000) {
			files.value = res.data || [];
			total.value = res.total || 0;
			if (res.page) page.value = res.page;
		}
	} finally {
		if (seq === reqSeq) loading.value = false;
	}
};

onMounted(load);

onBeforeUnmount(() => {
	if (searchTimer) clearTimeout(searchTimer);
});
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

	.pager {
		display: flex;
		justify-content: flex-end;
		margin-top: 18px;
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

		.gid {
			color: #9ec9ff;
			font-family: monospace;
			word-break: break-all;
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

</style>
