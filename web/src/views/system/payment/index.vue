<template>
	<div class="pay-page">
		<div class="page-head">
			<span class="title">{{ $t('message.pages.payment.title') }}</span>
			<span class="sub">{{ $t('message.pages.payment.sub') }}</span>
		</div>

		<div v-loading="loading" class="pay-panel">
			<!-- 加载中 -->
			<div v-if="loading" class="empty">{{ $t('message.pages.payment.loading') }}</div>

			<!-- 未启用 -->
			<div v-else-if="!config.enabled" class="no-auth">
				{{ $t('message.pages.payment.gatewayDisabled') }} <el-button link type="primary" @click="$router.push('/home')">{{ $t('message.pages.payment.backToWorkbench') }}</el-button>
			</div>

			<!-- 已完成 -->
			<div v-else-if="paid" class="done">
				<div class="done-ico"><el-icon><ele-CircleCheck /></el-icon></div>
				<div class="done-title">{{ $t('message.pages.payment.successTitle') }}</div>
				<div class="done-sub">{{ $t('message.pages.payment.successSub', { days: paidExpireText, time: newExpireTime }) }}</div>
				<div class="done-sub dim">{{ $t('message.pages.payment.successSubDim') }}</div>
				<el-button type="primary" @click="$router.push('/home')">{{ $t('message.pages.payment.backToWorkbench') }}</el-button>
			</div>

			<!-- 已超时/失败 -->
			<div v-else-if="chargeFailed" class="done">
				<div class="done-ico fail"><el-icon><ele-WarningFilled /></el-icon></div>
				<div class="done-title">{{ $t('message.pages.payment.failTitle') }}</div>
				<div class="done-sub">{{ $t('message.pages.payment.failSub') }}</div>
				<el-button type="primary" @click="regenerate">{{ $t('message.pages.payment.regenerate') }}</el-button>
			</div>

			<!-- 待支付 -->
			<div v-else class="pay-box">
				<!-- 金额 -->
				<div class="amount-card">
					<div class="amount-label">{{ $t('message.pages.payment.amountLabel') }}</div>
					<div class="amount-val">
						฿ {{ config.amount_thb.toLocaleString() }}
						<span class="unit">{{ $t('message.pages.payment.unit', { days: config.renew_days }) }}</span>
					</div>
				</div>

				<div class="renewal-note">
					<div class="renewal-note-head">
						<b>One-time annual payment</b>
						<span>{{ config.renew_days }} days · No auto-renewal</span>
					</div>
					<p>
						Your plan ends after {{ config.renew_days }} days. proNotify does not store your payment details and will not charge you automatically. By paying, you agree to our
						<a href="/legal/terms-of-service.html" target="_blank" rel="noopener">Terms of Service</a>,
						<a href="/legal/refund-cancellation-policy.html" target="_blank" rel="noopener">Cancellation &amp; Refund Policy</a>
						and <a href="/legal/privacy-policy.html" target="_blank" rel="noopener">Privacy Policy</a>.
					</p>
				</div>

				<!-- 倒计时 -->
				<div class="timer">
					<span class="timer-label">{{ $t('message.pages.payment.timeLeft') }}</span>
					<b class="timer-num" :class="{ 'timer-near': countdown <= 60 }">{{ formattedCountdown }}</b>
				</div>

				<!-- 二维码 -->
				<div class="qr-card">
					<img v-if="charge && charge.qr_code_url" :src="charge.qr_code_url" alt="PromptPay QR" class="qr-img" loading="lazy" />
					<div v-else class="qr-placeholder">
						<el-icon><ele-Wallet /></el-icon>
						<div>{{ $t('message.pages.payment.generatingQr') }}</div>
					</div>
					<div class="qr-tip">{{ $t('message.pages.payment.qrTip') }}</div>
				</div>

				<!-- 操作 -->
				<div class="actions">
					<div class="regen">
						<el-button link size="small" @click="regenerate">{{ $t('message.pages.payment.regenerate') }}</el-button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup name="tenantPayment">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { GetPaymentConfig, CreatePaymentCharge, GetPaymentStatus, SimulatePayment } from './api';

const { t } = useI18n();

const loading = ref(false);
const creating = ref(false);
const simulating = ref(false);
const polling = ref(false);
const config = ref<any>({ enabled: false, amount_thb: 0, renew_days: 365, expire_seconds: 900, expire_min: 15, dev_mode: false, test_mode: false });
const charge = ref<any>(null);
const paidInfo = ref<any>(null);
const chargeFailed = ref(false);

const paid = computed(() => !!paidInfo.value);
const newExpireTime = computed(() => (paidInfo.value && paidInfo.value.new_expire_time) || '');
const paidExpireText = computed(() => `${config.value.renew_days}`);

