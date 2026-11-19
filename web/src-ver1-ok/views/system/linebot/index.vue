<template>
	<div class="lb-page">
		<div class="toolbar">
			<div class="left">
				<span class="title">{{ $t('message.pages.linebot.title') }}</span>
				<span class="count">{{ $t('message.pages.linebot.count', { n: bots.length }) }}</span>
				<span class="note">{{ $t('message.pages.linebot.note') }}</span>
			</div>
			<el-button v-if="bots.length > 1" class="refresh-all-btn"
				:loading="refreshingAll" @click="refreshAll">
				<el-icon><ele-Refresh /></el-icon>
				{{ $t('message.pages.linebot.refreshAll') }}
			</el-button>
		</div>

		<div v-loading="loading" class="cards">
			<div v-if="!loading && bots.length === 0" class="empty">{{ $t('message.pages.linebot.empty') }}</div>
			<div v-for="bot in bots" :key="bot.id" class="card">
				<div class="card-head">
					<span class="nm">{{ bot.name }}</span>
					<span class="badges">
						<el-tag v-if="bot.is_default" size="small" effect="plain" type="primary">{{ $t('message.pages.linebot.platformDefault') }}</el-tag>
						<el-tag :type="bot.is_active ? 'success' : 'danger'" size="small" effect="plain">
							{{ bot.is_active ? $t('message.pages.linebot.enabled') : $t('message.pages.linebot.disabled') }}
						</el-tag>
					</span>
				</div>

				<div class="row quota-row">
					<span class="k">{{ $t('message.pages.linebot.monthlyQuotaShort') }}</span>
					<span class="v">
						<span class="quota-num">
							{{ bot.quota ? fmtUsed(bot.quota) : '—' }} / {{ bot.quota && bot.quota.limit ? bot.quota.limit : '—' }}
						</span>
						<el-progress v-if="bot.quota && bot.quota.limit" class="quota-bar"
							:percentage="usagePct(bot.quota)" :stroke-width="6"
							:color="quotaColor(bot.quota)" :show-text="false" />
						<span class="refresh-btn" :class="{ spinning: bot._refreshing }"
							@click="refreshQuota(bot)" :title="$t('message.pages.linebot.refreshQuota')">
							<el-icon><ele-Refresh /></el-icon>
						</span>
					</span>
				</div>



				<div class="row"><span class="k">Bot Code</span><span class="v">{{ bot.bot_code }}</span></div>
				<div class="row"><span class="k">Channel ID</span><span class="v">{{ bot.channel_id || '—' }}</span></div>
				<div class="row"><span class="k">Basic ID</span><span class="v">{{ bot.basic_id || '—' }}</span></div>

				<div class="row"><span class="k">{{ $t('message.pages.linebot.credentials') }}</span>
					<span class="v sec">
						{{ bot.has_channel_secret ? $t('message.pages.linebot.secretSet', { tail: bot.channel_secret_tail }) : $t('message.pages.linebot.secretNotSet') }}
						<span class="dot"></span>
						{{ bot.has_channel_access_token ? $t('message.pages.linebot.tokenSet', { tail: bot.channel_access_token_tail }) : $t('message.pages.linebot.tokenNotSet') }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup name="linebot">
import { ref, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { GetList, GetUsage } from './api';

const { t } = useI18n();

interface BotView {
	id: number;
	name: string;
	bot_code: string;
	channel_id: string;
	basic_id: string;
	is_default: boolean;
	is_active: boolean;
	has_channel_secret: boolean;
	has_channel_access_token: boolean;
	channel_secret_tail: string;
	channel_access_token_tail: string;
	quota?: { used?: number; limit?: number; local_used?: number; source?: string };
	[key: string]: any;
}

const bots = ref<BotView[]>([]);
const loading = ref(false);
const refreshingAll = ref(false);

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetList({ page: 1, limit: 100 });
		bots.value = (res.data || []).map((b: any) => ({ ...b }));
	} finally {
		loading.value = false;
	}
};

