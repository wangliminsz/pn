<template>
	<div class="cal-page">
		<!-- 头部 -->
		<div class="cal-head">
			<div class="left">
				<span class="title">{{ $t('message.pages.calendar.title') }}</span>
				<span class="sub">{{ $t('message.pages.calendar.sub') }}</span>
			</div>
			<div class="nav">
				<el-button class="soft-ghost" size="small" @click="jumpMonth(-1)">
					<el-icon><ele-ArrowLeft /></el-icon>
				</el-button>
				<el-button class="soft-ghost" size="small" @click="goToday">{{ $t('message.pages.calendar.today') }}</el-button>
				<span class="ym">{{ $t('message.pages.calendar.yearMonth', { year: viewYear, month: viewMonth }) }}</span>
				<el-button class="soft-ghost" size="small" @click="jumpMonth(1)">
					<el-icon><ele-ArrowRight /></el-icon>
				</el-button>
			</div>
		</div>

		<!-- 图例 -->
		<div class="legend">
			<span class="lg"><span class="dot dot-rent"></span>{{ $t('message.pages.calendar.legendRent') }}</span>
			<span class="lg"><span class="dot dot-end"></span>{{ $t('message.pages.calendar.legendEnd') }}</span>
			<span class="lg"><span class="dot dot-rule"></span>{{ $t('message.pages.calendar.legendRule') }}</span>
			<span class="lg"><span class="dot dot-today"></span>{{ $t('message.pages.calendar.legendToday') }}</span>
		</div>

		<!-- 月历 -->
		<div class="cal-grid" v-loading="loading">
			<div class="wk" v-for="w in weekdays" :key="w">{{ w }}</div>
			<div v-for="cell in cells" :key="cell.key" class="day"
				:class="{
					'other-month': cell.outside,
					'is-today': cell.isToday,
					'has-event': cell.events.length > 0,
				}"
				@click="cell.events.length && selectDay(cell)">
				<div class="day-num">{{ cell.day }}</div>
				<div class="day-events">
					<div v-for="(e, i) in cell.events.slice(0, 3)" :key="i" class="ev"
						:class="{ 'ev-end': e.kind === 'end', 'ev-rule': e.kind === 'utility' || e.kind === 'custom' }" :title="evTitle(e)">
						<span class="ev-k">{{ evKindShort(e) }}</span>
						<span class="ev-n">{{ e.name }}</span>
					</div>
					<div v-if="cell.events.length > 3" class="ev-more">{{ $t('message.pages.calendar.more', { n: cell.events.length - 3 }) }}</div>
					<div v-if="cell.events.length === 0" class="ev-empty"></div>
				</div>
			</div>
		</div>

		<!-- 当日明细 -->
		<el-drawer v-model="detailVisible" :title="detailTitle" size="420px" append-to-body>
			<div class="detail-list">
				<div v-for="(e, i) in selectedEvents" :key="i" class="detail-item"
					:class="{ 'is-end': e.kind === 'end', 'is-rule': e.kind === 'utility' || e.kind === 'custom' }">
					<div class="d-top">
						<span class="d-tag">{{ evKindLabel(e) }}</span>
						<span class="d-name">{{ e.name }}</span>
					</div>
					<div v-if="e.kind === 'end'" class="d-meta">{{ $t('message.pages.calendar.endDate') }} {{ e.rent_end }}{{ e.line_bot_name ? ` · ${e.line_bot_name}` : '' }}</div>
					<div v-else-if="e.rule_id" class="d-meta">{{ e.rule_name || $t('message.pages.calendar.customReminder') }} · {{ periodLabel(e.pay_period) }} {{ e.remind_day }} {{ $t('message.pages.calendar.day') }}{{ e.line_bot_name ? ` · ${e.line_bot_name}` : '' }}</div>
					<div v-else class="d-meta">{{ periodLabel(e.pay_period) }} {{ e.remind_day }} {{ $t('message.pages.calendar.day') }}{{ e.rent_amount ? ` · ฿${Number(e.rent_amount).toLocaleString()}` : '' }}{{ e.line_bot_name ? ` · ${e.line_bot_name}` : '' }}</div>
					<div class="d-rent">{{ $t('message.pages.calendar.rentPeriod') }} {{ e.rent_start || '—' }} {{ $t('message.pages.calendar.to') }} {{ e.rent_end || '—' }}</div>
				</div>
				<div v-if="!selectedEvents.length" class="d-empty">{{ $t('message.pages.calendar.noReminder') }}</div>
			</div>
		</el-drawer>
	</div>