// 倒计时
const countdown = ref(config.value.expire_seconds || 900);
let countdownTimer: any = null;
const formattedCountdown = computed(() => {
	const s = Math.max(0, countdown.value);
	const m = Math.floor(s / 60);
	const sec = s % 60;
	return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
});
const startCountdown = () => {
	if (countdownTimer) clearInterval(countdownTimer);
	countdown.value = config.value.expire_seconds || 900;
	countdownTimer = setInterval(() => {
		countdown.value -= 1;
		if (countdown.value <= 0) {
			clearInterval(countdownTimer);
			countdownTimer = null;
			// 超时未支付 -> 标记失败, 显示重新生成按钮
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
		const res: any = await CreatePaymentCharge();
		if (res.code === 2000 && res.data) {
			charge.value = res.data;
			if (res.data.expire_seconds) config.value.expire_seconds = res.data.expire_seconds;
			config.value.expire_min = Math.max(1, Math.round((config.value.expire_seconds || 900) / 60));
			polling.value = true;
			startCountdown();
			startPoll(res.data.charge_id);
			ElMessage.success(t('message.pages.payment.qrGenerated'));
		} else {
			ElMessage.warning((res.data && res.data.error) || res.msg || t('message.pages.payment.createFailed'));
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
				// 后端已超时自动标记失败(含 Omise mark_as_failed)
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
	pollTimer = setInterval(() => {
		doStatus(charge_id);
	}, 3000);
};

const simulate = async () => {
	if (!charge.value?.charge_id) return;
	simulating.value = true;
	try {
		const res: any = await SimulatePayment(charge.value.charge_id);
		if (res.code === 2000 && res.data && res.data.paid) {
			paidInfo.value = { new_expire_time: res.data.new_expire_time };
			polling.value = false;
			stopCountdown();
			if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
			ElMessage.success(t('message.pages.payment.simulateSuccess'));
		} else {
			ElMessage.warning(t('message.pages.payment.simulateFailed'));
		}
	} catch (e) {
		ElMessage.error(t('message.pages.payment.simulateRequestFailed'));
	} finally {
		simulating.value = false;
	}
};

onMounted(async () => {
	loading.value = true;
	try {
		const res: any = await GetPaymentConfig();
		if (res.code === 2000) {
			config.value = res.data || config.value;
			if (config.value.expire_seconds) {
				config.value.expire_min = Math.max(1, Math.round(config.value.expire_seconds / 60));
			}
		}
	} finally {
		loading.value = false;
	}
	// 进入页面即自动生成二维码(若网关已启用)
	if (config.value.enabled) {
		await create();
	}
});

onBeforeUnmount(() => {
	stopCountdown();
	if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
});
</script>

<style scoped lang="scss">
.pay-page {
	max-width: 720px;
	color: #eaeaea;

	.page-head {
		margin-bottom: 16px;
		.title {
			font-size: 18px;
			font-weight: 600;
			color: #f4f4f5;
		}
		.sub {
			margin-left: 10px;
			font-size: 13px;
			color: #b1b4b8;
		}
	}

	.pay-panel {
		background: #1a1a1c;
		border: 1px solid #2a2a2a;
		border-radius: 12px;
		padding: 24px;
		min-height: 320px;
	}

	.empty { color: #94979c; text-align: center; padding: 60px 0; }

	.no-auth {
		text-align: center;
		color: #f56c6c;
		padding: 40px 0;
	}

	.done {
		text-align: center;
		padding: 30px 20px;
	.done-ico {
		font-size: 56px;
		color: #67c23a;
		&.fail { color: #f56c6c; }
	}
		.done-title {
			font-size: 20px;
			font-weight: 600;
			color: #f0f0f1;
			margin: 14px 0 8px;
		}
		.done-sub {
			font-size: 14px;
			color: #b1b4b8;
			margin-bottom: 6px;
			&.dim { color: #8f9297; font-size: 12px; }
		}
		.el-button {
			margin-top: 18px;
		}
	}

	.pay-box {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 20px;

		.amount-card {
			text-align: center;
			.amount-label { font-size: 13px; color: #b1b4b8; margin-bottom: 6px; }
			.amount-val {
				font-size: 34px;
				font-weight: 600;
				color: #f0f0f1;
				.unit {
					font-size: 13px;
					color: #b1b4b8;
					font-weight: 400;
					margin-left: 8px;
				}
			}
		}

		.renewal-note {
			width: 100%;
			max-width: 420px;
			padding: 12px 14px;
			border: 1px solid #2f3b48;
			border-radius: 10px;
			background: rgba(64, 158, 255, 0.06);
			text-align: left;

			.renewal-note-head {
				display: flex;
				flex-wrap: wrap;
				align-items: baseline;
				justify-content: space-between;
				gap: 6px;
				margin-bottom: 6px;

				b { font-size: 13px; color: #e8e8ea; }
				span { font-size: 11px; color: #9ec9ff; }
			}

			p {
				margin: 0;
				font-size: 11px;
				line-height: 1.65;
				color: #9ba0a6;
			}

			a {
				color: #8ec5ff;
				text-decoration: underline;
			}
		}

		.qr-card {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			padding: 16px;
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 10px;

			.qr-img {
				width: 200px;
				height: 200px;
				object-fit: contain;
				border-radius: 8px;
				background: #fff;
			}
			.qr-placeholder {
				width: 200px;
				height: 200px;
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

		.timer {
			display: flex;
			align-items: center;
			gap: 8px;
			font-size: 13px;
			color: #b1b4b8;
			.timer-label {
				color: #8f9297;
			}
			.timer-num {
				font-family: monospace;
				font-size: 15px;
				color: #b9bcc2;
				font-weight: 600;
				&.timer-near {
					color: #e6a23c;
				}
			}
		}

		.actions {
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 10px;

			.paid-waiting {
				display: flex;
				align-items: center;
				gap: 8px;
				color: #e6a23c;
				font-size: 14px;
				.spin { animation: spin 1s linear infinite; }
			}
			.dev-sim {
				display: flex;
				flex-direction: column;
				align-items: center;
				gap: 10px;
				width: 100%;
				padding-top: 8px;
				border-top: 1px dashed rgba(255, 255, 255, 0.1);
				.dev-label {
					font-size: 12px;
					color: #8f9297;
				}
			}
		}
	}
}

@keyframes spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

:deep(.el-button--primary) {
	background: rgba(64, 158, 255, 0.2);
	border-color: rgba(64, 158, 255, 0.35);
	color: #9ec9ff;
	&:hover, &:focus {
		background: rgba(64, 158, 255, 0.3);
		border-color: rgba(64, 158, 255, 0.5);
		color: #bcd9ff;
	}
}
</style>