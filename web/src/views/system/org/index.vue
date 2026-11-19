<template>
	<div class="org-page">
		<div class="page-head">
			<span class="title">{{ $t('message.pages.org.title') }}</span>
			<span class="sub">{{ $t('message.pages.org.sub') }}</span>
		</div>

		<div v-if="!isManager" class="no-auth">
			{{ $t('message.pages.org.noAuth') }}
		</div>

		<OrgChartDialog v-else-if="tenantObj" :model-value="true" :tenant="tenantObj" :inline="true" />
	</div>
</template>

<script lang="ts" setup name="tenantOrg">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
import OrgChartDialog from '/@/views/admin/tenant/components/OrgChartDialog.vue';

const { userInfos } = storeToRefs(useUserInfo());

const isManager = computed(() =>
	(userInfos.value.role_info || []).some((r: any) => r.key === 'tenant_manager')
);

const tenantObj = computed(() =>
	userInfos.value.tenant_id ? { id: userInfos.value.tenant_id, name: userInfos.value.tenant_name || '' } : null
);
</script>

<style scoped lang="scss">
.org-page {
	max-width: 1200px;
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

	.no-auth {
		background: rgba(245, 108, 108, 0.1);
		border: 1px solid rgba(245, 108, 108, 0.3);
		border-radius: 10px;
		padding: 24px;
		text-align: center;
		color: #f28f8f;
	}
}
</style>