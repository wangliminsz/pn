<template>
	<div class="sa-page">
		<!-- 顶部: 说明 + 新增 -->
		<div class="page-head">
			<div class="head-left">
				<span class="head-title">Superadmin</span>
				<span class="head-sub">仅超级管理员可见。用于给同事开通管理账号，新账号首次登录需改密。</span>
			</div>
			<el-button type="primary" @click="openAdd">
				<el-icon style="margin-right:4px"><ele-Plus /></el-icon>新增
			</el-button>
		</div>

		<!-- 列表 -->
		<div class="sa-list">
			<div v-for="row in list" :key="row.id" class="sa-card">
				<div class="card-head">
					<div class="card-name">
						{{ row.name || row.username }}
						<span v-if="row.id === currentUserId" class="me-tag">当前账号</span>
						<span v-if="row.pwd_change_count === 0" class="need-change">首登需改密</span>
					</div>
					<div class="card-right">
						<el-tag :type="row.is_active ? 'success' : 'danger'" size="small" effect="plain">
							{{ row.is_active ? '已启用' : '已停用' }}
						</el-tag>
<el-button v-if="row.id !== currentUserId" class="soft-gray" size="small"
						:loading="togglingId === row.id" @click="toggle(row)">
							{{ row.is_active ? '停用' : '启用' }}
						</el-button>
						<el-button v-if="row.id !== currentUserId" class="soft-gray" size="small" @click="openResetPwd(row)">重置密码</el-button>
					</div>
				</div>
				<div class="card-rows">
					<div class="row"><span class="k">登录账号</span><span class="v">{{ row.username }}</span></div>
					<div class="row"><span class="k">邮箱</span><span class="v">{{ row.email || '-' }}</span></div>
					<div class="row"><span class="k">手机</span><span class="v">{{ row.mobile || '-' }}</span></div>
					<div class="row"><span class="k">最近登录</span><span class="v">{{ row.last_login || '-' }}</span></div>
					<div class="row"><span class="k">创建时间</span><span class="v">{{ row.create_datetime || '-' }}</span></div>
				</div>
			</div>
			<div v-if="!list.length && !loading" class="empty">暂无 Superadmin 账号</div>
		</div>

		<!-- 账号解锁(跨租户搜索任意用户, 含自助注册用户) -->
		<div class="sa-card unlock-card">
			<div class="card-head">
				<div class="head-left">
					<span class="head-title">账号解锁</span>
					<span class="head-sub">按邮箱/用户名搜索任意账号（含自助注册用户），解锁被锁或未激活的账号。</span>
				</div>
			</div>
			<div class="unlock-search">
				<el-input v-model="unlockQuery" placeholder="输入邮箱或用户名，如 someone@example.com" clearable
					@keyup.enter="searchUnlock" class="unlock-input" />
				<el-button type="primary" :loading="unlockSearching" @click="searchUnlock">搜索</el-button>
			</div>
			<div v-if="unlockResults.length" class="unlock-results">
				<div v-for="u in unlockResults" :key="u.id" class="unlock-row">
					<div class="ur-left">
						<span class="ur-name">{{ u.name || u.username }}</span>
						<span class="ur-mail">{{ u.email || u.username }}</span>
						<span v-if="!u.is_active" class="ur-lock">已停用/未激活</span>
						<span v-else-if="u.is_locked" class="ur-lock">临时锁定中(至 {{ u.login_locked_until }})</span>
						<el-tag v-if="u.tenant_code" size="small" effect="plain">租户 {{ u.tenant_code }}</el-tag>
					</div>
					<div class="ur-right">
						<el-tag :type="u.is_active ? 'success' : 'danger'" size="small" effect="plain">
							{{ u.is_active ? '已启用' : '已停用' }}
						</el-tag>
						<el-button v-if="!u.is_active || u.is_locked" class="soft-gray" size="small"
							:loading="unlockingId === u.id" @click="doUnlock(u)">解锁</el-button>
					</div>
				</div>
			</div>
			<div v-else-if="unlockSearched && !unlockSearching" class="unlock-empty">未找到匹配账号</div>
		</div>

		<!-- 登录安全设置(写入 system_config: login.*, 全租户生效) -->
		<div class="sa-card unlock-card">
			<div class="card-head">
				<div class="head-left">
					<span class="head-title">登录安全设置</span>
					<span class="head-sub">账号连续输错达到阈值后临时锁定，另有 IP 级限流。保存后立即生效。</span>
				</div>
			</div>
			<div class="setting-grid">
				<div v-for="s in settingsMeta" :key="s.key" class="setting-item">
					<span class="s-label">{{ s.title }}</span>
					<el-input-number v-model="settings[s.key]" :min="1" :max="86400" controls-position="right"
						style="width: 180px" />
				</div>
			</div>
			<div class="set-actions">
				<el-button type="primary" :loading="savingSettings" @click="saveSettings">保存</el-button>
				<el-button @click="loadSettings">撤销</el-button>
			</div>
		</div>

		<!-- 自助注册模式(是否需要付费后建租户) -->
		<div class="sa-card unlock-card">
			<div class="card-head">
				<div class="head-left">
					<span class="head-title">自助注册模式</span>
					<span class="head-sub">关闭「需付费开通」后，新用户验证邮箱即可直接开通租户，无需走 PromptPay。</span>
				</div>
			</div>
			<div class="signup-mode-row">
				<div class="sm-left">
					<span class="sm-label">需付费开通</span>
					<span class="sm-desc">{{ signupRequirePayment ? '开启：注册→验证→PromptPay 付费→建租户' : '关闭：注册→验证→直接创建租户' }}</span>
				</div>
				<div class="sm-right">
					<el-switch v-model="signupRequirePayment" :loading="savingSignupMode" />
					<el-button type="primary" size="small" :loading="savingSignupMode" @click="saveSignupMode">保存</el-button>
				</div>
			</div>
		</div>

		<!-- 默认密码设置(新建账号默认密码, 含批量导入/超管新增) -->
		<div class="sa-card unlock-card">
			<div class="card-head">
				<div class="head-left">
					<span class="head-title">默认密码设置</span>
					<span class="head-sub">新建账号（含组织架构批量导入、新增超管）的初始默认密码。保存后立即生效，前端会同步显示。</span>
				</div>
			</div>
			<div class="signup-mode-row">
				<div class="sm-left">
					<span class="sm-label">默认密码</span>
					<span class="sm-desc">至少 8 位，含字母和数字；首次登录需修改。</span>
				</div>
				<div class="sm-right">
					<el-input v-model="defaultPassword" type="password" show-password clearable
						placeholder="≥8 位，含字母和数字" style="width: 240px" />
					<el-button type="primary" size="small" :loading="savingDefaultPassword" @click="saveDefaultPassword">保存</el-button>
				</div>
			</div>
		</div>

		<!-- 新增弹窗 -->
		<el-dialog v-model="dialogVisible" title="新增" width="460px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
			<el-form ref="formRef" :model="form" :rules="rules" label-width="90px" label-position="left">
				<el-form-item label="登录账号" prop="username">
					<el-input v-model="form.username" placeholder="建议用邮箱，如 hkex2025@gmail.com" />
				</el-form-item>
				<el-form-item label="姓名">
					<el-input v-model="form.name" placeholder="显示姓名" />
				</el-form-item>
				<el-form-item label="初始密码" prop="password">
					<el-input v-model="form.password" type="password" show-password clearable
						placeholder="≥8 位，含字母和数字；首次登录需修改" />
				</el-form-item>
				<el-form-item label="确认密码" prop="password2">
					<el-input v-model="form.password2" type="password" show-password clearable placeholder="再次输入初始密码" />
				</el-form-item>
				<div class="form-tip">新账号默认「首登需改密码」</div>
			</el-form>
			<template #footer>
				<div class="footer-spacer"></div>
				<el-button type="primary" :loading="saving" @click="save">保存</el-button>
				<el-button @click="dialogVisible = false">取消</el-button>
			</template>
		</el-dialog>

		<!-- 重置密码弹窗 -->
		<el-dialog v-model="resetVisible" :title="'重置密码 · ' + (resetRow?.name || resetRow?.username || '')" width="460px"
			destroy-on-close :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
			<el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="90px" label-position="left">
				<el-form-item label="新密码" prop="password">
					<el-input v-model="resetForm.password" type="password" show-password clearable placeholder="≥8 位，含字母和数字" />
				</el-form-item>
				<el-form-item label="确认密码" prop="password2">
					<el-input v-model="resetForm.password2" type="password" show-password clearable placeholder="再次输入新密码" />
				</el-form-item>
				<el-form-item label="首登改密">
					<el-switch v-model="resetForm.force_change" />
					<span class="tip">开启后对方下次登录必须先改密码（推荐）</span>
				</el-form-item>
			</el-form>
			<template #footer>
				<div class="footer-spacer"></div>
				<el-button type="primary" :loading="resetting" @click="confirmReset">确认重置</el-button>
				<el-button @click="resetVisible = false">取消</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script lang="ts" setup name="adminSuperadmin">
