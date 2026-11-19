<template>
	<div class="ws">
		<!-- 头部 -->
		<div class="ws-head">
			<div>
				<h2 class="title">{{ $t('message.pages.home.workspace.title') }} <span v-if="data.tenant" class="co">· {{ data.tenant.name }}</span>
					<span v-if="data.tenant?.expire_time && !data.tenant.is_expired" class="expire-note"> {{ data.tenant.expire_time.slice(0,10) }}</span>
				</h2>
				<p class="hi">
					{{ hiText }}{{ userName }}{{ $t('message.pages.home.workspace.todayOverview') }}
					<el-tag v-if="data.tenant?.is_expired" size="small" effect="plain" class="expired-hit"
						@click="$router.push('/payment')" :title="$t('message.pages.home.workspace.expiredHit')">
						{{ $t('message.pages.home.workspace.expiredHit') }}
					</el-tag>
				</p>
			</div>
		</div>

		<!-- 统计卡 -->
		<div class="stat-grid">
			<div class="stat">
				<div class="n">{{ stats.active }}<em>/{{ stats.total }}</em></div>
				<div class="l">{{ $t('message.pages.home.workspace.activeProperties') }}</div>
			</div>
			<div class="stat">
				<div class="n">{{ stats.upcoming_7d }}</div>
				<div class="l">{{ $t('message.pages.home.workspace.upcoming3d') }}</div>
			</div>
			<div class="stat">
				<div class="n">{{ stats.ending_soon }}</div>
				<div class="l">{{ $t('message.pages.home.workspace.endingSoon') }}</div>
			</div>
			<!-- Google 日历小卡(仅经理/超管可见); 点击整卡进入设置 -->
			<div v-if="isManagerView && data.tenant" class="stat gcal-stat" @click="openGcal" :title="data.tenant.google_calendar_id ? $t('message.pages.home.workspace.gcalConfigured', { id: data.tenant.google_calendar_id }) : $t('message.pages.home.workspace.gcalNotConfiguredTitle')">
				<div class="gcal-main">
					<div class="gcal-title">{{ $t('message.pages.home.workspace.gcalTitle') }}</div>
					<div class="gcal-sub" :class="{ dim: !data.tenant.google_calendar_id }">
						{{ data.tenant.google_calendar_id ? shortGcal(data.tenant.google_calendar_id) : $t('message.pages.home.workspace.gcalNotSet') }}
					</div>
				</div>
			</div>
			<!-- 落款签名小卡(仅经理/超管可见); 点击整卡进入设置 -->
			<div v-if="isManagerView && data.tenant" class="stat gcal-stat" @click="openSign" :title="$t('message.pages.home.workspace.signTitleAttr', { name: (data.tenant.sign_name || $t('message.pages.home.workspace.signDefault')) })">
				<div class="gcal-main">
					<div class="gcal-title">{{ $t('message.pages.home.workspace.signTitle') }}</div>
					<div class="gcal-sub" :class="{ dim: !data.tenant.sign_name }">
						{{ data.tenant.sign_name || $t('message.pages.home.workspace.signDefault') }}
					</div>
				</div>
			</div>
			<!-- 推荐码小卡(仅经理/超管可见); 点击复制, 供新客户注册时填写 -->
			<div v-if="isManagerView && data.tenant" class="stat gcal-stat" @click="copyReferral"
				:title="$t('message.pages.home.workspace.referralTitleAttr', { code: (data.tenant.referral_code || $t('message.pages.home.workspace.referralNone')) })">
				<div class="gcal-main">
					<div class="gcal-title">{{ $t('message.pages.home.workspace.referralTitle') }}</div>
					<div class="gcal-sub ref-code" :class="{ dim: !data.tenant.referral_code }">
						{{ data.tenant.referral_code || $t('message.pages.home.workspace.referralNone') }}
					</div>
				</div>
			</div>
			<!-- 推荐链接小卡(仅经理/超管可见); 点击复制注册链接, 客户点开即自动带上推荐码 -->
			<div v-if="isManagerView && data.tenant" class="stat gcal-stat" @click="copyReferLink"
				:title="$t('message.pages.home.workspace.referralLinkAttr', { link: (data.tenant.referral_code ? `${locationOrigin}/#/signup?refcode=${data.tenant.referral_code}` : $t('message.pages.home.workspace.referralNone')) })">
				<div class="gcal-main">
					<div class="gcal-title">{{ $t('message.pages.home.workspace.referralLinkTitle') }}</div>
					<div class="gcal-sub ref-link" :class="{ dim: !data.tenant.referral_code }">
						{{ data.tenant.referral_code ? $t('message.pages.home.workspace.copyLink') : $t('message.pages.home.workspace.referralNone') }}
					</div>
				</div>
			</div>
		</div>

		<div class="cols" v-loading="loading">
			<!-- 未来 3 天提醒 -->
			<div class="col">
				<div class="col-head">
					<span>{{ $t('message.pages.home.workspace.upcoming3dCol') }}</span>
					<el-button link type="primary" @click="$router.push('/property')">{{ $t('message.pages.home.workspace.gotoProperty') }}</el-button>
				</div>
				<div v-if="upcoming.length === 0" class="empty">{{ $t('message.pages.home.workspace.emptyUpcoming') }}</div>
				<div v-for="(u, idx) in upcoming" :key="u.kind + '-' + u.id + '-' + (u.rule_id || '') + '-' + idx" class="item">
					<div class="item-top">
						<span class="nm">{{ u.name }}</span>
						<span class="tags">
