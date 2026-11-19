<template>
	<fs-page>
		<div class="quota-header" v-if="quotas.length">
			<el-card shadow="never" class="quota-card" v-for="q in quotas" :key="q.id" v-show="q.used != null && q.limit != null">
				<div class="quota-title">{{ q.name }}</div>
				<el-progress
					:percentage="percent(q)"
					:color="color(q)"
					:stroke-width="12"
					:text-inside="false"
				/>
				<div class="quota-text">
					<span>已用 {{ q.used }} / 上限 {{ q.limit }}</span>
				</div>
			</el-card>
		</div>
		<fs-crud ref="crudRef" v-bind="crudBinding"> </fs-crud>
	</fs-page>
</template>

<script lang="ts" setup name="messagelog">
import { ref, onMounted, watch } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { useThemeConfig } from '/@/stores/themeConfig';
import { storeToRefs } from 'pinia';
import { request } from '/@/utils/service';

const { themeConfig } = storeToRefs(useThemeConfig());

const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context: {} });

const quotas = ref<any[]>([]);

const percent = (q: any) => {
	if (!q.limit) return 0;
	return Math.min(100, Math.round(((q.used ?? 0) / q.limit) * 100));
};
const color = (q: any) => {
	const p = percent(q);
	if (p >= 90) return '#f56c6c';
	if (p >= 70) return '#e6a23c';
	return '#67c23a';
};

const loadQuota = async () => {
	const res: any = await request({ url: '/api/notify/linebot/quota_list/', method: 'get' });
	quotas.value = res?.data ?? [];
};

watch(
	() => themeConfig.value.globalI18n,
	() => {
		resetCrudOptions();
	}
);

onMounted(() => {
	crudExpose.doRefresh();
	loadQuota();
});
</script>

<style scoped>
.quota-header {
	display: flex;
	gap: 12px;
	flex-wrap: wrap;
	margin-bottom: 14px;
}
.quota-card {
	flex: 1;
	min-width: 200px;
}
.quota-title {
	font-weight: 600;
	margin-bottom: 8px;
}
.quota-text {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-top: 6px;
	font-size: 12px;
	color: #a5a8ae;
}
</style>
