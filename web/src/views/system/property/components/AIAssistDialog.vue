<template>
	<el-dialog :model-value="modelValue" :title="$t('message.pages.aiAssist.title')" width="820px" append-to-body
		:close-on-click-modal="false" @closed="onClosed">
		<!-- 输入区 -->
		<div class="ai-input">
			<el-input v-model="text" type="textarea" :rows="3" :placeholder="$t('message.pages.aiAssist.placeholder')" />
			<div class="ai-actions">
				<span class="ai-hint">{{ $t('message.pages.aiAssist.hint') }}</span>
				<el-button class="soft-ghost" :disabled="!text.trim() || loading" @click="parse">
					<el-icon v-if="!loading" style="margin-right:4px"><ele-MagicStick /></el-icon>
					<span v-else class="spinner"></span>
					{{ loading ? $t('message.pages.aiAssist.loading') : $t('message.pages.aiAssist.parse') }}
				</el-button>
			</div>
		</div>

		<!-- 预览确认卡 -->
		<div v-if="draft" class="ai-preview">
			<div class="pv-title">{{ $t('message.pages.aiAssist.previewTitle') }}</div>
			<div v-if="draft.missing && draft.missing.length" class="pv-missing">
				<el-icon><ele-Warning /></el-icon>
				{{ $t('message.pages.aiAssist.missing', { items: draft.missing.join('、') }) }}
			</div>
			<div v-if="draft.date_warn" class="pv-datewarn">
				<el-icon><ele-Warning /></el-icon>{{ draft.date_warn }}
			</div>
			<div class="pv-grid">
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.roomName') }}</span><el-input v-model="draft.name" :placeholder="$t('message.pages.aiAssist.roomNamePlaceholder')" /></div>
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.rentAmount') }}</span><el-input-number v-model="draft.rent_amount" :min="0" :precision="2" :controls="false" style="width:100%" /></div>
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.payPeriod') }}</span>
					<el-select v-model="draft.pay_period" style="width:100%">
						<el-option :label="$t('message.pages.property.period.monthly')" value="Monthly" />
						<el-option :label="$t('message.pages.property.period.quarterly')" value="Quarterly" />
						<el-option :label="$t('message.pages.property.period.halfyear')" value="HalfYear" />
						<el-option :label="$t('message.pages.property.period.yearly')" value="Yearly" />
					</el-select>
				</div>
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.remindDay') }}</span><el-input-number v-model="draft.remind_day" :min="1" :max="31" :controls="false" style="width:100%" /></div>
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.rentStart') }}</span><el-date-picker v-model="draft.rent_start" type="date" value-format="YYYY-MM-DD" style="width:100%" /></div>
				<div class="pv-item"><span class="k">{{ $t('message.pages.aiAssist.rentEnd') }}</span><el-date-picker v-model="draft.rent_end" type="date" value-format="YYYY-MM-DD" style="width:100%" /></div>
				<div class="pv-item">
					<span class="k">{{ $t('message.pages.aiAssist.owner') }}</span>
					<el-select v-model="draft.owner_id" filterable clearable :placeholder="$t('message.pages.aiAssist.ownerPlaceholder')" style="width:100%">
						<el-option v-for="o in ownerOptions" :key="o.id" :label="o.name" :value="o.id" />
					</el-select>
					<span v-if="draft.owner_warn" class="pv-warn">{{ $t('message.pages.aiAssist.ownerNotFound', { name: draft.owner_username }) }}</span>
				</div>
				<div class="pv-item">
					<span class="k">{{ $t('message.pages.aiAssist.lineBot') }}</span>
					<el-select v-model="draft.line_bot_id" filterable clearable :placeholder="$t('message.pages.aiAssist.lineBotPlaceholder')" style="width:100%">
						<el-option v-for="b in botOptions" :key="b.id" :label="b.name" :value="b.id" />
					</el-select>
					<span v-if="draft.bot_warn" class="pv-warn">{{ $t('message.pages.aiAssist.botNotFound', { name: draft.line_bot_name }) }}</span>
				</div>
				<div class="pv-item">
					<span class="k">{{ $t('message.pages.aiAssist.groupId') }}</span>
					<el-input v-model="draft.group_id" :placeholder="$t('message.pages.aiAssist.groupPlaceholder')" />
					<span v-if="draft.group_warn" class="pv-warn">{{ $t('message.pages.aiAssist.groupHint') }}</span>
				</div>
				<div class="pv-item full"><span class="k">{{ $t('message.pages.aiAssist.memo') }}</span><el-input v-model="draft.memo" placeholder="" /></div>
			</div>
		</div>

		<template #footer>
			<div class="dlg-footer">
				<span class="spacer"></span>
				<el-button type="primary" :loading="saving" :disabled="!draft" @click="confirmSave">{{ $t('message.pages.aiAssist.confirm') }}</el-button>
				<el-button @click="onClosed">{{ $t('message.pages.aiAssist.cancel') }}</el-button>
			</div>
		</template>
	</el-dialog>
</template>