<el-tag v-if="u.kind === 'end'" class="tag-end" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagEnd') }}</el-tag>
<el-tag v-else-if="u.kind === 'utility'" class="tag-utility" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagUtility') }}</el-tag>
<el-tag v-else-if="u.kind === 'custom'" class="tag-custom" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagCustom') }}</el-tag>
						<el-tag class="tag-days" size="small" effect="plain"
							:class="{ clickable: u.days === 0, sending: u._sending }"
							:title="u.days === 0 ? (u.sent_today ? $t('message.pages.home.workspace.sentTodayClickResend') : $t('message.pages.home.workspace.clickSendNow')) : ''"
							@click="u.days === 0 ? sendNow(u) : null">
							{{ daysText(u.days) }}
						</el-tag>
						<span v-if="u.sent_today" class="sent-now" :title="$t('message.pages.home.workspace.sentToday')">
							<el-icon><ele-CircleCheck /></el-icon>
						</span>
						</span>
					</div>
					<div class="meta">
						<template v-if="u.kind === 'end'">
							{{ $t('message.pages.home.workspace.expire') }}
							<span class="dot"></span>{{ $t('message.pages.home.workspace.aheadDays', { n: u.ahead }) }}
							<span class="dot"></span>{{ $t('message.pages.home.workspace.remindDate') }} {{ u.next_remind }}
						</template>
						<template v-else-if="u.rule_id">
							{{ u.rule_name }}
							<span class="dot"></span>{{ periodText(u.rule_period) }} {{ u.rule_day }} {{ $t('message.pages.home.workspace.remindDay') }}
							<span class="dot"></span>{{ $t('message.pages.home.workspace.remindDate') }} {{ u.next_remind }}
						</template>
						<template v-else>
							{{ periodText(u.pay_period) }}
							<span class="dot"></span>{{ $t('message.pages.home.workspace.remindDay') }} {{ u.remind_day }}
							<span class="dot"></span>{{ $t('message.pages.home.workspace.remindDate') }} {{ u.next_remind }}
						</template>
					</div>
				<div class="meta sender" v-if="u.line_bot_name || u.group_name || u.group_id">
					<template v-if="u.line_bot_name">{{ u.line_bot_name }}</template>
					<template v-if="u.group_name">
						<span class="dot"></span>{{ u.group_name }}
						<span class="refresh-btn" :class="{ spinning: u._refreshing }" @click="refreshGroupName(u)" :title="$t('message.pages.home.workspace.refreshGroupName')">
							<el-icon><ele-Refresh /></el-icon>
						</span>
					</template>
					<template v-else-if="u.group_id">
						<span class="dot"></span>{{ $t('message.pages.home.workspace.group') }} {{ u.group_id }}
						<span class="refresh-btn" :class="{ spinning: u._refreshing }" @click="refreshGroupName(u)" :title="$t('message.pages.home.workspace.getGroupName')">
							<el-icon><ele-Refresh /></el-icon>
						</span>
					</template>
				</div>
					<div v-if="u.rent_end" class="meta dim">{{ $t('message.pages.home.workspace.leaseTerm') }}: {{ u.rent_start || '—' }} {{ $t('message.pages.home.workspace.to') }} {{ u.rent_end }}</div>
				</div>
			</div>

			<!-- 最近更新的房源 -->
			<div class="col">
				<div class="col-head">
					<span>{{ $t('message.pages.home.workspace.recentCol') }}</span>
					<el-button link type="primary" @click="$router.push('/property')">{{ $t('message.pages.home.workspace.viewAll') }}</el-button>
				</div>
				<div v-if="recent.length === 0" class="empty">{{ $t('message.pages.home.workspace.emptyRecent') }}</div>
				<div v-for="r in recent" :key="r.id" class="item">
					<div class="item-top">
						<span class="nm">{{ r.name }}</span>
						<span class="tags">
							<el-tag v-if="r.pay_period === 'Quarterly'" class="tag-quarter" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagQuarter') }}</el-tag>
							<el-tag v-else-if="r.pay_period === 'HalfYear'" class="tag-utility" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagHalfYear') }}</el-tag>
							<el-tag v-else-if="r.pay_period === 'Yearly'" class="tag-custom" size="small" effect="plain">{{ $t('message.pages.home.workspace.tagYearly') }}</el-tag>
							<el-tag size="small" effect="plain" type="info">{{ r.owner_name || $t('message.pages.home.workspace.unassigned') }}</el-tag>
						</span>
					</div>
					
					<div v-if="r.rent_start || r.rent_end" class="meta dim">{{ $t('message.pages.home.workspace.leaseTerm') }}: {{ r.rent_start || '—' }} {{ $t('message.pages.home.workspace.to') }} {{ r.rent_end || '—' }}</div>
				
					<div class="meta dim">{{ $t('message.pages.home.workspace.updatedAt') }} {{ r.update_datetime }}</div>
				</div>
			</div>
		</div>

		<!-- Google 日历设置弹窗 -->
		<el-dialog v-model="gcalVisible" :title="$t('message.pages.home.workspace.gcalDialogTitle')" width="520px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false">
			<div class="gcal-tip">
			{{ $t('message.pages.home.workspace.gcalTip', { account: 'mycalendar@mycalendar-506811.iam.gserviceaccount.com' }) }}
			</div>
			<el-form label-width="90px" label-position="left">
				<el-form-item :label="$t('message.pages.home.workspace.calendarId')">
					<el-input v-model="gcalForm.google_calendar_id" placeholder="example@gmail.com" clearable />
				</el-form-item>
			</el-form>
			<div class="gcal-tip">
				{{ $t('message.pages.home.workspace.gcalEmptyHint') }}
			</div>
			<template #footer>
				<div class="dlg-footer">
					<span v-if="gcalSyncing" class="gcal-sync-tip">{{ $t('message.pages.home.workspace.syncing') }}</span>
					<div class="spacer"></div>
					<el-button class="soft-ghost" @click="gcalVisible = false">{{ $t('message.pages.home.workspace.cancel') }}</el-button>
					<el-button type="primary" :loading="gcalSyncing" @click="saveGcal">{{ $t('message.pages.home.workspace.saveAndSync') }}</el-button>
				</div>
			</template>
		</el-dialog>

		<!-- 落款签名设置弹窗 -->
		<el-dialog v-model="signVisible" :title="$t('message.pages.home.workspace.signDialogTitle')" width="520px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false">
			<div class="gcal-tip">
				{{ $t('message.pages.home.workspace.signTip') }}
			</div>
			<el-form label-width="90px" label-position="left">
				<el-form-item :label="$t('message.pages.home.workspace.signLabel')">
					<el-input v-model="signForm.sign_name" :placeholder="$t('message.pages.home.workspace.signPlaceholder')" maxlength="64" show-word-limit />
				</el-form-item>
			</el-form>
			<template #footer>
				<div class="dlg-footer">
					<div class="spacer"></div>
					<el-button class="soft-ghost" @click="signVisible = false">{{ $t('message.pages.home.workspace.cancel') }}</el-button>
					<el-button type="primary" :loading="signSaving" @click="saveSign">{{ $t('message.pages.home.workspace.save') }}</el-button>
				</div>
			</template>
		</el-dialog>
	</div>