import { ref, reactive, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
import { GetList, Create, ToggleActive, ResetPassword, LookupUsers, UnlockUser, GetLoginSettings, SaveLoginSettings, GetSignupSettings, SaveSignupSettings, GetDefaultPassword, SaveDefaultPassword } from './api';

const { userInfos } = storeToRefs(useUserInfo());
const currentUserId = userInfos.value.id as number | undefined;

const list = ref<any[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const saving = ref(false);
const togglingId = ref<number | null>(null);
const formRef = ref<any>();
const form = reactive<any>({ username: '', name: '', password: '', password2: '' });

const pwdRegex = /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/;
const rules = {
	username: [{ required: true, message: '请输入登录账号', trigger: 'blur' }],
	password: [
		{ required: true, message: '请输入初始密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (!pwdRegex.test(value || '')) {
				cb(new Error('密码需 ≥8 位且含字母和数字'));
			} else cb();
		}, trigger: 'blur' },
	],
	password2: [
		{ required: true, message: '请再输入一次密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (value !== form.password) cb(new Error('两次输入的密码不一致'));
			else cb();
		}, trigger: 'blur' },
	],
};

const load = async () => {
	loading.value = true;
	try {
		const res: any = await GetList({ page: 1, limit: 100 });
		list.value = res.data || [];
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
};

const openAdd = () => {
	form.username = '';
	form.name = '';
	form.password = '';
	form.password2 = '';
	dialogVisible.value = true;
};

const save = () => {
	formRef.value.validate((valid: boolean) => {
		if (!valid) return;
		saving.value = true;
		Create({ username: form.username, name: form.name, password: form.password })
			.then((res: any) => {
				if (res.code === 2000) {
					ElMessage.success('超管已创建，首次登录需改密');
					dialogVisible.value = false;
					load();
				} else {
					ElMessage.error(res.msg || '创建失败');
				}
			})
			.finally(() => {
				saving.value = false;
			});
	});
};

// ---------------- 重置密码 ----------------
const resetVisible = ref(false);
const resetting = ref(false);
const resetRow = ref<any>(null);
const resetFormRef = ref<any>();
const resetForm = reactive<any>({ password: '', password2: '', force_change: true });
const resetRules = {
	password: [
		{ required: true, message: '请输入新密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (!pwdRegex.test(value || '')) cb(new Error('密码需 ≥8 位且含字母和数字'));
			else cb();
		}, trigger: 'blur' },
	],
	password2: [
		{ required: true, message: '请再输入一次密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (value !== resetForm.password) cb(new Error('两次输入的密码不一致'));
			else cb();
		}, trigger: 'blur' },
	],
};

