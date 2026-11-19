<template>
	<div class="signup-page">
		<header class="signup-header">
			<img :src="siteLogo" class="brand-mark" />
		</header>

		<main class="signup-panel">
			<div class="signup-card" style="max-width: 460px">
				<div class="card-head">
					<!-- <img :src="siteLogo" class="card-logo" /> -->
					<h1 class="card-title" v-if="!paid && !chargeFailed">{{ $t('message.pages.signup.activateTitle') }}</h1>
					<h1 class="card-title" v-else-if="chargeFailed">{{ $t('message.pages.signup.activateFailed') }}</h1>
					<h1 class="card-title" v-else>{{ $t('message.pages.signup.activateSuccess') }}</h1>
					<!-- <p class="card-subtitle" v-if="!paid && !chargeFailed">付费后立即创建你的租户账号</p> -->
				</div>

				<!-- 加载中 -->
				<div v-if="loading" class="center-loading">
					<el-icon class="spin"><ele-Loading /></el-icon>
					<p>{{ $t('message.pages.signup.loading') }}</p>
				</div>

				<!-- 免付费开通模式(超管关闭"付费开通"开关) -->
				<div v-else-if="freeMode" class="success-box">
					<div class="done-ico ok"><el-icon><ele-CircleCheck /></el-icon></div>
					<h2 class="card-title">{{ $t('message.pages.signup.freeActivateTitle') }}</h2>
					<p class="card-subtitle">{{ $t('message.pages.signup.freeActivateSubtitle', { company }) }}</p>
					<div class="card-actions">
						<el-button type="primary" round :loading="activatingFree" @click="activateFree">
							{{ $t('message.pages.signup.freeActivateBtn') }}
						</el-button>
					</div>
				</div>

				<!-- 已付款成功 -->
				<div v-else-if="paid" class="success-box">
					<div class="done-ico ok"><el-icon><ele-CircleCheck /></el-icon></div>
					<p class="card-subtitle">{{ $t('message.pages.signup.activated', { company, days: renewDays }) }}</p>
					<div class="card-actions">
						<el-button type="primary" round @click="relogin">{{ $t('message.pages.signup.relogin') }}</el-button>
					</div>
					<!-- <p class="small-note">为加载你的账号权限，请重新登录一次</p> -->
				</div>

				<!-- 超时/失败 -->
				<div v-else-if="chargeFailed" class="success-box">
					<div class="done-ico fail"><el-icon><ele-WarningFilled /></el-icon></div>
					<p class="card-subtitle">{{ $t('message.pages.signup.paymentVoid') }}</p>
					<div class="card-actions">
						<el-button type="primary" round @click="regenerate">{{ $t('message.pages.signup.regenerate') }}</el-button>
					</div>
				</div>

				<!-- 待支付 -->
				<div v-else>
					<!-- 金额 -->
					<div class="amount-card">
						<!-- <div class="amount-label">开通费用</div> -->
						<div class="amount-val">
							฿ {{ config.amount_thb.toLocaleString() }}
							<span class="unit">{{ $t('message.pages.signup.unit', { days: config.renew_days }) }}</span>
						</div>
						<!-- <div class="amount-desc">包含你的租户账号，首年使用费</div> -->
					</div>

					<!-- 倒计时 -->
					<div class="timer">
						<span class="timer-label">{{ $t('message.pages.signup.timeLeft') }}</span>
						<b class="timer-num" :class="{ 'timer-near': countdown <= 60 }">{{ formattedCountdown }}</b>
					</div>

					<!-- 二维码 -->
					<div class="qr-card">
						<img v-if="charge && charge.qr_code_url" :src="charge.qr_code_url" alt="PromptPay QR" class="qr-img" loading="lazy" />
						<div v-else class="qr-placeholder">
							<el-icon><ele-Wallet /></el-icon>
							<div>{{ $t('message.pages.signup.verifying') }}</div>
						</div>
						<div class="qr-tip">{{ $t('message.pages.payment.qrTip') }}</div>
					</div>

					<!-- 操作 -->
					<div class="actions">
						<!-- <div class="paid-waiting">
							<el-icon class="spin" v-if="polling"><ele-Loading /></el-icon>
							<span>我已转账，请等待确认…</span>
						</div> -->
						<!-- <div class="dev-sim" v-if="config.dev_mode || config.test_mode">
							<span class="dev-label">{{ config.dev_mode ? '开发模式' : '测试模式' }}</span>
							<el-button size="small" :loading="simulating" @click="simulate">模拟支付成功({{ config.dev_mode ? 'dev' : 'test' }})</el-button>
						</div> -->
					</div>
				</div>
			</div>
		</main>

		<footer class="signup-footer">
			<p>{{ $t('message.pages.signup.footer') }}</p>
		</footer>
	</div>
