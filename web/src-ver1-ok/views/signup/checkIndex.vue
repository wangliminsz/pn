<template>
	<div class="signup-page">
		<header class="signup-header">
			<img :src="siteLogo" class="brand-mark" />
		</header>

		<main class="signup-panel">
			<div class="signup-card center-card">
				<div class="done-ico"><el-icon><ele-Message /></el-icon></div>
				<h1 class="card-title">{{ $t('message.pages.signup.checkTitle') }}</h1>
				<p class="card-subtitle">
					{{ $t('message.pages.signup.checkSubtitle', { email }) }}
				</p>
				<div class="card-actions">
					<el-button type="primary" round @click="$router.push('/login')">{{ $t('message.pages.signup.checkGoLogin') }}</el-button>
				</div>
			</div>
		</main>

		<footer class="signup-footer">
			<p>{{ $t('message.pages.signup.footer') }}</p>
		</footer>
	</div>
</template>

<script lang="ts" setup name="signupCheckEmail">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { NextLoading } from '/@/utils/loading';
import { SystemConfigStore } from '/@/stores/systemConfig';
import logoBlackTrans from '/@/assets/img/proNotify_logo_black_trans.png';
import _ from 'lodash-es';

onMounted(() => {
	NextLoading.done();
});

const route = useRoute();
const { systemConfig } = storeToRefs(SystemConfigStore());
const siteLogo = computed(() => {
	if (!_.isEmpty(systemConfig.value['login.site_logo'])) return systemConfig.value['login.site_logo'];
	return logoBlackTrans;
});
const { t } = useI18n();
const email = computed(() => (route.query?.email as string) || t('message.pages.signup.yourEmail'));
</script>

<style scoped lang="scss">
@import './styles';
</style>