</template>

<script lang="ts" setup name="tenantHome">
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { GetWorkspace, RefreshGroupName, SendReminderNow, UpdateTenantGoogleCalendar, UpdateTenantSignName } from './api';
import { useUserInfo } from '/@/stores/userInfo';

const { t } = useI18n();
const { userInfos } = storeToRefs(useUserInfo());

// 租户经理/超管才有租户设置入口(Google 日历等); 与后端 _org_manage_ok 保持一致(主管/员工不可改)
const roleKeys = computed(() => (userInfos.value.role_info || []).map((r: any) => r.key));
const isManagerView = computed(() => userInfos.value.is_superuser || roleKeys.value.includes('tenant_manager'));

const loading = ref(false);
const data = ref<any>({ tenant: null, stats: {}, upcoming: [], recent: [] });
const userName = computed(() => userInfos.value.name || userInfos.value.username || '');
const stats = computed(() => data.value.stats || {});
const upcoming = computed(() => data.value.upcoming || []);
const recent = computed(() => data.value.recent || []);
const hiText = computed(() => {
	const h = new Date().getHours();
	return h < 6 ? t('message.pages.home.workspace.greetingDawn') : h < 12 ? t('message.pages.home.workspace.greetingMorning') : h < 18 ? t('message.pages.home.workspace.greetingAfternoon') : t('message.pages.home.workspace.greetingEvening');
});
const fmtMoney = (v: any) => (v === null || v === undefined || v === '' ? '—' : Number(v).toLocaleString());
const daysText = (d: number) => (d === 0 ? t('message.pages.home.workspace.today') : d === 1 ? t('message.pages.home.workspace.tomorrow') : t('message.pages.home.workspace.daysLater', { n: d }));
const periodText = (v: any) => (v === 'Quarterly' ? t('message.pages.calendar.period.quarterly') : v === 'HalfYear' ? t('message.pages.calendar.period.halfYear') : v === 'Yearly' ? t('message.pages.calendar.period.yearly') : t('message.pages.calendar.period.monthly'));
const shortGcal = (v: string) => (v && v.length > 28 ? v.slice(0, 28) + '…' : v);