</template>

<script lang="ts" setup name="signupActivate">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { NextLoading } from '/@/utils/loading';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { Session } from '/@/utils/storage';
import logoBlackTrans from '/@/assets/img/proNotify_logo_black_trans.png';
import _ from 'lodash-es';
import { CreateSignupPayment, GetPaymentStatus, SimulatePayment, GetPaymentConfig, ActivateFree } from './api';

const { t } = useI18n();
const router = useRouter();
const { systemConfig } = storeToRefs(SystemConfigStore());
const siteLogo = computed(() => {
	if (!_.isEmpty(systemConfig.value['login.site_logo'])) return systemConfig.value['login.site_logo'];
	return logoBlackTrans;
});

const loading = ref(false);
const creating = ref(false);
const simulating = ref(false);
const polling = ref(false);
const activatingFree = ref(false);
const freeMode = ref(false);
const config = ref<any>({ enabled: false, amount_thb: 0, renew_days: 365, expire_seconds: 900, dev_mode: false, test_mode: false, signup_require_payment: true });
const charge = ref<any>(null);
const paidInfo = ref<any>(null);
const chargeFailed = ref(false);
const company = ref('');

const paid = computed(() => !!paidInfo.value);
const renewDays = computed(() => config.value.renew_days || 365);

// 倒计时
const countdown = ref(config.value.expire_seconds || 900);
let countdownTimer: any = null;
const formattedCountdown = computed(() => {
	const s = Math.max(0, countdown.value);
	return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
});
const startCountdown = () => {
	if (countdownTimer) clearInterval(countdownTimer);
	countdown.value = config.value.expire_seconds || 900;
	countdownTimer = setInterval(() => {
		countdown.value -= 1;
		if (countdown.value <= 0) {
			clearInterval(countdownTimer);
			countdownTimer = null;
			chargeFailed.value = true;
			polling.value = false;
		}
	}, 1000);
};
const stopCountdown = () => {
	if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
};

let pollTimer: any = null;

const create = async () => {
	creating.value = true;
	chargeFailed.value = false;
	try {
		const res: any = await CreateSignupPayment();
		if (res.code === 2000 && res.data) {
			charge.value = res.data;
			company.value = res.data.company || '';
			if (res.data.expire_seconds) config.value.expire_seconds = res.data.expire_seconds;
			polling.value = true;
			startCountdown();
			startPoll(res.data.charge_id);
		} else if (res.code === 2000 && res.data?.paid) {
			paidInfo.value = res.data;
		} else {
			ElMessage.warning(res.msg || t('message.pages.payment.createPaymentFailed'));
			// 例如已开通(已有租户): 引导回工作台
			if (res.msg && res.msg.includes('已付费')) {
				setTimeout(() => router.push('/home'), 1200);
			}
		}
	} catch (e) {
		ElMessage.error(t('message.pages.payment.createPaymentFailed'));
	} finally {
		creating.value = false;
	}
};

const regenerate = async () => {
	stopCountdown();
	if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
	charge.value = null;
	await create();
};

const doStatus = async (charge_id: string) => {
	try {
		const res: any = await GetPaymentStatus(charge_id);
		if (res.code === 2000 && res.data) {
			if (res.data.paid) {
				paidInfo.value = res.data;
				polling.value = false;
				stopCountdown();
				if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
			} else if (res.data.failed || res.data.expired) {
				chargeFailed.value = true;
				polling.value = false;
				stopCountdown();
				if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
			}
		}
	} catch (e) {
		/* 忽略轮询错误 */
	}
};

