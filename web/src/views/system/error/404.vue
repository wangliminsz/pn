<template>
	<div class="pn-404">
		<div class="pn-404-glow"></div>
		<div class="pn-404-card">
			<div class="pn-404-num">404</div>
			<h1 class="pn-404-title">Page Not Found</h1>
			<p class="pn-404-msg">The page you're looking for doesn't exist or may have been moved. Check the URL and try again.</p>
			<el-button class="pn-404-btn" round @click="onGoHome">
				{{ isSuperuser ? 'Back to Experience' : 'Back to Home' }}
			</el-button>
		</div>
	</div>
</template>

<script setup lang="ts" name="404">
import { useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';

const router = useRouter();
const { userInfos } = storeToRefs(useUserInfo());

const isSuperuser = userInfos.value.is_superuser;

const onGoHome = () => {
	if (userInfos.value.is_superuser) {
		router.push('/admin/dashboard');
	} else {
		router.push('/');
	}
};
</script>

<style scoped lang="scss">
/* proNotify 深色主题: 与登录页 / 后台深色一致 (design-system/pronotify/MASTER.md) */
.pn-404 {
	--pn-bg: #1f1f1f;
	--pn-card: #1a1a1c;
	--pn-border: #2a2a2a;
	--pn-primary: #409eff;
	--pn-primary-hover: #66b1ff;
	--pn-accent: #ea580c;
	--pn-text: #dadada;
	--pn-text-strong: #eaeaea;
	--pn-muted: #b1b4b8;
	--pn-faint: #8f9297;

	position: relative;
	min-height: 100dvh;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 24px;
	background: var(--pn-bg);
	font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
	color: var(--pn-text);
	overflow: hidden;
}

.pn-404-glow {
	position: absolute;
	top: 50%;
	left: 50%;
	width: 700px;
	height: 700px;
	transform: translate(-50%, -50%);
	background: radial-gradient(circle, rgba(64, 158, 255, 0.10) 0%, rgba(64, 158, 255, 0) 60%);
	pointer-events: none;
}

.pn-404-card {
	position: relative;
	z-index: 1;
	max-width: 560px;
	width: 100%;
	text-align: center;
	padding: 56px 48px;
	background: linear-gradient(180deg, var(--pn-card), #161618);
	border: 1px solid var(--pn-border);
	border-radius: 18px;
	box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
}

.pn-404-num {
	font-size: 92px;
	line-height: 1;
	font-weight: 700;
	letter-spacing: 0.04em;
	background: linear-gradient(135deg, #ffffff 0%, var(--pn-primary) 55%, var(--pn-accent) 100%);
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
}

.pn-404-title {
	margin: 22px 0 12px;
	font-size: 22px;
	font-weight: 600;
	color: var(--pn-text-strong);
}

.pn-404-msg {
	margin: 0 0 32px;
	font-size: 14px;
	line-height: 1.7;
	color: var(--pn-muted);
}

.pn-404-btn {
	--el-color-primary: var(--pn-primary);
	--el-color-primary-hover: var(--pn-primary-hover);
	--el-color-white: #ffffff;
	padding: 20px 44px;
	font-size: 15px;
	font-weight: 600;
	font-family: inherit;
	letter-spacing: 0.02em;
}
</style>
