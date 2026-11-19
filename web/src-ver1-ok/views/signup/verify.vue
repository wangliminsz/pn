<template>
	<div class="signup-page">
		<header class="signup-header">
			<img :src="siteLogo" class="brand-mark" />
		</header>

		<main class="signup-panel">
			<div class="signup-card center-card">
				<div v-if="state === 'verifying'" class="loading-box">
					<el-icon class="spin"><ele-Loading /></el-icon>
					<p>{{ $t('message.pages.signup.verifying') }}</p>
				</div>

				<div v-else-if="state === 'ok'" class="success-box">
					<div class="done-ico ok"><el-icon><ele-CircleCheck /></el-icon></div>
					<h1 class="card-title">{{ $t('message.pages.signup.verifySuccess') }}</h1>
					<p class="card-subtitle">{{ $t('message.pages.signup.verifySubtitle', { company }) }}</p>
					<div class="card-actions">
						<el-button type="primary" round @click="goPay">{{ $t('message.pages.signup.goPay') }}</el-button>
						<el-button round @click="$router.push('/login')">{{ $t('message.pages.signup.later') }}</el-button>
					</div>
				</div>

				<div v-else class="success-box">
					<div class="done-ico fail"><el-icon><ele-WarningFilled /></el-icon></div>
					<h1 class="card-title">{{ $t('message.pages.signup.verifyFailed') }}</h1>
					<p class="card-subtitle">{{ errorMsg }}</p>
					<div class="card-actions">
						<el-button round @click="$router.push('/signup')">{{ $t('message.pages.signup.reRegister') }}</el-button>
					</div>
				</div>
			</div>
		</main>

		<footer class="signup-footer">
			<p>{{ $t('message.pages.signup.footer') }}</p>
		</footer>
	</div>
</template>

<script lang="ts" setup name="signupVerify">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { NextLoading } from '/@/utils/loading';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { Session } from '/@/utils/storage';
import logoBlackTrans from '/@/assets/img/proNotify_logo_black_trans.png';
import _ from 'lodash-es';
import { VerifySignup } from './api';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const { systemConfig } = storeToRefs(SystemConfigStore());
const siteLogo = computed(() => {
	if (!_.isEmpty(systemConfig.value['login.site_logo'])) return systemConfig.value['login.site_logo'];
	return logoBlackTrans;
});

const state = ref<'verifying' | 'ok' | 'err'>('verifying');
const errorMsg = ref('');
const company = ref('');

onMounted(async () => {
	const token = (route.query?.token as string) || '';
	if (!token) {
		NextLoading.done();
		state.value = 'err';
		errorMsg.value = t('message.pages.signup.verifyFailed');
		return;
	}
	try {
		const res: any = await VerifySignup(token);
		NextLoading.done();
		if (res.code === 2000) {
			state.value = 'ok';
			company.value = res.data?.company || '';
		} else {
			state.value = 'err';
			errorMsg.value = res.msg || t('message.pages.signup.verifyFailed');
		}
	} catch (e) {
		state.value = 'err';
		errorMsg.value = t('message.pages.signup.networkError');
	}
});

const goPay = () => {
	// 跳到登录页, 登录后路由守卫会自动引导到 /signup/pay 完成开通支付
	router.push('/login');
	ElMessage.info(t('message.pages.signup.checkGoLogin'));
};
</script>

<style scoped lang="scss">
@import './styles';

.spin { font-size: 40px; color: #409eff; animation: spin 1s linear infinite; }
@keyframes spin {
	from { transform: rotate(0deg); }
	to { transform: rotate(360deg); }
}

.done-ico {
	font-size: 52px;
	margin: 10px 0 4px;
	&.ok { color: #67c23a; }
	&.fail { color: #f56c6c; }
}
</style>