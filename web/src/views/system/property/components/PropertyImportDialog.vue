<template>
	<el-dialog v-model="visible" :title="$t('message.pages.propertyImport.title')" width="900px" top="6vh" append-to-body destroy-on-close
		:close-on-click-modal="false" :close-on-press-escape="false">
		<div class="imp-scope">
			<div class="imp-scope-ico"><el-icon><ele-UploadFilled /></el-icon></div>
			<div class="imp-scope-main">
				<div class="im-scope-name">{{ $t('message.pages.propertyImport.name') }}</div>
				<div class="im-scope-hint">
					{{ $t('message.pages.propertyImport.hint1') }}
					{{ $t('message.pages.propertyImport.hint2') }}
				</div>
				<div style="margin-top:20px; margin-bottom:20px;"></div>
			</div>
		</div>

		<!-- 第一行：下载模板 / 选择文件 -->
		<div class="imp-toolbar">
			<el-dropdown @command="downloadTemplate" trigger="click">
				<el-button class="soft-primary">
					<el-icon style="margin-right:4px"><ele-Download /></el-icon>{{ $t('message.pages.propertyImport.downloadTemplate') }}
					<el-icon style="margin-left:4px"><ele-ArrowDown /></el-icon>
				</el-button>
				<template #dropdown>
					<el-dropdown-menu>
						<el-dropdown-item command="zh-cn">{{ $t('message.pages.propertyImport.templateZh') }}</el-dropdown-item>
						<el-dropdown-item command="en">{{ $t('message.pages.propertyImport.templateEn') }}</el-dropdown-item>
					</el-dropdown-menu>
				</template>
			</el-dropdown>
			<el-upload :show-file-list="false" :auto-upload="false" accept=".csv,.xls,.xlsx"
				:on-change="onFileChange">
				<el-button type="primary">
					<el-icon style="margin-right:4px"><ele-Upload /></el-icon>{{ $t('message.pages.propertyImport.chooseFile') }}
				</el-button>
			</el-upload>
			<span v-if="uploadFile" class="file-badge">
				<el-icon style="margin-right:4px"><ele-Document /></el-icon>{{ uploadFile.name }}
			</span>
			<div class="toolbar-grow"></div>
			<el-button class="soft-ghost" :disabled="!uploadFile" @click="clearFile">{{ $t('message.pages.propertyImport.removeFile') }}</el-button>
			<el-button type="primary" :loading="previewing" :disabled="!uploadFile" @click="preview">
				<el-icon style="margin-right:4px"><ele-MagicStick /></el-icon>{{ $t('message.pages.propertyImport.preview') }}
			</el-button>
		</div>

		<!-- 预览统计 -->
		<div v-if="previewData" class="stats">
			<div class="stat"><span class="n ok">{{ previewData.stats.valid_rows }}</span><span class="l">{{ $t('message.pages.propertyImport.validRows') }}</span></div>
			<div class="stat" :class="{ warn: previewData.stats.duplicate_rows }"><span class="n">{{ previewData.stats.duplicate_rows }}</span><span class="l">{{ $t('message.pages.propertyImport.duplicateRows') }}</span></div>
			<div class="stat" :class="{ bad: previewData.stats.invalid_rows }"><span class="n">{{ previewData.stats.invalid_rows }}</span><span class="l">{{ $t('message.pages.propertyImport.invalidRows') }}</span></div>
			<div class="stat" :class="{ warn: previewData.stats.existing_warn.length }"><span class="n">{{ previewData.stats.existing_warn.length }}</span><span class="l">{{ $t('message.pages.propertyImport.existingWarn') }}</span></div>
		</div>

		<!-- 预览表格 -->
		<div v-if="previewData" class="preview-table">
			<el-table :data="previewData.rows" size="small" max-height="360" :header-cell-style="headerStyle">
				<el-table-column type="index" width="46" />
				<el-table-column :label="$t('message.pages.propertyImport.roomName')" min-width="130">
					<template #default="{ row }">
						<span :class="{ err: row.errors && row.errors.length }">{{ row.name || '—' }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.propertyImport.rent')" min-width="80">
					<template #default="{ row }">{{ row.rent_amount ? '฿' + Number(row.rent_amount).toLocaleString() : '—' }}</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.propertyImport.period')" min-width="70" align="center">
					<template #default="{ row }">
						<el-tag v-if="row.pay_period === 'Monthly'" size="small" effect="plain" type="primary">{{ $t('message.pages.property.period.monthly') }}</el-tag>
						<el-tag v-else-if="row.pay_period === 'Quarterly'" size="small" effect="plain" type="warning">{{ $t('message.pages.property.period.quarterly') }}</el-tag>
						<el-tag v-else-if="row.pay_period === 'HalfYear'" size="small" effect="plain" type="success">{{ $t('message.pages.property.period.halfyear') }}</el-tag>
						<el-tag v-else-if="row.pay_period === 'Yearly'" size="small" effect="plain">{{ $t('message.pages.property.period.yearly') }}</el-tag>
						<span v-else class="err">{{ row.pay_raw }}</span>
					</template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.propertyImport.remindDay')" prop="remind_day" min-width="70" align="center" />
				<el-table-column :label="$t('message.pages.propertyImport.rentStart')" prop="rent_start" min-width="100" />
				<el-table-column :label="$t('message.pages.propertyImport.rentEnd')" prop="rent_end" min-width="100" />
				<el-table-column :label="$t('message.pages.propertyImport.memo')" prop="memo" min-width="100">
					<template #default="{ row }"><span class="muted">{{ row.memo || '—' }}</span></template>
				</el-table-column>
				<el-table-column :label="$t('message.pages.propertyImport.status')" min-width="140">
					<template #default="{ row }">
						<span v-if="row.errors && row.errors.length" class="err">✕ {{ row.errors.join('、') }}</span>
						<span v-else-if="row.dup_status === 'duplicate'" class="warn">⧉ {{ $t('message.pages.propertyImport.duplicate') }}</span>
						<span v-else class="ok">{{ $t('message.pages.propertyImport.valid') }}</span>
					</template>
				</el-table-column>
			</el-table>
		</div>

		<!-- 预览错误汇总 -->
		<div v-if="previewData && previewData.errors.length" class="err-box">
			<div v-for="(e, i) in previewData.errors" :key="i" class="err-line">
				{{ e.row ? $t('message.pages.propertyImport.rowLine', { n: e.row }) : '' }}{{ e.msg }}
			</div>
		</div>

		<template #footer>
			<div class="dlg-footer">
				<span class="commit-tip" v-if="previewData">
					{{ $t('message.pages.propertyImport.commitTip', { n: previewData.stats.valid_rows, extra: previewData.stats.existing_warn.length ? $t('message.pages.propertyImport.sameNameNote', { list: previewData.stats.existing_warn.slice(0, 4).join('、') }) : '' }) }}
				</span>
				<div class="footer-spacer"></div>
				<el-button class="soft-ghost" @click="visible = false">{{ $t('message.pages.propertyImport.close') }}</el-button>
				<el-button type="primary" :loading="committing" :disabled="!canCommit" @click="commit">
					<el-icon style="margin-right:4px"><ele-Finished /></el-icon>{{ $t('message.pages.propertyImport.confirmImport') }}
				</el-button>
			</div>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup name="PropertyImportDialog">
import { ref, computed, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { ImportProperty, DownloadPropertyTemplate } from '../api';

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits(['update:modelValue', 'imported']);
const { t } = useI18n();
const visible = computed({
	get: () => props.modelValue,
	set: (v) => emit('update:modelValue', v),
});

const headerStyle = { background: '#1f1f1f', color: '#b1b4b8', borderColor: '#2a2a2a' };
const uploadFile = ref<File | null>(null);
const previewing = ref(false);
const committing = ref(false);
const previewData = ref<any>(null);

const onFileChange = (file: any) => {
	uploadFile.value = file.raw;
	previewData.value = null;
};

const clearFile = () => {
	uploadFile.value = null;
	previewData.value = null;
};

const downloadTemplate = (lang: 'zh-cn' | 'en' = 'zh-cn') => {
	DownloadPropertyTemplate(lang);
};

const preview = async () => {
	if (!uploadFile.value) { ElMessage.warning(t('message.pages.propertyImport.selectFileFirst')); return; }
	previewing.value = true;
	try {
		const fd = new FormData();
		fd.append('file', uploadFile.value);
		const res: any = await ImportProperty(fd, true);
		previewData.value = res.data;
		previewData.value.stats = res.data.stats || {};
		previewData.value.errors = res.data.errors || [];
		ElMessage.success(t('message.pages.propertyImport.previewReady'));
	} catch (e) {
		console.error(e);
	} finally {
		previewing.value = false;
	}
};

const canCommit = computed(() => {
	if (!previewData.value) return false;
	const s = previewData.value.stats || {};
	return s.valid_rows > 0 && s.invalid_rows === 0;
});

const commit = async () => {
	committing.value = true;
	try {
		const fd = new FormData();
		fd.append('file', uploadFile.value!);
		const res: any = await ImportProperty(fd, false);
		const d = res.data || {};
		const parts = [];
		if (d.created) parts.push(t('message.pages.propertyImport.importedNew', { n: d.created }));
		if (d.duplicates) parts.push(t('message.pages.propertyImport.skippedDup', { n: d.duplicates }));
		if (d.invalid) parts.push(t('message.pages.propertyImport.skippedErr', { n: d.invalid }));
		if (d.existing_warn && d.existing_warn.length) parts.push(t('message.pages.propertyImport.sameName', { n: d.existing_warn.length }));
		ElMessage.success(t('message.pages.propertyImport.importDone', { parts: parts.join('，') }));
		previewData.value = null;
		uploadFile.value = null;
		emit('imported');
		visible.value = false;
	} catch (e) {
		console.error(e);
	} finally {
		committing.value = false;
	}
};

watch(
	() => props.modelValue,
	(v) => {
		if (v) { uploadFile.value = null; previewData.value = null; }
	}
);
</script>

<style lang="scss">
// teleport 到 body, 用非 scoped 样式
.im-scope {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 16px 18px;
	margin-bottom: 20px;
	background: linear-gradient(90deg, rgba(64, 158, 255, 0.08), rgba(64, 158, 255, 0.02));
	border: 1px solid rgba(64, 158, 255, 0.2);
	border-radius: 12px;
}
.im-scope-ico {
	width: 42px; height: 42px;
	display: flex; align-items: center; justify-content: center;
	border-radius: 10px;
	background: rgba(64, 158, 255, 0.14);
	color: #409eff;
	font-size: 22px;
	flex-shrink: 0;
}
.im-scope-main { flex: 1; min-width: 0; }
.im-scope-name { font-weight: 400; color: #f0f0f1; font-size: 15px; }
.im-scope-hint { font-size: 12px; color: #b1b4b8; margin-top: 10px; line-height: 1.6; }
.im-scope-hint b { color: #e6a23c; font-weight: 600; }

.imp-toolbar {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 14px;
	flex-wrap: wrap;
	.toolbar-grow { flex: 1; }
	.file-badge {
		display: inline-flex;
		align-items: center;
		padding: 6px 10px;
		background: rgba(103, 194, 58, 0.12);
		border: 1px solid rgba(103, 194, 58, 0.35);
		border-radius: 6px;
		color: #93c989;
		font-size: 13px;
		max-width: 220px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
}

.stats {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
	gap: 10px;
	margin-bottom: 14px;
	.stat {
		background: #1a1a1c;
		border: 1px solid #2a2a2a;
		border-radius: 8px;
		padding: 10px;
		text-align: center;
		.n { display: block; font-size: 22px; font-weight: 600; color: #eaeaea; &.ok { color: #67c23a; } }
		.l { display: block; font-size: 12px; color: #b1b4b8; margin-top: 2px; }
		&.bad .n { color: #f56c6c; }
		&.warn .n { color: #e6a23c; }
	}
}

.preview-table {
	border: 1px solid #2a2a2a;
	border-radius: 8px;
	overflow: hidden;
	:deep(.el-table) {
		--el-table-border-color: #2a2a2a;
		--el-table-bg-color: transparent;
		--el-table-tr-bg-color: transparent;
		--el-table-header-bg-color: transparent;
		--el-table-row-hover-bg-color: rgba(255, 255, 255, 0.04);
		--el-table-text-color: #eaeaea;
		--el-table-header-text-color: #b1b4b8;
		background: transparent;
		.el-table__cell { color: #eaeaea; }
	}
	.ok { color: #67c23a; }
	.warn { color: #e6a23c; }
	.muted { color: #8f9297; }
	.err { color: #f56c6c; }
}

.err-box {
	margin-top: 12px;
	background: rgba(245, 108, 108, 0.08);
	border: 1px solid rgba(245, 108, 108, 0.3);
	border-radius: 8px;
	padding: 10px 12px;
	max-height: 120px;
	overflow: auto;
	.err-line { color: #f56c6c; font-size: 13px; line-height: 1.8; }
}

.dlg-footer { display: flex; align-items: center; gap: 8px; width: 100%; }
.footer-spacer { flex: 1; }
.commit-tip { font-size: 12px; color: #b1b4b8; line-height: 1.5; }

// ---- 柔和按钮(与附件弹窗一致) ----
.soft-primary {
	background: rgba(64, 158, 255, 0.12) !important;
	border-color: rgba(64, 158, 255, 0.5) !important;
	color: #409eff !important;
	&:hover, &:focus { background: rgba(64, 158, 255, 0.22) !important; border-color: rgba(64, 158, 255, 0.7) !important; color: #79bbff !important; }
}
.soft-ghost {
	background: transparent !important;
	border-color: #333 !important;
	color: #b1b4b8 !important;
	&:hover, &:focus { background: rgba(255, 255, 255, 0.05) !important; color: #c0c4cc !important; }
}
</style>