const fmtUsed = (q: any) => (q && q.used !== undefined && q.used !== null ? q.used : '—');
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

const refreshQuota = async (bot: BotView) => {
	if (bot._refreshing) return;
	bot._refreshing = true;
	try {
		const res: any = await GetUsage(bot.id, true);
		if (res.code === 2000 && res.data) {
			bot.quota = res.data;
			ElMessage.success(t('message.pages.linebot.refreshSuccess', { name: bot.name }));
		} else {
			bot.quota = null;
			ElMessage.warning(t('message.pages.linebot.refreshFailNetwork', { name: bot.name }));
		}
	} catch (e) {
		bot.quota = null;
		ElMessage.error(t('message.pages.linebot.refreshFail'));
	} finally {
		bot._refreshing = false;
	}
};

const refreshAll = async () => {
	if (refreshingAll.value) return;
	if (bots.value.length === 0) return;
	refreshingAll.value = true;
	let ok = 0;
	let fail = 0;
	const failNames: string[] = [];
	try {
		for (const bot of bots.value) {
			bot._refreshing = true;
			try {
				const res: any = await GetUsage(bot.id, true);
				if (res.code === 2000 && res.data) {
					bot.quota = res.data;
					ok++;
				} else {
					bot.quota = null;
					fail++;
					failNames.push(bot.name);
				}
			} catch (e) {
				bot.quota = null;
				fail++;
				failNames.push(bot.name);
			} finally {
				bot._refreshing = false;
			}
		}
	} finally {
		refreshingAll.value = false;
	}
	if (fail === 0) {
		ElMessage.success(t('message.pages.linebot.refreshAllDone', { n: ok }));
	} else {
		ElMessage.warning(t('message.pages.linebot.refreshAllPartial', { ok, fail, names: failNames.join('、') }));
	}
};

onMounted(load);
</script>

<style scoped lang="scss">
.lb-page {
	color: #eaeaea;
	max-width: 900px;

	.toolbar {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 16px;
		.title { font-size: 18px; font-weight: 600; color: #f4f4f5; }
		.count { margin-left: 8px; font-size: 13px; color: #b1b4b8; }
		.note { display: block; margin-top: 6px; font-size: 12px; color: #94979c; }

		.refresh-all-btn {
			flex-shrink: 0;
			margin-left: 16px;
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

	.cards {
		display: grid;
		grid-template-columns: 1fr;
		gap: 12px;

		.empty { text-align: center; color: #94979c; padding: 60px 0; }

		.card {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			padding: 16px 18px;
			display: flex;
			flex-direction: column;
			gap: 8px;

			.card-head {
				display: flex;
				justify-content: space-between;
				align-items: center;
				.nm { font-weight: 600; color: #f4f4f5; }
				.badges { display: flex; gap: 6px; }
			}

			.row {
				display: flex;
				justify-content: space-between;
				gap: 10px;
				font-size: 13px;
				.k { color: #b1b4b8; flex-shrink: 0; }
				.v { color: #d8dade; text-align: right; word-break: break-all;
					.sec { color: #e6a23c; }
					.quota-num { color: #f0f0f1; font-weight: 600; }
					.refresh-btn {
						display: inline-flex;
						align-items: center;
						margin-left: 8px;
						cursor: pointer;
						color: #94979c;
						vertical-align: middle;
						transition: color 0.2s;
						&:hover { color: #409eff; }
						&.spinning .el-icon { animation: spin 0.8s linear infinite; }
					}
				}
				.dot { margin: 0 6px; color: #7d8188; }
			}
			.quota-bar { display: inline-block; width: 120px; vertical-align: middle; margin-left: 8px; }
			@keyframes spin {
				from { transform: rotate(0deg); }
				to { transform: rotate(360deg); }
			}
		}
	}
}
</style>