</template>

<script lang="ts" setup name="reminderCalendar">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { GetCalendarMonth } from './api';

const { t, tm } = useI18n();

const weekdays = computed(() => tm('message.pages.calendar.weekdays') as unknown as string[]);

const now = new Date();
const viewYear = ref(now.getFullYear());
const viewMonth = ref(now.getMonth() + 1); // 1-12
const todayStr = ref('');
const loading = ref(false);
const eventsByDay = ref<Record<string, any[]>>({});

const detailVisible = ref(false);
const selectedEvents = ref<any[]>([]);
const detailTitle = ref('');

const goToday = () => {
	viewYear.value = now.getFullYear();
	viewMonth.value = now.getMonth() + 1;
	load();
};
const jumpMonth = (delta: number) => {
	let m = viewMonth.value + delta;
	let y = viewYear.value;
	if (m < 1) { m = 12; y--; }
	if (m > 12) { m = 1; y++; }
	viewYear.value = y;
	viewMonth.value = m;
	load();
};

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetCalendarMonth(viewYear.value, viewMonth.value);
		if (res.code === 2000) {
			eventsByDay.value = res.data?.days || {};
			todayStr.value = res.data?.today || '';
		}
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
};

const cells = computed(() => {
	const year = viewYear.value;
	const month = viewMonth.value;
	const first = new Date(year, month - 1, 1);
	const startWeekday = first.getDay(); // 0=日
	const daysInMonth = new Date(year, month, 0).getDate();
	const prevDays = new Date(year, month - 1, 0).getDate();
	const out: any[] = [];
	const iso = (y: number, m: number, d: number) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

	// 上月补位(从周日开始对齐)
	for (let i = startWeekday - 1; i >= 0; i--) {
		const d = prevDays - i;
		const py = month === 1 ? year - 1 : year;
		const pm = month === 1 ? 12 : month - 1;
		const keyIso = iso(py, pm, d);
		out.push({ key: `prev-${d}`, day: d, outside: true, isToday: false, events: eventsByDay.value[keyIso] || [], dateIso: keyIso });
	}
	// 当月
	for (let d = 1; d <= daysInMonth; d++) {
		const keyIso = iso(year, month, d);
		out.push({
			key: keyIso, day: d, outside: false,
			isToday: keyIso === todayStr.value,
			events: eventsByDay.value[keyIso] || [],
			dateIso: keyIso,
		});
	}
	// 下月补位到 6 行(42格)
	let nextDay = 1;
	while (out.length % 7 !== 0) {
		const ny = month === 12 ? year + 1 : year;
		const nm = month === 12 ? 1 : month + 1;
		const keyIso = iso(ny, nm, nextDay);
		out.push({ key: `next-${nextDay}`, day: nextDay, outside: true, isToday: false, events: eventsByDay.value[keyIso] || [], dateIso: keyIso });
		nextDay++;
	}
	return out;
});

const evTitle = (e: any) =>
	e.kind === 'end'
		? t('message.pages.calendar.evTitleEnd', { name: e.name, rent_end: e.rent_end })
		: e.rule_id
			? t('message.pages.calendar.evTitleRule', { name: e.name, rule: e.rule_name || t('message.pages.calendar.customReminder'), period: periodLabel(e.pay_period), day: e.remind_day })
			: t('message.pages.calendar.evTitleRent', { name: e.name, period: periodLabel(e.pay_period), day: e.remind_day });

const evKindLabel = (e: any) =>
	e.kind === 'end' ? t('message.pages.calendar.labelEnd') : e.kind === 'utility' ? t('message.pages.calendar.labelUtility') : e.kind === 'custom' ? t('message.pages.calendar.labelCustom') : (e.pay_period === 'Quarterly' ? t('message.pages.calendar.quarterlyRent') : periodLabel(e.pay_period) + t('message.pages.calendar.rentSuffix'));

const evKindShort = (e: any) =>
	e.kind === 'end' ? t('message.pages.calendar.kindEnd') : e.kind === 'utility' ? t('message.pages.calendar.kindUtility') : e.kind === 'custom' ? t('message.pages.calendar.kindCustom') : t('message.pages.calendar.kindRent');

const periodLabel = (v: any) => (v === 'Quarterly' ? t('message.pages.calendar.period.quarterly') : v === 'HalfYear' ? t('message.pages.calendar.period.halfYear') : v === 'Yearly' ? t('message.pages.calendar.period.yearly') : t('message.pages.calendar.period.monthly'));

