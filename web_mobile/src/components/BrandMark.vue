<template>
	<div class="brand-mark" :style="{ width: `${size}px`, height: `${size}px`, borderRadius: `${size * 0.28}px` }">
		<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
			<path d="m3 9.5 9-7 9 7V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20z" />
			<path d="M9 21.5v-7h6v7" />
		</svg>
	</div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number }>(), { size: 42 });
</script>

<style scoped>
.brand-mark {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 auto;
	background: linear-gradient(145deg, #ff7a1a 0%, var(--pn-accent) 55%, #c2410c 100%);
	color: #fff;
	box-shadow: 0 8px 22px rgba(234, 88, 12, 0.28);
}

.brand-mark svg {
	width: 58%;
	height: 58%;
}
</style>
