<template>
	<div class="signup-page">
		<header class="signup-header">
			<img :src="siteLogo" class="brand-mark" />
		</header>

		<main class="signup-panel">
			<div class="signup-card">
				<div class="card-head">
					<img :src="siteLogo" class="card-logo" />
					<h1 class="card-title">{{ $t('message.pages.signup.createTitle') }}</h1>
					<!-- <p class="card-subtitle">{{ $t('message.pages.signup.createSubtitle') }}</p> -->
				</div>

				<el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @keyup.enter="submit">
					<el-form-item prop="email">
						<el-input v-model="form.email" :placeholder="$t('message.pages.signup.emailPlaceholder')" clearable autocomplete="off">
							<template #prefix><el-icon><ele-Message /></el-icon></template>
						</el-input>
					</el-form-item>
					<el-form-item prop="company">
						<el-input v-model="form.company" :placeholder="$t('message.pages.signup.companyPlaceholder')" clearable autocomplete="off">
							<template #prefix><el-icon><ele-OfficeBuilding /></el-icon></template>
						</el-input>
					</el-form-item>
					<!-- <el-form-item prop="contact_phone">
						<el-input v-model="form.contact_phone" :placeholder="$t('message.pages.signup.phonePlaceholder')" clearable autocomplete="off">
							<template #prefix><el-icon><ele-Iphone /></el-icon></template>
						</el-input>
					</el-form-item> -->
					<el-form-item prop="referral_code">
						<el-input v-model="form.referral_code" :placeholder="$t('message.pages.signup.referralPlaceholder')" clearable autocomplete="off">
							<template #prefix><el-icon><ele-Present /></el-icon></template>
						</el-input>
					</el-form-item>
					<el-form-item prop="password">
						<el-input v-model="form.password" type="password" :placeholder="$t('message.pages.signup.passwordPlaceholder')" autocomplete="new-password" show-password>
							<template #prefix><el-icon><ele-Lock /></el-icon></template>
						</el-input>
					</el-form-item>

					<el-button type="primary" round class="submit-btn" :loading="sending" @click="submit">
						{{ $t('message.pages.signup.submit') }}
					</el-button>
				</el-form>

				<div class="card-foot">
					<span>{{ $t('message.pages.signup.haveAccount') }}&nbsp </span>
					<el-button link type="primary" @click="$router.push('/login')">{{ $t('message.pages.signup.goLogin') }}</el-button>
				</div>
			</div>
		</main>

		<footer class="signup-footer">
			<p>{{ $t('message.pages.signup.footer') }}</p>
		</footer>
	</div>
</template>

<script lang="ts" setup name="signupForm">
import { reactive, ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { NextLoading } from '/@/utils/loading';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { useThemeConfig } from '/@/stores/themeConfig';
import logoBlackTrans from '/@/assets/img/proNotify_logo_black_trans.png';
import _ from 'lodash-es';
import { SendSignup } from './api';

const { t } = useI18n();
const route = useRoute();

onMounted(() => {
	NextLoading.done();
	// 支持从 URL 带推荐码预填: /signup?refcode=XXXXXX
	const refcode = (route.query.refcode as string) || '';
	if (refcode) {
		form.referral_code = refcode.trim().toUpperCase();
	}
});

const router = useRouter();
const systemConfigStore = SystemConfigStore();
const { systemConfig } = storeToRefs(systemConfigStore);
const { themeConfig } = storeToRefs(useThemeConfig());

const siteLogo = computed(() => {
	if (!_.isEmpty(systemConfig.value['login.site_logo'])) return systemConfig.value['login.site_logo'];
	return logoBlackTrans;
});

const sending = ref(false);
const formRef = ref<any>();
const form = reactive({ email: '', company: '', contact_phone: '', password: '', referral_code: '' });

const rules = {
	email: [
		{ required: true, message: t('message.pages.signup.emailRequired'), trigger: 'blur' },
		{
			validator: (_: any, v: string, cb: any) =>
				!v || /^[A-Za-z0-9@._\-+]+$/.test(v) && v.includes('@') ? cb() : cb(new Error(t('message.pages.signup.emailInvalid'))),
			trigger: 'blur',
		},
	],
	company: [{ required: true, message: t('message.pages.signup.companyRequired'), trigger: 'blur' }],
	password: [
		{ required: true, message: t('message.pages.signup.passwordRequired'), trigger: 'blur' },
		{ min: 8, message: t('message.pages.signup.passwordMin'), trigger: 'blur' },
		{
			validator: (_: any, v: string, cb: any) =>
				!v || (/[a-zA-Z]/.test(v) && /\d/.test(v)) ? cb() : cb(new Error(t('message.pages.signup.passwordComplexity'))),
			trigger: 'blur',
		},
	],
};

const submit = () => {
	formRef.value.validate(async (valid: boolean) => {
		if (!valid) return;
		sending.value = true;
		try {
			const res: any = await SendSignup({
				email: form.email.trim(),
				company: form.company.trim(),
				contact_phone: form.contact_phone.trim(),
				password: form.password,
				referral_code: form.referral_code.trim(),
			});
			if (res.code === 2000) {
				ElMessage.success(res.msg || t('message.pages.signup.emailSent'));
				router.push({ path: '/signup/check', query: { email: form.email.trim() } });
			} else {
				ElMessage.warning(res.msg || t('message.pages.signup.signupFailed'));
			}
		} catch (e) {
			// 业务错误(如邮箱已注册)已由请求拦截器以通知形式提示, 这里不再重复弹
			if ((e as any)?.response?.status) {
				ElMessage.error(t('message.pages.signup.networkError'));
			}
		} finally {
			sending.value = false;
		}
	});
};
</script>

<style scoped lang="scss">
@import './styles';

// 与登录页按钮风格一致(round 基础上覆盖为 10px 小圆角)
.submit-btn {
	border-radius: 10px;
	height: 44px;
	font-size: 15px;
	font-weight: 600;
	letter-spacing: 0.5px;
}
</style>