<template>
	<div class="dashboard">
		<div class="stat-grid">
			<div v-for="card in cards" :key="card.label" class="stat-card">
				<div class="stat-icon" :style="{ background: card.color }">
					<el-icon><component :is="card.icon" /></el-icon>
				</div>
				<div class="stat-body">
					<div class="stat-value">{{ card.value }}</div>
					<div class="stat-label">{{ card.label }}</div>
				</div>
			</div>
		</div>

		<!-- 每日提醒发送时间(运行时配置) -->
		<div class="panel">
			<div class="panel-title">每日提醒发送时间</div>
			<div class="sched-row">
				<div class="sched-info">
					<div class="sched-cur">
						泰国时间 <b class="sched-hour">{{ fmtSched(sched.hour) }}:{{ fmtSched(sched.minute) }}</b>
						<el-tag v-if="sched.source === 'db'" size="small" effect="plain" type="success">运行时配置</el-tag>
						<el-tag v-else size="small" effect="plain">env.py 默认</el-tag>
					</div>
					<div class="sched-sub">
						{{ sched.source === 'db'
							? `已覆盖 env.py 默认值(${sched.env_default}:00)，改动立即生效`
							: `取自 env.py (NOTIFY_SEND_HOUR=${sched.env_default})，时区 ${sched.tz}` }}
					</div>
				</div>
				<div class="sched-ctrl">
					<el-select v-model="sched.hour" style="width: 110px" placeholder="小时">
						<el-option v-for="h in 24" :key="h - 1" :label="`${String(h - 1).padStart(2, '0')}:00`" :value="h - 1" />
					</el-select>
					<el-select v-model="sched.minute" style="width: 110px" placeholder="分钟">
						<el-option v-for="m in [0,5,10,15,20,25,30,35,40,45,50,55]" :key="m" :label="`${String(m).padStart(2, '0')} 分`" :value="m" />
					</el-select>
					<el-button class="sched-save" :loading="savingSched" @click="saveSched">保存并生效</el-button>
				</div>
			</div>
			<div class="dedup-row">
				<el-switch v-model="sched.dedup" active-color="#409eff" inactive-color="#4b4e57" />
				<div class="dedup-info">
					<div class="dedup-title">当日防重（同房源/同类型/同规则一天只发一次）</div>
					<div class="dedup-sub">默认<em>关闭</em>：命中即发（简单可靠、便于测试）。开启后定时任务会对「同一房源+同类型」当天已成功发送过的跳过。</div>
				</div>
			</div>
			<div class="env-hint">保存后立即写入数据库，内置调度器会在下一个检查周期(约 20 秒)按新时间触发，无需重启后端；时区固定为泰国时间。</div>
		</div>

		<!-- 提醒消息模板(运行时配置) -->
		<div class="panel">
			<div class="panel-title">提醒消息模板</div>
			<div class="tpl-grid">
				<div class="tpl-item">
					<div class="tpl-label">默认付租提醒模板</div>
					<el-input v-model="tplDraft.rent" type="textarea" :rows="7" class="tpl-ta" placeholder="留空 = 使用系统内置默认（泰/英双语付租文案）" />
				</div>
				<div class="tpl-item">
					<div class="tpl-label">默认到期提醒模板</div>
					<el-input v-model="tplDraft.maturity" type="textarea" :rows="7" class="tpl-ta" placeholder="留空 = 使用系统内置默认（泰/英双语到期文案）" />
				</div>
			</div>
			<div class="tpl-vars">可用变量：<code>{name}</code> 房名 · <code>{rent}</code> 租金 · <code>{date}</code> 起租日 · <code>{rent_end}</code> 结束日 · <code>{sign}</code> 落款签名（租户自定义 &gt; 公司名 &gt; 全局）</div>
			<div class="tpl-actions">
				<el-button class="tpl-reset" @click="resetTemplates">恢复内置默认</el-button>
				<el-button class="tpl-save" :loading="savingTpl" @click="saveTemplates">保存模板</el-button>
			</div>
			<div class="env-hint">保存后立即生效（定时任务 / 工作台「立即发送」共用）。空内容保存 = 恢复内置默认；已配置「房源自定义消息」的仍以房源自定义优先。</div>
		</div>

		<!-- 环境配置概览 -->
		<div v-if="envGroups.length" class="panel">
			<div class="panel-title">环境配置 (.env)</div>
			<div class="env-groups">
				<div v-for="g in envGroups" :key="g.group" class="env-group">
					<div class="env-group-title">{{ g.group }}</div>
					<div class="env-items">
						<div v-for="item in g.items" :key="item.key" class="env-row">
							<span class="env-label" :title="item.key">{{ item.label }}</span>
							<span class="env-value">{{ item.value === '' ? '（空）' : item.value }}</span>
						</div>
					</div>
				</div>
			</div>
			<div class="env-hint">以上为 conf/env.py 配置(密钥已脱敏)。改动需重启后端生效。</div>
		</div>

		<!-- AI 助手模型配置 -->
		<div class="panel">
			<div class="panel-title">AI 助手模型</div>
			<div class="ai-cfg-row">
				<div class="ai-cfg-info">
					<div class="ai-cfg-title">房源一句话添加（AI 解析→预览确认）</div>
					<div class="ai-cfg-sub">当前模型 <b class="ai-model">{{ aiCfg.model || '—' }}</b> · 服务 <span class="ai-base">{{ aiCfg.base || '—' }}</span></div>
				</div>
				<div class="ai-cfg-ctrl">
					<el-input v-model="aiDraft.base" class="ai-inp" placeholder="API Base，如 https://integrate.api.nvidia.com/v1" />
					<el-input v-model="aiDraft.model" class="ai-inp" placeholder="模型名，如 deepseek-ai/deepseek-v4-flash-0731" />
					<el-input v-model="aiDraft.api_key" class="ai-inp key" placeholder="API Key（已保存时留空 = 不修改）" show-password />
					<el-button class="sched-save" :loading="savingAI" @click="saveAIConfig">保存</el-button>
				</div>
				<div v-if="aiDraft.warn" class="ai-warn">新 Key 已保存（仅展示时打码，不影响使用）</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts" name="adminDashboard">