const openResetPwd = (row: any) => {
	resetRow.value = row;
	resetForm.password = '';
	resetForm.password2 = '';
	resetForm.force_change = true;
	resetVisible.value = true;
};

const confirmReset = () => {
	resetFormRef.value.validate((valid: boolean) => {
		if (!valid) return;
		resetting.value = true;
		ResetPassword(resetRow.value.id, { password: resetForm.password, force_change: resetForm.force_change })
			.then((res: any) => {
				if (res.code === 2000) {
					ElMessage.success(res.msg || '密码已重置');
					resetVisible.value = false;
					load();
				} else {
					ElMessage.error(res.msg || '重置失败');
				}
			})
			.finally(() => {
				resetting.value = false;
			});
	});
};

const toggle = async (row: any) => {
	const nextActive = !row.is_active;
	const action = nextActive ? '启用' : '停用';
	await ElMessageBox.confirm(`确认${action}超管账号「${row.username}」？`, '确认操作', {
		type: 'warning',
		confirmButtonText: `确认${action}`,
		cancelButtonText: '取消',
	});
	togglingId.value = row.id;
	try {
		const res: any = await ToggleActive(row.id, nextActive);
		if (res.code === 2000) {
			ElMessage.success(res.msg || `${action}成功`);
			load();
		} else {
			ElMessage.error(res.msg || '操作失败');
		}
	} finally {
		togglingId.value = null;
	}
};

