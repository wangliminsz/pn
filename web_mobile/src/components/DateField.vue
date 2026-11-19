<template>
	<van-field
		:model-value="displayText"
		:label="label"
		:placeholder="placeholder"
		readonly
		is-link
		@click="open"
	>
		<template #right-icon>
			<button
				v-if="clearable && modelValue"
				type="button"
				class="clear-btn"
				aria-label="Clear date"
				@click.stop="clear"
			>
				<Icon name="x" :size="14" />
			</button>
		</template>
	</van-field>

	<van-popup v-model:show="visible" position="bottom" round teleport="body">
		<van-date-picker
			v-model="pickerValue"
			:title="label"
			:min-date="minDate"
			:max-date="maxDate"
			@confirm="onConfirm"
			@cancel="visible = false"
		/>
	</van-popup>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Icon from './Icon.vue';

const props = withDefaults(
	defineProps<{
		modelValue?: string;
		label: string;
		placeholder?: string;
		minDate?: Date;
		maxDate?: Date;
		clearable?: boolean;
	}>(),
	{
		modelValue: '',
		placeholder: 'Select date',
		minDate: () => new Date(1970, 0, 1),
		maxDate: () => new Date(2100, 11, 31),
		clearable: true,
	},
);

const emit = defineEmits<{
	'update:modelValue': [value: string];
}>();

const visible = ref(false);
const pickerValue = ref<string[]>(toValues(props.modelValue || today()));

const displayText = computed(() => props.modelValue || '');

function today() {
	return toISO(new Date());
}

function toISO(date: Date) {
	const month = `${date.getMonth() + 1}`.padStart(2, '0');
	const day = `${date.getDate()}`.padStart(2, '0');
	return `${date.getFullYear()}-${month}-${day}`;
}

function toValues(value: string) {
	const [year, month, day] = value.split('-');
	if (!year || !month || !day) {
		const now = new Date();
		return [`${now.getFullYear()}`, `${now.getMonth() + 1}`.padStart(2, '0'), `${now.getDate()}`.padStart(2, '0')];
	}
	return [year, month.padStart(2, '0'), day.padStart(2, '0')];
}

function open() {
	pickerValue.value = toValues(props.modelValue || today());
	visible.value = true;
}

function clear() {
	emit('update:modelValue', '');
}

function onConfirm({ selectedValues }: { selectedValues: string[] }) {
	const [year, month, day] = selectedValues;
	emit('update:modelValue', `${year}-${month}-${day}`);
	visible.value = false;
}
</script>

<style scoped>
.clear-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 24px;
	height: 24px;
	margin-right: 2px;
	padding: 0;
	border: 0;
	border-radius: 50%;
	background: #2a2a2a;
	color: var(--pn-muted);
}

.clear-btn:hover {
	color: var(--pn-text);
	background: #343434;
}
</style>