import { ref, onMounted, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { getDashboardStat, getEnvConfig, getNotifySchedule, updateNotifySchedule, getAIConfig, updateAIConfig, updateNotifyMessageTemplates } from './api';

const stat = ref<any>({});
const envGroups = ref<any[]>([]);
const sched = ref<any>({ hour: null, minute: 0, source: 'env', env_default: 9, tz: 'Asia/Bangkok', dedup: false });
const savingSched = ref(false);
const tplDraft = ref<any>({ rent: '', maturity: '' });
const savingTpl = ref(false);

const cards = computed(() => [
	{ label: '租户总数', value: stat.value.tenant_total ?? '-', icon: 'ele-OfficeBuilding', color: '#409eff' },
	{ label: '启用中', value: stat.value.tenant_active ?? '-', icon: 'ele-CircleCheck', color: '#67c23a' },
	{ label: '试用客户', value: stat.value.tenant_trial ?? '-', icon: 'ele-AlarmClock', color: '#e6a23c' },
	{ label: '正式客户', value: stat.value.tenant_paid ?? '-', icon: 'ele-Medal', color: '#a5a8ae' },
	{ label: 'LineBot 总数', value: stat.value.bot_total ?? '-', icon: 'ele-ChatDotRound', color: '#409eff' },
	{ label: '启用 Bot', value: stat.value.bot_active ?? '-', icon: 'ele-Switch', color: '#67c23a' },
	{ label: '本月消息量', value: stat.value.msg_total ?? '-', icon: 'ele-Send', color: '#e6a23c' },
]);

onMounted(async () => {
	try {
		const [statRes, envRes, schedRes] = await Promise.all([
			getDashboardStat(),
			getEnvConfig(),
			getNotifySchedule(),
		]);
		stat.value = statRes.data || {};
		envGroups.value = envRes.data || [];
		if (schedRes.data) {
			sched.value = { ...sched.value, ...schedRes.data };
			tplDraft.value.rent = schedRes.data.rent_template || '';
			tplDraft.value.maturity = schedRes.data.maturity_template || '';
		}
	} catch (e) {
		console.error('dashboard load failed', e);
	}
	try {
		const aiRes: any = await getAIConfig();
		if (aiRes.code === 2000 && aiRes.data) {
			aiCfg.value = { ...aiCfg.value, ...aiRes.data };
			aiDraft.value.base = aiRes.data.base || '';
			aiDraft.value.model = aiRes.data.model || '';
		}
	} catch (e) {
		console.error('ai config load failed', e);
	}
});

// AI 助手模型配置
const aiCfg = ref<any>({ base: '', model: '', api_key: '', has_key: false });
const aiDraft = ref<any>({ base: '', model: '', api_key: '', warn: '' });
const savingAI = ref(false);
const saveAIConfig = async () => {
	if (savingAI.value) return;
	savingAI.value = true;
	try {
		const res: any = await updateAIConfig({
			base: aiDraft.value.base,
			model: aiDraft.value.model,
			api_key: aiDraft.value.api_key,
		});
		if (res.code === 2000 && res.data) {
			aiCfg.value = { ...aiCfg.value, ...res.data };
			const keyWasProvided = !!aiDraft.value.api_key && !aiDraft.value.api_key.includes('*');
			aiDraft.value.warn = keyWasProvided ? '已保存新 Key（回显仅打码）' : '';
			if (!keyWasProvided) aiDraft.value.warn = '已保存';
			aiDraft.value.api_key = '';
			ElMessage.success('AI 配置已保存并生效');
		} else {
			ElMessage.warning(res.msg || '保存失败');
		}
	} catch (e) {
		ElMessage.error('保存失败');
	} finally {
		savingAI.value = false;
	}
};

const saveSched = async () => {
	if (savingSched.value || sched.value.hour === null || sched.value.hour === undefined) return;
	savingSched.value = true;
	try {
		const res: any = await updateNotifySchedule(sched.value.hour, sched.value.minute || 0, sched.value.dedup);
		if (res.code === 2000 && res.data?.ok) {
			ElMessage.success(res.msg || '已保存并生效');
			sched.value.source = 'db';
			sched.value.hour = res.data.hour;
			sched.value.minute = res.data.minute;
			if (typeof res.data.dedup === 'boolean') sched.value.dedup = res.data.dedup;
		} else {
			ElMessage.warning(res.msg || res.data?.error || '保存失败');
		}
	} catch (e) {
		ElMessage.error('保存失败');
	} finally {
		savingSched.value = false;
	}
};

const resetTemplates = () => {
	tplDraft.value.rent = '';
	tplDraft.value.maturity = '';
};

const saveTemplates = async () => {
	if (savingTpl.value) return;
	savingTpl.value = true;
	try {
		const res: any = await updateNotifyMessageTemplates(tplDraft.value.rent, tplDraft.value.maturity);
		if (res.code === 2000 && res.data?.ok) {
			ElMessage.success(res.msg || '消息模板已保存并生效');
		} else {
			ElMessage.warning(res.msg || res.data?.error || '保存失败');
		}
	} catch (e) {
		ElMessage.error('保存失败');
	} finally {
		savingTpl.value = false;
	}
};

const fmtSched = (v: any) => (v === null || v === undefined ? '00' : String(v).padStart(2, '0'));
</script>

<style scoped lang="scss">
.dashboard {
	--cn-muted: #b1b4b8;
	--cn-border: #2a2a2a;
	--cn-text: #eaeaea;
	display: flex;
	flex-direction: column;
	gap: 32px;
	padding: 8px 4px 16px;
}

.stat-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
	gap: 20px;
}

