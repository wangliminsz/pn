<template>
	<div class="login-page">
		<!-- 左上角 Logo -->
		<header class="login-header">
			<img :src="siteLogo" class="brand-mark" />
		</header>

		<!-- 居中表单 -->
		<main class="login-panel">
			<div class="login-card">
				<div class="card-head">
					<img :src="siteLogo" class="card-logo" />
					<h1 class="card-title">
						{{ pageTitle }}
					</h1>
					<!-- <p class="card-subtitle">{{ $t('message.pages.login.subtitle') }}</p> -->
					 <div style="margin-top:40px;"></div>
				</div>

				<ResetPwdToken v-if="resetToken" />
				<ForgotPwd v-else-if="forgotMode" @back="forgotMode = false" />
				<ChangePwd v-else-if="userInfos.pwd_change_count === 0" />
				<Account v-else />

				<div class="card-lang" @click="toggleLang">
					{{ $t('message.pages.login.footer.lang') }} · {{ currentLangLabel }}
				</div>
			</div>
		</main>

		<footer class="login-footer">
			<p>© 2026-2028 proNotify · All rights reserved</p>
		</footer>
	</div>
</template>

<script setup lang="ts" name="loginIndex">
import { defineAsyncComponent, onMounted, computed, ref, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { NextLoading } from '/@/utils/loading';
import mittBus from '/@/utils/mitt';
import { useI18n } from 'vue-i18n';
import logoBlackTrans from '/@/assets/img/proNotify_logo_black_trans.png';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { useUserInfo } from '/@/stores/userInfo';
import _ from 'lodash-es';

// 引入组件
const Account = defineAsyncComponent(() => import('/@/views/system/login/component/account.vue'));
const ChangePwd = defineAsyncComponent(() => import('/@/views/system/login/component/changePwd.vue'));
const ForgotPwd = defineAsyncComponent(() => import('/@/views/system/login/component/forgotPwd.vue'));
const ResetPwdToken = defineAsyncComponent(() => import('/@/views/system/login/component/resetPwdToken.vue'));

const route = useRoute();
const forgotMode = ref(false);
const resetToken = computed(() => (route.query?.token as string) || '');
const pageTitle = computed(() => {
	if (resetToken.value) return t('message.pages.login.validation.resetPassword');
	if (forgotMode.value) return t('message.pages.login.account.forgotPassword');
	return userInfos.value.pwd_change_count === 0 ? t('message.pages.login.validation.firstLoginChangePwd') : t('message.pages.login.signInText');
});

const { userInfos } = storeToRefs(useUserInfo());
const { t, locale } = useI18n();

const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);

const systemConfigStore = SystemConfigStore();
const { systemConfig } = storeToRefs(systemConfigStore);

const getThemeConfig = computed(() => themeConfig.value);
const getSystemConfig = computed(() => systemConfig.value);

const siteLogo = computed(() => {
	if (!_.isEmpty(getSystemConfig.value['login.site_logo'])) {
		return getSystemConfig.value['login.site_logo'];
	}
	return logoBlackTrans;
});

const currentLangLabel = computed(() => {
	const map: Record<string, string> = { 'zh-cn': '中文', en: 'EN', 'zh-tw': '繁中', th: 'ไทย' };
	return map[locale.value] || 'EN';
});

const toggleLang = () => {
	const order = ['en', 'zh-cn', 'th', 'zh-tw'];
	const next = order[(order.indexOf(locale.value) + 1) % order.length];
	locale.value = next;
	// 同步 themeConfig, 保证登录后 initBackEndControlRoutes 请求菜单用对语言
	themeConfig.value.globalI18n = next;
};

onMounted(() => {
	if (resetToken.value) NextLoading.done();
	// 登录页「忘记密码」链接 → 切换为找回密码视图
	mittBus.on('openForgot', () => {
		forgotMode.value = true;
	});
	NextLoading.done();
});

onUnmounted(() => {
	mittBus.off('openForgot', () => {});
});
</script>

