<template>
	<el-dialog :model-value="modelValue" :title="prop?.name ? $t('message.pages.reminderRule.titleWithName', { name: prop.name }) : $t('message.pages.reminderRule.title')" width="860px"
		append-to-body :close-on-click-modal="false" @closed="onClosed" @update:model-value="onModel">
		<el-form :model="form" label-width="140px" label-position="left" class="rr-form">
			<el-row :gutter="12">
				<el-col :span="12">
					<el-form-item :label="$t('message.pages.reminderRule.periods')">
						<el-select v-model="form.period" style="width:100%">
							<el-option :label="$t('message.pages.property.period.monthly')" value="Monthly" />
							<el-option :label="$t('message.pages.property.period.quarterly')" value="Quarterly" />
							<el-option :label="$t('message.pages.property.period.halfyear')" value="HalfYear" />
							<el-option :label="$t('message.pages.property.period.yearly')" value="Yearly" />
						</el-select>
					</el-form-item>
				</el-col>
				<el-col :span="12">
					<el-form-item :label="$t('message.pages.reminderRule.day')">
						<el-input-number v-model="form.day" :min="1" :max="31" style="width:100%" />
					</el-form-item>
				</el-col>
			</el-row>

			<el-form-item :label="$t('message.pages.reminderRule.content')">
				<div class="msg-field">
					<el-input v-model="form.template" type="textarea" :rows="4"
						:placeholder="$t('message.pages.reminderRule.contentPlaceholder')" />
					<div class="msg-vars">
						<span class="msg-vars-label">{{ $t('message.pages.reminderRule.vars') }}</span>
						<el-tag v-for="v in templateVars" :key="v" size="small" class="var-tag"
							@click="insertVar(v)">{{ '{' + v + '}' }}</el-tag>
					</div>
					<div class="msg-hint">{{ $t('message.pages.reminderRule.varsHint') }}</div>
				</div>
			</el-form-item>

			<el-form-item :label="$t('message.pages.reminderRule.preview')">
				<div class="rr-preview">
					<pre v-if="previewText" class="rr-preview-text">{{ previewText }}</pre>
					<div v-else class="rr-preview-empty">{{ $t('message.pages.reminderRule.previewEmpty') }}</div>
				</div>
			</el-form-item>

			<el-form-item :label="$t('message.pages.reminderRule.enabled')">
				<el-switch v-model="form.enabled" />
			</el-form-item>
		</el-form>

		<template #footer>
			<div class="dlg-footer">
				<el-button v-if="form.id" class="dlg-del" @click="onDelete">{{ $t('message.pages.reminderRule.delete') }}</el-button>
				<span class="spacer"></span>
				<el-button type="primary" :loading="saving" @click="save">{{ $t('message.pages.reminderRule.save') }}</el-button>
				<el-button @click="onClosed">{{ $t('message.pages.reminderRule.cancel') }}</el-button>
			</div>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, reactive, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { AddReminderRule, UpdateReminderRule, DelReminderRule } from '../api';

const { t } = useI18n();

const props = defineProps<{ modelValue: boolean; prop: any; editing?: any }>();
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>();

const templateVars = ['name', 'amount', 'date', 'sign'];

const emptyForm = () => ({
	id: '',
	type: 'custom',
	period: 'Monthly',
	day: 1,
	template: '',
	enabled: true,
});

const form = reactive<any>(emptyForm());
const saving = ref(false);
const previewText = ref('');

const insertVar = (v: string) => {
	form.template = (form.template || '') + '{' + v + '}';
};

const reset = () => {
	Object.assign(form, emptyForm());
	previewText.value = '';
};

const loadEditing = () => {
	if (props.editing) {
		// 兼容旧数据(水电 utility / 自定义 custom), 保留原类型, 仅展示通用字段
		Object.assign(form, emptyForm(), props.editing);
		previewText.value = props.editing.preview || '';
	} else {
		reset();
	}
};

watch(() => [props.modelValue, props.editing] as any, () => {
	if (props.modelValue) loadEditing();
});

const onModel = (v: boolean) => emit('update:modelValue', v);
const onClosed = () => emit('update:modelValue', false);

const save = async () => {
	saving.value = true;
	try {
		const payload: any = {
			...form,
			property: props.prop?.id,
		};
		if (!form.id) payload.type = 'custom';
		if (!payload.template) delete payload.template;
		const res: any = form.id
			? await UpdateReminderRule(payload)
			: await AddReminderRule(payload);
		if (res.code === 2000) {
			ElMessage.success(t('message.pages.reminderRule.saved'));
			onClosed();
			emit('saved');
		} else {
			ElMessage.error(res.msg || t('message.pages.reminderRule.saveFail'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.reminderRule.saveFail'));
	} finally {
		saving.value = false;
	}
};

const onDelete = async () => {
	try {
		await ElMessageBox.confirm(t('message.pages.reminderRule.deleteConfirm'), t('message.pages.reminderRule.deleteTitle'), { type: 'warning' });
		const res: any = await DelReminderRule(form.id);
		if (res.code === 2000) {
			ElMessage.success(t('message.pages.reminderRule.deleted'));
			onClosed();
			emit('saved');
		}
	} catch (e) { /* 取消 */ }
};
</script>

<style scoped lang="scss">
.rr-form {
	.msg-field { width: 100%; }

	.msg-vars {
		margin-top: 8px;
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 6px;

		.msg-vars-label { font-size: 12px; color: #b1b4b8; }
		.var-tag {
			cursor: pointer;
			--el-tag-bg-color: rgba(64, 158, 255, 0.1) !important;
			--el-tag-border-color: rgba(64, 158, 255, 0.35) !important;
			--el-tag-text-color: #9ec9ff !important;
			&:hover {
				--el-tag-bg-color: rgba(64, 158, 255, 0.22) !important;
				--el-tag-border-color: rgba(64, 158, 255, 0.55) !important;
				--el-tag-text-color: #bcd9ff !important;
			}
		}
	}

	.msg-hint { font-size: 11px; color: #94979c; margin-top: 4px; }

	.rr-preview {
		width: 100%;
		border: 1px solid #2a2a2a;
		border-radius: 10px;
		background: #1a1a1c;
		min-height: 60px;

		.rr-preview-text {
			margin: 0;
			padding: 12px 14px;
			font-size: 13px;
			color: #d8dade;
			white-space: pre-wrap;
			word-break: break-word;
		}
		.rr-preview-empty {
			padding: 20px;
			text-align: center;
			color: #94979c;
			font-size: 12px;
		}
	}
}

.dlg-footer { display: flex; align-items: center; .spacer { flex: 1; } }

.dlg-del {
	background: rgba(245, 108, 108, 0.12) !important;
	border-color: rgba(245, 108, 108, 0.5) !important;
	color: #f56c6c !important;
	&:hover, &:focus {
		background: rgba(245, 108, 108, 0.22) !important;
		border-color: rgba(245, 108, 108, 0.7) !important;
		color: #f87171 !important;
	}
}

.soft-ghost {
	background: transparent !important;
	border-color: #333 !important;
	color: #b1b4b8 !important;
	&:hover, &:focus { background: rgba(255, 255, 255, 0.05) !important; color: #c0c4cc !important; }
}
</style>
<style lang="scss">
/* teleport body, 非 scoped */
</style>
