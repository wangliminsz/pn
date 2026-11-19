<template>
	<fs-page>
		<fs-crud ref="crudRef" v-bind="crudBinding"> </fs-crud>
	</fs-page>
</template>

<script lang="ts" setup name="tenant">
import { ref, onMounted, watch } from 'vue';
import { useFs } from '@fast-crud/fast-crud';
import { createCrudOptions } from './crud';
import { useThemeConfig } from '/@/stores/themeConfig';
import { storeToRefs } from 'pinia';

const { themeConfig } = storeToRefs(useThemeConfig());

const { crudBinding, crudRef, crudExpose, resetCrudOptions } = useFs({ createCrudOptions, context: {} });

watch(
	() => themeConfig.value.globalI18n,
	() => {
		resetCrudOptions();
	}
);

onMounted(() => {
	crudExpose.doRefresh();
});
</script>