<style scoped lang="scss">
.login-page {
	// ---- 品牌 token（深色下提亮主色，与后台深色一致） ----
	--pn-primary: #409eff;
	--pn-primary-hover: #66b1ff;
	--pn-card: #1a1a1c;
	--pn-card-border: #333333;
	--pn-text: #dadada;
	--pn-muted: #b1b4b8;
	--pn-faint: #8f9297;
	// 不覆盖任何 el-* 变量，让深色主题的变量自然生效，登录页与后台完全一致

	position: relative;
	display: flex;
	flex-direction: column;
	min-height: 100dvh;
	font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
	color: var(--pn-text);
	background: #1f1f1f;
}

// ---- 左上角 Logo ----
.login-header {
	position: absolute;
	top: 28px;
	left: 32px;
	z-index: 2;

	.brand-mark {
		display: block;
		width: 190px;
		height: auto;
		max-width: 100%;
	}
}

// ---- 居中表单 ----
.login-panel {
	flex: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 96px 24px 32px;

	.login-card {
		width: 100%;
		max-width: 400px;
		background: var(--pn-card);
		border: 1px solid var(--pn-card-border);
		border-radius: 16px;
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
		padding: 36px 36px 24px;

		.card-head {
			margin-bottom: 26px;
			text-align: center;

			.card-logo {
				width: 168px;
				height: auto;
				margin: 0 auto 20px;
				display: block;
			}

			.card-title {
				font-size: 26px;
				font-weight: 600;
				color: var(--pn-text);
				letter-spacing: -0.4px;
				margin: 0 0 8px;
			}

			.card-subtitle {
				font-size: 14px;
				color: var(--pn-muted);
				line-height: 1.5;
				margin: 0;
			}
		}

		.card-lang {
			margin-top: 22px;
			text-align: center;
			font-size: 13px;
			color: var(--pn-faint);
			cursor: pointer;
			user-select: none;

			&:hover {
				color: var(--pn-primary);
			}
		}
	}
}

// ---- 底部 ----
.login-footer {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 16px;
	flex-wrap: wrap;
	padding: 16px 32px max(56px, env(safe-area-inset-bottom));
	font-size: 12px;
	color: var(--pn-faint);

	p {
		margin: 0;
	}
}

// ---- 响应式 ----
@media (max-width: 480px) {
	.login-header {
		top: 20px;
		left: 20px;

		.brand-mark {
			width: 150px;
		}
	}

	.login-panel {
		padding: 80px 20px 24px;
	}

	.login-card {
		padding: 28px 24px 20px;
	}
}

// 子组件（account/changePwd）输入框与按钮跟随深色主题
:deep(.login-card) {
	.el-input__wrapper {
		border-radius: 10px;
		background: #242424;
		box-shadow: 0 0 0 1px #333333 inset;
		transition: box-shadow 0.2s ease;

		&:hover {
			box-shadow: 0 0 0 1px #444444 inset;
		}

		&.is-focus {
			box-shadow: 0 0 0 1.5px var(--pn-primary) inset;
		}
	}

	.el-input__inner {
		font-size: 14px;
		color: #eaeaea;
		height: 44px;
	}

	.el-input__prefix,
	.el-input__suffix {
		color: #b1b4b8;
	}

	.el-input__suffix .iconfont {
		color: #b1b4b8;
	}

	.login-content-submit {
		height: 46px;
		font-size: 15px;
		font-weight: 600;
		border-radius: 10px;
		background: var(--pn-primary);
		border: none;
		box-shadow: 0 4px 14px rgba(0, 0, 0, 0.3);
		transition: all 0.2s ease;
		letter-spacing: 0.5px;

		&:hover {
			background: var(--pn-primary-hover);
			box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
			transform: translateY(-1px);
		}

		&:active {
			transform: scale(0.99);
		}
	}

	.el-form-item__error {
		color: #f56c6c;
	}
}
</style>
