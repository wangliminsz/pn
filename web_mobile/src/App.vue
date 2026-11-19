<template>
	<van-config-provider theme="dark" :theme-vars="themeVars">
		<router-view v-slot="{ Component }">
			<transition name="page-fade" mode="out-in">
				<component :is="Component" :key="$route.fullPath" />
			</transition>
		</router-view>
	</van-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';

const themeVars = {
	primaryColor: '#409EFF',
	primaryColorEnd: '#66B1FF',
	successColor: '#67C23A',
	dangerColor: '#F56C6C',
	warningColor: '#E6A23C',
	background: '#1F1F1F',
	background2: '#1A1A1C',
	background3: '#212121',
	textColor: '#DADADA',
	textColor2: '#9B9DA1',
	textColor3: '#7A7A7A',
	borderColor: '#2A2A2A',
	activeColor: '#212121',
	cellBackground: '#1A1A1C',
	cellBorderColor: '#2A2A2A',
	fieldLabelColor: '#9B9DA1',
	fieldInputTextColor: '#EAEAEA',
	fieldPlaceholderTextColor: '#6F7175',
	navBarBackground: '#171717',
	navBarTitleTextColor: '#EAEAEA',
	navBarIconColor: '#DADADA',
	popupBackground: '#1A1A1C',
	dialogBackground: '#1A1A1C',
	pickerBackground: '#1A1A1C',
	pickerOptionTextColor: '#9B9DA1',
	pickerCancelActionColor: '#9B9DA1',
	pickerConfirmActionColor: '#409EFF',
	buttonPrimaryBackground: '#409EFF',
	buttonPrimaryBorderColor: '#409EFF',
	buttonDefaultBackground: '#242424',
	buttonDefaultColor: '#DADADA',
	buttonDefaultBorderColor: '#333333',
	toastBackground: 'rgba(20,20,20,.94)',
};

const auth = useAuthStore();
onMounted(() => {
	auth.restore();
});
</script>