// ---------------- 账号解锁 ----------------
const unlockQuery = ref('');
const unlockResults = ref<any[]>([]);
const unlockSearching = ref(false);
const unlockSearched = ref(false);
const unlockingId = ref<number | null>(null);

const searchUnlock = async () => {
	const q = unlockQuery.value.trim();
	if (!q) {
		ElMessage.warning('请输入邮箱或用户名');
		return;
	}
	unlockSearching.value = true;
	try {
		const res: any = await LookupUsers(q);
		unlockResults.value = res.data || [];
		unlockSearched.value = true;
	} catch (e) {
		console.error(e);
	} finally {
		unlockSearching.value = false;
	}
};

const doUnlock = async (u: any) => {
	await ElMessageBox.confirm(`确认解锁账号「${u.username}」？解锁后将恢复登录权限。`, '确认操作', {
		type: 'warning',
		confirmButtonText: '确认解锁',
		cancelButtonText: '取消',
	});
	unlockingId.value = u.id;
	try {
		const res: any = await UnlockUser({ email: u.username });
		if (res.code === 2000) {
			ElMessage.success(res.msg || '账号已解锁');
			searchUnlock();
		} else {
			ElMessage.error(res.msg || '操作失败');
		}
	} finally {
		unlockingId.value = null;
	}
};

// ---------------- 登录安全设置 ----------------
const settings = ref<any>({});
const settingsMeta = ref<any[]>([]);
const savingSettings = ref(false);

const loadSettings = async () => {
	try {
		const res: any = await GetLoginSettings();
		settings.value = res.data?.values || {};
		settingsMeta.value = Object.entries(res.data?.meta || {}).map(([k, v]: any) => ({
			key: k,
			title: v.title || k,
		}));
	} catch (e) {
		console.error(e);
	}
};

const saveSettings = async () => {
	savingSettings.value = true;
	try {
		const res: any = await SaveLoginSettings(settings.value);
		if (res.code === 2000) {
			ElMessage.success(res.msg || '已保存');
			settings.value = res.data?.values || settings.value;
		} else {
			ElMessage.error(res.msg || '保存失败');
		}
	} catch (e) {
		console.error(e);
	} finally {
		savingSettings.value = false;
	}
};

// ---------------- 自助注册模式 ----------------
const signupRequirePayment = ref(true);
const savingSignupMode = ref(false);

const loadSignupMode = async () => {
	try {
		const res: any = await GetSignupSettings();
		signupRequirePayment.value = res.data?.require_payment !== false;
	} catch (e) {
		console.error(e);
	}
};

const saveSignupMode = async () => {
	savingSignupMode.value = true;
	try {
		const res: any = await SaveSignupSettings({ require_payment: signupRequirePayment.value });
		if (res.code === 2000) {
			ElMessage.success(res.msg || '已保存');
			loadSignupMode();
		} else {
			ElMessage.error(res.msg || '保存失败');
		}
	} catch (e) {
		console.error(e);
	} finally {
		savingSignupMode.value = false;
	}
};

// ---------------- 默认密码设置 ----------------
const defaultPassword = ref('');
const savingDefaultPassword = ref(false);

const loadDefaultPassword = async () => {
	try {
		const res: any = await GetDefaultPassword();
		defaultPassword.value = res.data?.default_password || '';
	} catch (e) {
		console.error(e);
	}
};

const saveDefaultPassword = async () => {
	const pw = (defaultPassword.value || '').trim();
	if (!pw) {
		ElMessage.warning('请输入默认密码');
		return;
	}
	if (!/^(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}$/.test(pw)) {
		ElMessage.warning('密码至少 8 位，且须同时包含字母和数字');
		return;
	}
	savingDefaultPassword.value = true;
	try {
		const res: any = await SaveDefaultPassword({ default_password: pw });
		if (res.code === 2000) {
			ElMessage.success(res.msg || '已保存');
			loadDefaultPassword();
		} else {
			ElMessage.error(res.msg || '保存失败');
		}
	} catch (e) {
		console.error(e);
	} finally {
		savingDefaultPassword.value = false;
	}
};

onMounted(() => {
	load();
	loadSettings();
	loadSignupMode();
	loadDefaultPassword();
});
</script>

<style scoped lang="scss">
.sa-page {
	--cn-muted: #b1b4b8;
	--cn-border: #2a2a2a;
	--cn-text: #eaeaea;
	display: flex;
	flex-direction: column;
	gap: 24px;
}