.stat-card {
	background: #1a1a1c;
	border: 1px solid var(--cn-border);
	border-radius: 14px;
	padding: 24px;
	display: flex;
	align-items: center;
	gap: 18px;
	transition: border-color 0.2s ease;

	&:hover {
		border-color: #333333;
	}

	.stat-icon {
		width: 52px;
		height: 52px;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #fff;
		font-size: 24px;
		flex-shrink: 0;
	}

	.stat-body {
		.stat-value {
			font-size: 30px;
			font-weight: 600;
			color: var(--cn-text);
			line-height: 1.1;
		}

		.stat-label {
			font-size: 14px;
			color: var(--cn-muted);
			margin-top: 8px;
		}
	}
}

.panel {
	background: #1a1a1c;
	border: 1px solid var(--cn-border);
	border-radius: 14px;
	padding: 28px;

	.panel-title {
		font-size: 16px;
		font-weight: 600;
		color: var(--cn-text);
		margin-bottom: 22px;
		padding-bottom: 14px;
		border-bottom: 1px solid var(--cn-border);
	}

	/* 环境配置概览 */
	.env-groups {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 32px;
	}

	.env-group {
		.env-group-title {
			font-size: 14px;
			font-weight: 600;
			color: #9ec9ff;
			margin-bottom: 16px;
			padding-bottom: 10px;
			border-bottom: 1px solid var(--cn-border);
		}

		.env-items {
			display: flex;
			flex-direction: column;
			gap: 14px;

			.env-row {
				display: flex;
				justify-content: space-between;
				align-items: center;
				gap: 16px;
				font-size: 14px;

				.env-label {
					color: var(--cn-muted);
					flex-shrink: 0;
				}

				.env-value {
					color: var(--cn-text);
					text-align: right;
					word-break: break-all;
					max-width: 70%;
					font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
				}
			}
		}
	}

	.env-hint {
		margin-top: 24px;
		padding-top: 16px;
		border-top: 1px solid var(--cn-border);
		font-size: 12px;
		color: var(--cn-muted);
	}
}