const copyReferral = async () => {
	const code = data.value.tenant?.referral_code;
	if (!code) return;
	try {
		await navigator.clipboard.writeText(code);
		ElMessage.success(t('message.pages.home.workspace.copyReferralSuccess', { code }));
	} catch (e) {
		ElMessage.info(t('message.pages.home.workspace.copyReferralFail', { code }));
	}
};

const locationOrigin = window.location.origin;

const copyReferLink = async () => {
	const code = data.value.tenant?.referral_code;
	if (!code) return;
	const link = `${locationOrigin}/#/signup?refcode=${code}`;
	try {
		await navigator.clipboard.writeText(link);
		ElMessage.success(t('message.pages.home.workspace.copyLinkSuccess'));
	} catch (e) {
		ElMessage.info(t('message.pages.home.workspace.copyLinkFail', { link }));
	}
};

const refreshGroupName = async (u: any) => {
	if (!u.id || u._refreshing) return;
	u._refreshing = true;
	try {
		const res: any = await RefreshGroupName(u.id);
		if (res.code === 2000 && res.data) {
			const name = res.data.group_name;
			if (name) {
				u.group_name = name;
				ElMessage.success(t('message.pages.home.workspace.refreshGroupSuccess'));
			} else if (res.data.error === 'network') {
				ElMessage.warning(t('message.pages.home.workspace.refreshGroupNetwork'));
			} else if (res.data.error === 'denied') {
				ElMessage.warning(t('message.pages.home.workspace.refreshGroupDenied'));
			} else {
				ElMessage.warning(t('message.pages.home.workspace.refreshGroupOther'));
			}
		}
	} catch (e) {
		ElMessage.error(t('message.pages.home.workspace.refreshFailed'));
	} finally {
		u._refreshing = false;
	}
};