<script lang="ts" setup>
import { ref, watch, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { request } from '/@/utils/service';
import { AIAssist, AddObj } from '../api';

const { t } = useI18n();

const props = defineProps<{ modelValue: boolean; ownerSuggestions?: string[] }>();
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>();

const text = ref('');
const draft = ref<any>(null);
const loading = ref(false);
const saving = ref(false);
const ownerOptions = ref<any[]>([]);
const botOptions = ref<any[]>([]);

const loadOptions = async () => {
	try {
		const [uo, bo]: any = await Promise.all([
			request({ url: '/api/system/user/options/', method: 'get' }),
			request({ url: '/api/notify/linebot/options/', method: 'get' }),
		]);
		ownerOptions.value = uo.data || [];
		botOptions.value = bo.data || [];
	} catch (e) {
		/* 选项加载失败不阻塞 AI 解析, 用户仍可手填 */
	}
};
onMounted(loadOptions);

const onClosed = () => emit('update:modelValue', false);

watch(() => props.modelValue, (v) => {
	if (v) {
		text.value = '';
		draft.value = null;
	}
});

const parse = async () => {
	if (!text.value.trim()) return;
	loading.value = true;
	try {
		const res: any = await AIAssist(text.value.trim());
		if (res.code === 2000 && res.data?.draft) {
			draft.value = {
				name: res.data.draft.name ?? '',
				rent_amount: res.data.draft.rent_amount,
				pay_period: res.data.draft.pay_period || 'Monthly',
				remind_day: res.data.draft.remind_day ?? 1,
				rent_start: res.data.draft.rent_start || null,
				rent_end: res.data.draft.rent_end || null,
				memo: res.data.draft.memo || '',
				missing: res.data.draft.missing || [],
				date_warn: res.data.draft.date_warn || '',
				owner_id: res.data.draft.owner_id ?? null,
				owner_username: res.data.draft.owner_username || '',
				owner_warn: res.data.draft.owner_warn || '',
				line_bot_id: res.data.draft.line_bot_id ?? null,
				line_bot_name: res.data.draft.line_bot_name || '',
				bot_warn: res.data.draft.bot_warn || '',
				group_id: res.data.draft.group_id || '',
				group_warn: res.data.draft.group_warn || '',
			};
		} else {
			ElMessage.warning(res.msg || t('message.pages.aiAssist.parseFail'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.aiAssist.parseError'));
	} finally {
		loading.value = false;
	}
};

const confirmSave = async () => {
	if (!draft.value) return;
	// 转成房源创建 payload
	const payload: any = {
		name: draft.value.name,
		rent_amount: draft.value.rent_amount ?? null,
		pay_period: draft.value.pay_period,
		remind_day: draft.value.remind_day ?? 1,
		rent_start: draft.value.rent_start,
		rent_end: draft.value.rent_end,
		owner: draft.value.owner_id ?? null,
		line_bot: draft.value.line_bot_id ?? null,
		group_id: draft.value.group_id || null,
		memo: draft.value.memo || null,
	};
	if (!payload.name) { ElMessage.warning(t('message.pages.aiAssist.nameRequired')); return; }
	if (!payload.rent_start || !payload.rent_end) { ElMessage.warning(t('message.pages.aiAssist.datesRequired')); return; }
	if (draft.value.date_warn) { ElMessage.warning(draft.value.date_warn); return; }
	saving.value = true;
	try {
		const res: any = await AddObj(payload);
		if (res.code === 2000) {
			ElMessage.success(t('message.pages.aiAssist.created'));
			onClosed();
			emit('saved');
		} else {
			ElMessage.error(res.msg || t('message.pages.aiAssist.createFail'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.aiAssist.createFail'));
	} finally {
		saving.value = false;
	}
};
</script>

<style scoped lang="scss">
.ai-input {
	.ai-actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 10px;

		.ai-hint { font-size: 12px; color: #b1b4b8; }
	}
}

.ai-preview {
	margin-top: 16px;
	border: 1px solid #2f2f33;
	border-radius: 12px;
	background: #161618;
	padding: 14px 16px;

	.pv-title { font-size: 13px; color: #eaeaea; font-weight: 600; margin-bottom: 10px; }

	.pv-missing {
		display: flex; align-items: center; gap: 6px;
		font-size: 12px; color: #e6a23c;
		background: rgba(230,162,60,.1);
		border: 1px solid rgba(230,162,60,.3);
		border-radius: 8px; padding: 6px 10px; margin-bottom: 10px;
	}
	.pv-datewarn {
		display: flex; align-items: center; gap: 6px;
		font-size: 12px; color: #f56c6c;
		background: rgba(245,108,108,.1);
		border: 1px solid rgba(245,108,108,.3);
		border-radius: 8px; padding: 6px 10px; margin-bottom: 10px;
	}
	.pv-warn {
		font-size: 12px; color: #e6a23c;
		line-height: 1.5;
	}

	.pv-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;

		.pv-item {
			display: flex; flex-direction: column; gap: 5px;
			.k { font-size: 12px; color: #b1b4b8; }
			&.full { grid-column: 1 / -1; }
		}
	}
}

.dlg-footer { display: flex; align-items: center; .spacer { flex: 1; } }

.soft-ghost {
	background: transparent !important;
	border-color: #3a3a40 !important;
	color: #c0c4cc !important;
	&:hover, &:focus { background: rgba(255,255,255,.06) !important; border-color: #4a4a52 !important; }
}

.spinner {
	width: 14px; height: 14px; border-radius: 50%;
	border: 2px solid rgba(255,255,255,.2); border-top-color: #fff;
	display: inline-block; vertical-align: -2px; margin-right: 4px;
	animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>