.sched-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	flex-wrap: wrap;

	.sched-info {
		.sched-cur {
			font-size: 15px;
			color: var(--cn-text);
			.sched-hour {
				font-family: monospace;
				font-size: 18px;
				color: #9ec9ff;
			}
			.el-tag { margin-left: 8px; vertical-align: 2px; }
		}
		.sched-sub {
			margin-top: 6px;
			font-size: 12px;
			color: var(--cn-muted);
		}
	}

	.sched-ctrl {
		display: flex;
		align-items: center;
		gap: 10px;

		.sched-save {
			background: rgba(64, 158, 255, 0.2);
			border-color: rgba(64, 158, 255, 0.35);
			color: #9ec9ff;
			&:hover, &:focus {
				background: rgba(64, 158, 255, 0.3);
				border-color: rgba(64, 158, 255, 0.5);
				color: #bcd9ff;
			}
		}
	}
}

.dedup-row {
	display: flex;
	align-items: center;
	gap: 14px;
	margin-top: 18px;
	padding-top: 16px;
	border-top: 1px dashed var(--cn-border);

	.dedup-info {
		.dedup-title {
			font-size: 13px;
			color: var(--cn-text);
		}
		.dedup-sub {
			margin-top: 4px;
			font-size: 12px;
			color: var(--cn-muted);
			em { color: #e6a23c; font-style: normal; }
		}
	}
}

.tpl-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
	gap: 20px;

	.tpl-item {
		.tpl-label {
			font-size: 13px;
			color: var(--cn-text);
			margin-bottom: 10px;
		}

		.tpl-ta {
			:deep(.el-textarea__inner) {
				background: #212121;
				border-color: var(--cn-border);
				color: var(--cn-text);
				font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
				font-size: 13px;
				line-height: 1.6;
				border-radius: 10px;
				&:hover, &:focus {
					border-color: rgba(64, 158, 255, 0.5);
				}
			}
		}
	}
}

.tpl-vars {
	margin-top: 14px;
	font-size: 12px;
	color: var(--cn-muted);
	line-height: 1.8;

	code {
		background: #212121;
		border: 1px solid var(--cn-border);
		border-radius: 6px;
		padding: 1px 6px;
		color: #9ec9ff;
		font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
	}
}

.tpl-actions {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
	margin-top: 16px;

	.tpl-reset {
		background: #212121;
		border-color: #333;
		color: #9b9da1;
		&:hover, &:focus {
			background: #2a2a2a;
			border-color: #444;
			color: #d6d8dc;
		}
	}

	.tpl-save {
		background: rgba(64, 158, 255, 0.2);
		border-color: rgba(64, 158, 255, 0.35);
		color: #9ec9ff;
		&:hover, &:focus {
			background: rgba(64, 158, 255, 0.3);
			border-color: rgba(64, 158, 255, 0.5);
			color: #bcd9ff;
		}
	}
}

.ai-cfg-row {
	display: flex;
	flex-direction: column;
	gap: 14px;

	.ai-cfg-info {
		.ai-cfg-title { font-size: 14px; color: var(--cn-text); }
		.ai-cfg-sub { margin-top: 5px; font-size: 12px; color: var(--cn-muted);
			.ai-model { color: #b0a3ff; font-family: monospace; }
			.ai-base { color: #9ec9ff; font-family: monospace; word-break: break-all; }
		}
	}

	.ai-cfg-ctrl {
		display: flex;
		gap: 10px;
		flex-wrap: wrap;
		.ai-inp { width: 320px; }
		.ai-inp.key { width: 260px; }
		.sched-save {
			background: rgba(124, 93, 250, .2);
			border-color: rgba(124, 93, 250, .5);
			color: #b0a3ff;
			&:hover, &:focus { background: rgba(124, 93, 250, .32); color: #cdc1ff; }
		}
	}

	.ai-warn { font-size: 12px; color: #95d475; }
}
</style>