const startPoll = (charge_id: string) => {
	if (pollTimer) clearInterval(pollTimer);
	pollTimer = setInterval(() => doStatus(charge_id), 3000);
};

const simulate = async () => {
	if (!charge.value?.charge_id) return;
	simulating.value = true;
	try {
		const res: any = await SimulatePayment(charge.value.charge_id);
		if (res.code === 2000 && res.data && res.data.paid) {
			paidInfo.value = { ...res.data };
			polling.value = false;
			stopCountdown();
			if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
		} else {
			ElMessage.warning(t('message.pages.payment.simulateFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.payment.simulateRequestFailed'));
	} finally {
		simulating.value = false;
	}
};

const relogin = () => {
	Session.clear();
	router.push('/login');
};

const activateFree = async () => {
	activatingFree.value = true;
	try {
		const res: any = await ActivateFree();
		if (res.code === 2000) {
			ElMessage.success(res.msg || t('message.pages.signup.activateSuccess'));
			setTimeout(() => relogin(), 800);
		} else {
			ElMessage.warning(res.msg || t('message.pages.signup.activateFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.payment.createPaymentFailed'));
	} finally {
		activatingFree.value = false;
	}
};

onMounted(async () => {
	// 关掉全局 loading(登录后 initBackEndControlRoutes 会 start, 本页无 layout 不会自动 done)
	NextLoading.done();
	loading.value = true;
	try {
		const res: any = await GetPaymentConfig();
		if (res.code === 2000) config.value = { ...config.value, ...(res.data || {}) };
	} finally {
		loading.value = false;
	}
	// 超管关闭"付费开通"开关 → 免付费直接开通
	if (config.value.signup_require_payment === false) {
		freeMode.value = true;
		return;
	}
	if (config.value.enabled) await create();
});

onBeforeUnmount(() => {
	stopCountdown();
	if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
});
</script>

<style scoped lang="scss">
@import './styles';

.spin { font-size: 40px; color: #409eff; animation: spin 1s linear infinite; }
.loading-box, .center-loading { text-align: center; padding: 30px 0; p { color: var(--pn-muted); } }
.success-box { text-align: center; }
.done-ico {
	font-size: 52px;
	margin: 10px 0 4px;
	&.ok { color: #67c23a; }
	&.fail { color: #f56c6c; }
}
.small-note { margin-top: 10px; font-size: 12px; color: var(--pn-faint); }

.amount-card {
	text-align: center;
	margin-bottom: 14px;
	.amount-label { font-size: 13px; color: var(--pn-muted); margin-bottom: 4px; }
	.amount-val {
		font-size: 30px;
		font-weight: 600;
		color: #f0f0f1;
		.unit { font-size: 12px; color: var(--pn-muted); font-weight: 400; margin-left: 8px; }
	}
	.amount-desc { margin-top: 4px; font-size: 12px; color: var(--pn-faint); }
}

.timer {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	font-size: 13px;
	color: #b1b4b8;
	margin-bottom: 14px;
	.timer-label { color: #8f9297; }
	.timer-num {
		font-family: monospace;
		font-size: 15px;
		color: #b9bcc2;
		font-weight: 600;
		&.timer-near { color: #e6a23c; }
	}
}

.qr-card {
	background: #1a1a1c;
	border: 1px solid #2a2a2a;
	border-radius: 12px;
	padding: 14px;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;

	.qr-img {
		width: 190px;
		height: 190px;
		object-fit: contain;
		border-radius: 8px;
		background: #fff;
	}
	.qr-placeholder {
		width: 190px;
		height: 190px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 8px;
		color: #b1b4b8;
		font-size: 13px;
		border: 1px dashed #3a3a3a;
		border-radius: 8px;
		.el-icon { font-size: 36px; color: #409eff; }
	}
	.qr-tip { font-size: 12px; color: #8f9297; }
}

.actions {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 10px;
	margin-top: 16px;

	.paid-waiting {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: #b1b4b8;
		.spin { font-size: 15px; }
	}
	.dev-sim {
		font-size: 12px;
		color: #8f9297;
		.dev-label { margin-right: 6px; }
	}
}

@keyframes spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}
</style>