const selectDay = (cell: any) => {
	selectedEvents.value = cell.events;
	detailTitle.value = t('message.pages.calendar.detailTitle', { date: cell.dateIso });
	detailVisible.value = true;
};

onMounted(load);
</script>

<style lang="scss">
.cal-page {
	max-width: 1100px;
	margin: 0 auto;
	color: #eaeaea;

	.cal-head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 14px;

		.title { font-size: 18px; font-weight: 600; color: #f4f4f5; }
		.sub { display: block; margin-top: 4px; font-size: 12px; color: #b1b4b8; }
		.nav { display: flex; align-items: center; gap: 8px;
			.ym { font-size: 15px; font-weight: 600; color: #f0f0f1; min-width: 110px; text-align: center; }
		}
	}

	.legend { display: flex; gap: 16px; margin-bottom: 12px; font-size: 12px; color: #b1b4b8;
		.lg { display: inline-flex; align-items: center; gap: 5px; }
		.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block;
			&.dot-rent { background: rgba(64, 158, 255, 0.85); }
			&.dot-end { background: rgba(245, 108, 108, 0.85); }
			&.dot-rule { background: rgba(103, 194, 58, 0.85); }
			&.dot-today { width: 0; height: 0; border: 4px solid #e6a23c; border-radius: 50%; background: transparent; }
		}
	}

	.cal-grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		gap: 6px;
		min-height: 460px;

		.wk {
			text-align: center;
			font-size: 12px;
			color: #b1b4b8;
			padding: 8px 0;
			font-weight: 600;
		}

		.day {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 8px;
			min-height: 86px;
			padding: 6px 8px;
			cursor: default;
			transition: border-color 0.15s;

			.day-num { font-size: 13px; color: #d8dade; font-weight: 500; }

			&.other-month { background: transparent; border-color: rgba(42, 42, 42, 0.4);
				.day-num { color: #7d8188; }
				.day-events .ev { opacity: 0.85; }
				&.has-event { cursor: pointer; &:hover { border-color: rgba(64, 158, 255, 0.45); } }
			}
			&.is-today { border-color: rgba(230, 162, 60, 0.7); background: rgba(230, 162, 60, 0.06);
				.day-num { color: #e6a23c; font-weight: 700; }
			}
			&.has-event { cursor: pointer; &:hover { border-color: rgba(64, 158, 255, 0.45); } }

			.day-events { margin-top: 4px; display: flex; flex-direction: column; gap: 3px;
				.ev {
					display: flex; align-items: center; gap: 4px;
					font-size: 10px; line-height: 1.2;
					padding: 2px 4px; border-radius: 4px;
					background: rgba(64, 158, 255, 0.12);
					color: #9ec9ff;
					overflow: hidden; white-space: nowrap;
					.ev-k { flex-shrink: 0; font-weight: 600; }
					.ev-n { overflow: hidden; text-overflow: ellipsis; }
					&.ev-end { background: rgba(245, 108, 108, 0.12); color: #f28f8f; }
					&.ev-rule { background: rgba(103, 194, 58, 0.12); color: #95d475; }
				}
				.ev-more { font-size: 10px; color: #94979c; }
				.ev-empty { height: 2px; }
			}
		}
	}
}

// 当日明细 drawer
.detail-list {
	.detail-item {
		background: #1a1a1c;
		border: 1px solid #2a2a2a;
		border-left: 3px solid #409eff;
		border-radius: 8px;
		padding: 12px 14px;
		margin-bottom: 10px;

		&.is-end { border-left-color: #f56c6c; }
		&.is-rule { border-left-color: #67c23a; }

		.d-top { display: flex; align-items: center; gap: 8px; }
		.d-tag {
			font-size: 11px; padding: 2px 7px; border-radius: 4px;
			background: rgba(64, 158, 255, 0.14); color: #9ec9ff;
			flex-shrink: 0;
			.is-end & { background: rgba(245, 108, 108, 0.14); color: #f28f8f; }
		}
		.d-name { font-weight: 600; color: #f0f0f1; font-size: 14px; }
		.d-meta { margin-top: 6px; font-size: 12px; color: #b1b4b8; }
		.d-rent { margin-top: 3px; font-size: 11px; color: #94979c; }
	}
	.d-empty { text-align: center; color: #94979c; padding: 40px 0; font-size: 13px; }
}

.soft-ghost {
	background: transparent !important;
	border-color: #333 !important;
	color: #b1b4b8 !important;
	&:hover, &:focus { background: rgba(255, 255, 255, 0.05) !important; color: #c0c4cc !important; }
}
</style>