.page-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;

	.head-left {
		display: flex;
		flex-direction: column;
		gap: 8px;

		.head-title {
			font-size: 17px;
			font-weight: 600;
			color: var(--cn-text);
		}

		.head-sub {
			font-size: 13px;
			color: var(--cn-muted);
		}
	}
}

.sa-list {
	display: flex;
	flex-direction: column;
	gap: 18px;
}

.sa-card {
	background: #1a1a1c;
	border: 1px solid var(--cn-border);
	border-radius: 14px;
	padding: 26px 30px;
	display: flex;
	flex-direction: column;
	gap: 22px;

	.card-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
	}

	.card-name {
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: 16px;
		font-weight: 600;
		color: var(--cn-text);

		.me-tag {
			font-size: 11px;
			color: #409eff;
			background: rgba(64, 158, 255, 0.12);
			border: 1px solid rgba(64, 158, 255, 0.4);
			border-radius: 4px;
			padding: 1px 8px;
		}

		.need-change {
			font-size: 11px;
			color: #e6a23c;
			background: rgba(230, 162, 60, 0.12);
			border: 1px solid rgba(230, 162, 60, 0.4);
			border-radius: 4px;
			padding: 1px 8px;
		}
	}

	.card-right {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 10px;
		flex-shrink: 0;
	}

	.card-rows {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px 48px;

		.row {
			display: flex;
			justify-content: space-between;
			align-items: center;
			font-size: 14px;
			padding-bottom: 14px;
			border-bottom: 1px dashed rgba(255, 255, 255, 0.06);

			.k {
				color: var(--cn-muted);
			}

			.v {
				color: var(--cn-text);
				text-align: right;
				word-break: break-all;
			}
		}
	}
}

.empty {
	text-align: center;
	color: #b1b4b8;
	padding: 80px 0;
}

.unlock-search {
	display: flex;
	gap: 10px;

	.unlock-input {
		flex: 1;
		max-width: 420px;
	}
}

.unlock-results {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.unlock-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 14px 16px;
	background: rgba(255, 255, 255, 0.03);
	border: 1px solid rgba(255, 255, 255, 0.07);
	border-radius: 10px;

	.ur-left {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-wrap: wrap;
		min-width: 0;

		.ur-name {
			color: var(--cn-text);
			font-weight: 600;
		}

		.ur-mail {
			color: var(--cn-muted);
			font-size: 13px;
			word-break: break-all;
		}

		.ur-lock {
			font-size: 12px;
			color: #f56c6c;
		}
	}

	.ur-right {
		display: flex;
		align-items: center;
		gap: 10px;
		flex-shrink: 0;
	}
}

.unlock-empty {
	text-align: center;
	color: #b1b4b8;
	padding: 30px 0;
	font-size: 13px;
}

.setting-grid {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
	gap: 14px 32px;

	.setting-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 10px 14px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.07);
		border-radius: 10px;

		.s-label {
			color: var(--cn-text);
			font-size: 13px;
		}
	}
}

.set-actions {
	display: flex;
	justify-content: flex-end;
	gap: 10px;
}

.signup-mode-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;

	.sm-left {
		display: flex;
		flex-direction: column;
		gap: 4px;

		.sm-label {
			color: var(--cn-text);
			font-size: 14px;
			font-weight: 600;
		}

		.sm-desc {
			color: var(--cn-muted);
			font-size: 12px;
		}
	}

	.sm-right {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-shrink: 0;
	}
}

.form-tip {
	width: 100%;
	font-size: 12px;
	line-height: 1.5;
	color: var(--cn-muted);
}

.footer-spacer {
	flex: 1;
}

:deep(.el-dialog__footer) {
	display: flex;
	align-items: center;
	gap: 8px;
}

/* Simple Better: 校验时只显示红边框, 不显示红色提示文字 */
:deep(.el-form-item__error) {
	display: none !important;
}

/* 柔和灰色按钮(启用/停用): 状态tag区分主次, 操作按钮低调灰 so用户不会误会成状态 */
.soft-gray {
	background: rgba(120, 124, 130, 0.12) !important;
	border-color: rgba(120, 124, 130, 0.5) !important;
	color: #9ba1a6 !important;

	&:hover,
	&:focus {
		background: rgba(120, 124, 130, 0.22) !important;
		border-color: rgba(120, 124, 130, 0.7) !important;
		color: #c0c4cc !important;
	}
}
</style>
