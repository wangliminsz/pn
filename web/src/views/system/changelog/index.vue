<template>
	<div class="cl-page">
		<div class="page-head">
			<span class="title">{{ $t('message.pages.changelog.title') }}</span>
			<span class="sub">{{ $t('message.pages.changelog.sub') }}</span>
		</div>

		<div v-loading="loading" class="cl-panel">
			<div v-if="!loading && logs.length === 0" class="cl-empty">
				{{ $t('message.pages.changelog.empty') }}
			</div>

			<div v-for="log in logs" :key="log.id" class="cl-row">
				<div class="cl-main">
					<div class="cl-top">
						<span class="cl-prop">{{ log.property_name || $t('message.pages.changelog.property', { id: log.property }) }}</span>
						<span class="cl-tenant" v-if="log.tenant_name && isSuper">{{ log.tenant_name }}</span>
					</div>
					<div class="cl-text">
						<span class="cl-op">{{ log.user_name || '—' }}</span>
						<span class="cl-action">{{ $t('message.pages.changelog.action') }}</span>
						<span class="cl-val">{{ log.from_value || $t('message.pages.changelog.emptyValue') }}</span>
						<el-icon class="cl-arrow"><ele-Right /></el-icon>
						<span class="cl-val">{{ log.to_value || $t('message.pages.changelog.emptyValue') }}</span>
					</div>
					<div class="cl-owner" v-if="log.owner_name">{{ $t('message.pages.changelog.currentOwner', { name: log.owner_name }) }}</div>
				</div>
				<div class="cl-time">{{ fmtTime(log.create_datetime) }}</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup name="changelog">
import { ref, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
import { GetChangeLogs } from './api';

const { userInfos } = storeToRefs(useUserInfo());
const isSuper = computed(() => userInfos.value.is_superuser);

const logs = ref<any[]>([]);
const loading = ref(false);

const fmtTime = (v: any) => (v ? String(v).replace('T', ' ').slice(0, 16) : '');

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetChangeLogs();
		if (res.code === 2000) logs.value = res.data || [];
	} finally {
		loading.value = false;
	}
};

onMounted(load);
</script>

<style scoped lang="scss">
.cl-page {
	max-width: 1100px;
	color: #eaeaea;

	.page-head {
		margin-bottom: 16px;
		.title { font-size: 18px; font-weight: 600; color: #f4f4f5; }
		.sub { margin-left: 10px; font-size: 13px; color: #b1b4b8; }
	}

	.cl-panel {
		min-height: 100px;
		.cl-empty {
			text-align: center;
			color: #94979c;
			padding: 60px 0;
		}
		.cl-row {
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 12px;
			padding: 14px 16px;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			background: #1a1a1c;
			margin-bottom: 10px;
			transition: border-color 0.2s;
			&:hover { border-color: rgba(64, 158, 255, 0.45); }

			.cl-main { min-width: 0; }
			.cl-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
			.cl-prop { font-weight: 600; color: #f0f0f1; }
			.cl-tenant {
				font-size: 11px;
				color: #9ec9ff;
				background: rgba(64, 158, 255, 0.12);
				border: 1px solid rgba(64, 158, 255, 0.35);
				border-radius: 4px;
				padding: 1px 6px;
			}
			.cl-text {
				display: flex;
				align-items: center;
				gap: 4px;
				flex-wrap: wrap;
				font-size: 13px;
				color: #d8dade;
				.cl-op { color: #f0f0f1; font-weight: 600; }
				.cl-action { color: #b1b4b8; }
				.cl-val { color: #9ec9ff; }
				.cl-arrow { color: #7d8188; font-size: 12px; }
			}
			.cl-owner { font-size: 12px; color: #94979c; margin-top: 3px; }
			.cl-time { font-size: 12px; color: #94979c; flex-shrink: 0; }
		}
	}
}
</style>