const sendNow = async (u: any) => {
	if (!u.id || u._sending) return;
	const kind = u.kind || 'rent';
	const rule_id = u.rule_id || undefined;
	u._sending = true;
	try {
		const res: any = await SendReminderNow(u.id, kind, rule_id);
		if (res.code === 2000 && res.data && res.data.ok) {
			ElMessage.success(res.data.message || t('message.pages.home.workspace.sendSuccess'));
			u.sent_today = true;
		} else {
			ElMessage.warning((res.data && res.data.message) || t('message.pages.home.workspace.sendFail'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.home.workspace.sendFail'));
	} finally {
		u._sending = false;
	}
};

// ---------------- Google 日历设置(租户经理) ----------------
const gcalVisible = ref(false);
const gcalSyncing = ref(false);
const gcalForm = ref<{ google_calendar_id: string }>({ google_calendar_id: '' });

const openGcal = () => {
	gcalForm.value.google_calendar_id = data.value.tenant?.google_calendar_id || '';
	gcalVisible.value = true;
};

const saveGcal = async () => {
	if (!data.value.tenant?.id) return;
	gcalSyncing.value = true;
	try {
		const res: any = await UpdateTenantGoogleCalendar(data.value.tenant.id, (gcalForm.value.google_calendar_id || '').trim());
		if (res.code === 2000) {
			// 更新本地展示 + 重新拉工作台
			if (data.value.tenant) data.value.tenant.google_calendar_id = res.data.google_calendar_id || '';
			gcalVisible.value = false;
			const parts = [t('message.pages.home.workspace.gcalSaved', { synced: res.data.synced })];
			if (res.data.failed) parts.push(t('message.pages.home.workspace.gcalFailed', { failed: res.data.failed }));
			ElMessage.success(parts.join('，'));
			if (res.data.msgs && res.data.msgs.length) console.warn('日历同步失败项:', res.data.msgs);
			load();
		} else {
			ElMessage.error(res.msg || t('message.pages.home.workspace.saveFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.home.workspace.saveFailed'));
	} finally {
		gcalSyncing.value = false;
	}
};

// ---------------- 落款签名设置(租户经理) ----------------
const signVisible = ref(false);
const signSaving = ref(false);
const signForm = ref<{ sign_name: string }>({ sign_name: '' });

const openSign = () => {
	signForm.value.sign_name = data.value.tenant?.sign_name || '';
	signVisible.value = true;
};

const saveSign = async () => {
	if (!data.value.tenant?.id) return;
	signSaving.value = true;
	try {
		const res: any = await UpdateTenantSignName(data.value.tenant.id, (signForm.value.sign_name || '').trim());
		if (res.code === 2000) {
			if (data.value.tenant) data.value.tenant.sign_name = res.data.sign_name || '';
			signVisible.value = false;
			ElMessage.success(t('message.pages.home.workspace.signUpdated'));
			load();
		} else {
			ElMessage.error(res.msg || t('message.pages.home.workspace.saveFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.home.workspace.saveFailed'));
	} finally {
		signSaving.value = false;
	}
};

onMounted(async () => {
	load();
});

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetWorkspace();
		if (res.code === 2000) data.value = res.data;
	} finally {
		loading.value = false;
	}
};
</script>

<style scoped lang="scss">
.ws {
	max-width: 1200px;
	color: #eaeaea;

	.ws-head {
		.title {
			font-size: 20px;
			margin: 0 0 6px;
			color: #f4f4f5;
			display: flex;
			align-items: center;
			gap: 10px;
			.co {
				font-size: 14px;
				color: #b1b4b8;
				font-weight: 500;
			}
			.expire-note {
				font-size: 12px;
				color: #8f9297;
				font-weight: 400;
				padding: 1px 8px;
				border: 1px solid #333;
				border-radius: 6px;
				white-space: nowrap;
			}
		}
		.hi {
			margin: 0;
			color: #b1b4b8;
			font-size: 13px;
			display: flex;
			align-items: center;
			gap: 8px;

			.expired-hit {
				--el-tag-bg-color: rgba(245, 108, 108, 0.08) !important;
				--el-tag-border-color: rgba(245, 108, 108, 0.3) !important;
				--el-tag-text-color: #cf8282 !important;
				font-weight: 400;
				line-height: 18px;
				height: 18px;
				cursor: pointer;
				transition: all 0.15s;
				&:hover {
					--el-tag-bg-color: rgba(245, 108, 108, 0.18) !important;
					--el-tag-border-color: rgba(245, 108, 108, 0.5) !important;
					--el-tag-text-color: #f28f8f !important;
				}
			}
		}
	}

	.stat-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 14px;
		margin: 22px 0;
		.stat {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			padding: 18px;
			.n {
				font-size: 28px;
				font-weight: 600;
				color: #eaeaea;
				em {
					font-style: normal;
					font-size: 15px;
					color: #b1b4b8;
					margin-left: 2px;
				}
			}
			.l {
				margin-top: 6px;
				font-size: 12px;
				color: #b1b4b8;
			}
		}

		// Google 日历小卡(与其它统计卡背景一致, 点击整卡进入设置; 长邮箱单行截断, hover 显示完整)
		.gcal-stat {
			display: flex;
			align-items: center;
			gap: 10px;
			padding: 14px 16px;
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			cursor: pointer;
			transition: border-color 0.2s, background 0.2s;

			&:hover {
				border-color: rgba(64, 158, 255, 0.5);
				background: rgba(64, 158, 255, 0.06);
			}

			.gcal-main { min-width: 0; flex: 1; }
			.gcal-title { font-size: 13px; font-weight: 600; color: #f0f0f1; }
			.gcal-sub {
				margin-top: 3px;
				font-size: 11px;
				color: #9ec9ff;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				&.dim { color: #8f9297; }
			}
			.ref-code {
				font-family: monospace;
				font-size: 15px;
				font-weight: 600;
				letter-spacing: 1px;
			}
			.ref-link {
				color: #9ec9ff;
				font-size: 12px;
				&.dim { color: #8f9297; }
			}
		}
	}

	.cols {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 14px;
		min-height: 160px;

		.col {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			padding: 18px;

			.col-head {
				display: flex;
				justify-content: space-between;
				align-items: center;
				font-size: 15px;
				font-weight: 600;
				color: #f0f0f1;
				margin-bottom: 12px;
			}

			.empty {
				color: #94979c;
				font-size: 13px;
				padding: 26px 0;
				text-align: center;
			}

			.item {
				padding: 12px 0;
				border-bottom: 1px dashed rgba(255, 255, 255, 0.07);

				.item-top {
					display: flex;
					justify-content: space-between;
					align-items: center;
					gap: 8px;
					.nm {
						font-weight: 600;
						color: #f0f0f1;
						word-break: break-all;
					}
					.tags {
						display: flex;
						gap: 6px;
						flex-shrink: 0;
					}
					.tag-days {
						--el-tag-bg-color: rgba(64, 158, 255, 0.2) !important;
						--el-tag-border-color: rgba(64, 158, 255, 0.35) !important;
						--el-tag-text-color: #9ec9ff !important;

						// 今天: 可点击触发发送
						&.clickable {
							cursor: pointer;
							user-select: none;
							transition: background 0.15s, border-color 0.15s;
							&:hover {
								--el-tag-bg-color: rgba(64, 158, 255, 0.32) !important;
								--el-tag-border-color: rgba(64, 158, 255, 0.55) !important;
								--el-tag-text-color: #bcd9ff !important;
							}
							&.sending {
								pointer-events: none;
								opacity: 0.7;
								animation: sendPulse 0.8s ease-in-out infinite;
							}
						}
					}
					.tag-end {
						--el-tag-bg-color: rgba(207, 130, 130, 0.14) !important;
						--el-tag-border-color: rgba(224, 144, 144, 0.5) !important;
						--el-tag-text-color: #cf8282 !important;
					}
					.tag-utility {
						--el-tag-bg-color: rgba(103, 194, 58, 0.14) !important;
						--el-tag-border-color: rgba(103, 194, 58, 0.5) !important;
						--el-tag-text-color: #95d475 !important;
					}
					.tag-custom {
						--el-tag-bg-color: rgba(230, 162, 60, 0.14) !important;
						--el-tag-border-color: rgba(230, 162, 60, 0.5) !important;
						--el-tag-text-color: #e6a23c !important;
					}
					.tag-quarter {
						--el-tag-bg-color: rgba(230, 162, 60, 0.14) !important;
						--el-tag-border-color: rgba(230, 162, 60, 0.5) !important;
						--el-tag-text-color: #e6a23c !important;
					}
					.sent-now {
						display: inline-flex;
						align-items: center;
						justify-content: center;
						width: 20px;
						height: 20px;
						border-radius: 50%;
						border: 1px solid rgba(103, 194, 58, 0.35);
						background: rgba(103, 194, 58, 0.12);
						color: #85ce61;
						cursor: default;
					}


				}
				.meta {
					margin-top: 6px;
					font-size: 13px;
					color: #d8dade;
					b { color: #e6a23c; font-weight: 600; }
					.dot {
						display: inline-block;
						width: 3px;
						height: 3px;
						border-radius: 50%;
						background: #7d8188;
						margin: 0 8px 2px;
						vertical-align: middle;
					}
					&.dim { color: #b1b4b8; font-size: 12px; }
					.ic { margin-right: 4px; }
					&.sender {
						display: flex;
						align-items: center;
						flex-wrap: wrap;
						gap: 0 2px;
						color: #b1b4b8;
						font-size: 12px;
						.refresh-btn {
							display: inline-flex;
							align-items: center;
							margin-left: 6px;
							cursor: pointer;
							color: #94979c;
							transition: color 0.2s;
							&:hover { color: #409eff; }
							&.spinning .el-icon { animation: spin 0.8s linear infinite; }
						}
					}
				}
				@keyframes spin {
					from { transform: rotate(0deg); }
					to { transform: rotate(360deg); }
				}
				@keyframes sendPulse {
					0% { transform: scale(1); }
					50% { transform: scale(1.25); }
					100% { transform: scale(1); }
				}
			}
		}
	}
}
</style>
<style lang="scss">
/* Google 日历设置弹窗(teleport body, 非 scoped) */
.gcal-tip {
	font-size: 13px;
	color: #b1b4b8;
	line-height: 1.7;
	background: rgba(255, 255, 255, 0.04);
	border: 1px solid #2a2a2a;
	border-radius: 8px;
	padding: 10px 12px;
	margin-bottom: 16px;
	b { color: #e6a23c; font-weight: 600; }
}
.gcal-warn {
	font-size: 13px;
	color: #e6a23c;
	line-height: 1.6;
	margin-top: 4px;
	b { color: #f0b661; }
}
.dlg-footer { display: flex; align-items: center; gap: 8px; width: 100%; }
.spacer { flex: 1; }
.gcal-sync-tip { font-size: 12px; color: #b1b4b8; }

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