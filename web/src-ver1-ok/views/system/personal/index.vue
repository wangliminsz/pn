<template>
	<div class="personal-page">
		<div class="page-head">
			<span class="title">{{ $t('message.pages.personal.page.title') }}</span>
			<!-- <span class="sub">管理你的账户资料与登录安全</span> -->
		</div>

		<div class="cols">
			<!-- 基本信息 -->
			<div class="col profile-col">

				<div class="flex justify-between">
					<div class="col-head">
						<span>{{ $t('message.pages.personal.page.basicInfo') }}</span>
					</div>

					 <!-- class="form-button-section" -->
					<div>
						<template v-if="!isEditing">
							<el-button type="primary" @click="isEditing = true">{{ $t('message.pages.personal.page.updateInfo') }}</el-button>
						</template>
						<template v-else>
							<el-button type="primary" :loading="saving" @click="submitForm">{{ $t('message.pages.personal.page.submit') }}</el-button>
							<el-button @click="isEditing = false">{{ $t('message.pages.personal.page.cancel') }}</el-button>
						</template>
					</div>

				</div>



				<div class="profile-main">
					<div class="welcome">
						<div class="hello">{{ currentTime }}{{ $t('message.pages.personal.page.greetingComma') }}{{ state.personalForm.name || state.personalForm.username }}</div>
						<div class="acc">@{{ state.personalForm.username }}</div>
						<div class="role-tags">
							<el-tag v-for="(item, index) in state.personalForm.role_info" :key="index" size="small" effect="plain">{{ item.name }}</el-tag>
						</div>
					</div>


				</div>

				<el-form ref="userInfoFormRef" :model="state.personalForm" :rules="rules" label-width="110px" label-position="left"
					class="personal-form">
					<el-form-item :label="$t('message.pages.personal.form.nickname')" prop="name">
						<el-input v-model="state.personalForm.name" :placeholder="$t('message.pages.personal.form.nicknamePlaceholder')"
							clearable :disabled="!isEditing" />
					</el-form-item>
					<el-form-item :label="$t('message.pages.personal.form.email')" prop="email">
						<el-input v-model="state.personalForm.email" :placeholder="$t('message.pages.personal.form.emailPlaceholder')"
							clearable :disabled="!isEditing" />
					</el-form-item>
					<el-form-item :label="$t('message.pages.personal.form.mobile')" prop="mobile">
						<el-input v-model="state.personalForm.mobile" :placeholder="$t('message.pages.personal.form.mobilePlaceholder')"
							clearable :disabled="!isEditing" />
					</el-form-item>
					<el-form-item :label="$t('message.pages.personal.form.gender')" prop="gender">
						<el-select v-model="state.personalForm.gender" :placeholder="$t('message.pages.personal.form.genderPlaceholder')"
							clearable :disabled="!isEditing" style="width: 100%">
							<el-option v-for="(item, index) in translatedGenderList" :key="index" :label="item.label" :value="item.value" />
						</el-select>
					</el-form-item>
					<el-form-item :label="$t('message.pages.personal.info.company')">
						<el-tag class="dept-tag" effect="plain">{{ state.personalForm.tenant_name || '—' }}</el-tag>
					</el-form-item>
					<el-form-item :label="$t('message.pages.personal.info.department')">
						<el-tag class="dept-tag" effect="plain">{{ state.personalForm.dept_info.dept_name || '—' }}</el-tag>
					</el-form-item>
				</el-form>

				
			</div>
		</div>

		<!-- 密码修改 -->
		<el-dialog v-model="passwordFormShow" :title="$t('message.pages.personal.dialog.passwordChange')" width="520px" destroy-on-close
			:close-on-click-modal="false" :close-on-press-escape="false">
			<el-form ref="userPasswordFormRef" :model="userPasswordInfo" label-width="150px" label-position="left" :rules="passwordRules">
				<el-form-item :label="$t('message.pages.personal.dialog.oldPassword')" prop="oldPassword">
					<el-input type="password" v-model="userPasswordInfo.oldPassword"
						:placeholder="$t('message.pages.personal.dialog.oldPasswordPlaceholder')" show-password clearable />
				</el-form-item>
				<el-form-item :label="$t('message.pages.personal.dialog.newPassword')" prop="newPassword">
					<el-input type="password" v-model="userPasswordInfo.newPassword"
						:placeholder="$t('message.pages.personal.dialog.newPasswordPlaceholder')" show-password clearable />
				</el-form-item>
				<el-form-item :label="$t('message.pages.personal.dialog.confirmPassword')" prop="newPassword2">
					<el-input type="password" v-model="userPasswordInfo.newPassword2"
						:placeholder="$t('message.pages.personal.dialog.confirmPasswordPlaceholder')" show-password clearable />
				</el-form-item>
			</el-form>
			<template #footer>
				<el-button @click="passwordFormShow = false">取消</el-button>
				<el-button type="primary" @click="settingPassword">提交</el-button>
			</template>
		</el-dialog>
	</div>
</template>

<script setup lang="ts" name="personal">
import { reactive, computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { formatAxis } from '/@/utils/formatTime';
import * as api from './api';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { dictionary } from '/@/utils/dictionary';
import { Session } from '/@/utils/storage';

interface PersonalState {
	personalForm: {
		avatar: string;
		username: string;
		name: string;
		email: string;
		mobile: string;
		gender: string | number;
		tenant_name: string;
		dept_info: {
			dept_name: string;
		};
		role_info: Array<{
			id: number;
			name: string;
		}>;
	};
}

const router = useRouter();
const { t } = useI18n();

const currentTime = computed(() => formatAxis(new Date()));

const userInfoFormRef = ref();
const isEditing = ref(false);
const saving = ref(false);
const rules = reactive({
	name: [{ required: true, validator: (rule: any, value: any, callback: any) => {
		if (!value) callback(new Error(t('message.pages.personal.validation.nicknameRequired')));
		else callback();
	}, trigger: 'blur' }],
});

const state = reactive<PersonalState>({
	personalForm: {
		avatar: '',
		username: '',
		name: '',
		email: '',
		mobile: '',
		gender: '',
		tenant_name: '',
		dept_info: { dept_name: '' },
		role_info: [],
	},
});

const genderList = ref();
const translatedGenderList = computed(() => {
	if (!genderList.value) return [];
	const labelMap: Record<string, string> = {
		'男': t('message.pages.personal.form.genderMale'),
		'女': t('message.pages.personal.form.genderFemale'),
		'保密': t('message.pages.personal.form.genderSecret'),
	};
	return genderList.value.map((item: any) => ({
		...item,
		label: labelMap[item.label] || item.label,
	}));
});

const getUserInfo = () => {
	api.GetUserInfo({}).then((res: any) => {
		const { data } = res;
		genderList.value = dictionary('gender');
		state.personalForm.avatar = data.avatar || '';
		state.personalForm.username = data.username || '';
		state.personalForm.name = data.name || '';
		state.personalForm.email = data.email || '';
		state.personalForm.mobile = data.mobile || '';
		state.personalForm.gender = data.gender;
		state.personalForm.tenant_name = data.tenant_name || '';
		state.personalForm.dept_info.dept_name = data.dept_info.dept_name || '';
		state.personalForm.role_info = data.role_info || [];
	});
};

const submitForm = async () => {
	if (!userInfoFormRef.value) return;
	await userInfoFormRef.value.validate((valid: boolean) => {
		if (valid) {
			saving.value = true;
			api.updateUserInfo(state.personalForm).then((res: any) => {
				ElMessage.success(t('message.pages.personal.messages.updateSuccess'));
				getUserInfo();
				isEditing.value = false;
			}).finally(() => {
				saving.value = false;
			});
		} else {
			ElMessage.error(t('message.pages.personal.validation.formValidationFailed'));
		}
	});
};

onMounted(() => {
	getUserInfo();
});

/**************************密码修改部分************************/
const passwordFormShow = ref(false);
const userPasswordFormRef = ref();
const userPasswordInfo = reactive({
	oldPassword: '',
	newPassword: '',
	newPassword2: '',
});

const validatePass = (rule: any, value: any, callback: any) => {
	const pwdRegex = new RegExp('(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}');
	if (value === '') {
		callback(new Error(t('message.pages.personal.validation.oldPasswordRequired')));
	} else if (value === userPasswordInfo.oldPassword) {
		callback(new Error(t('message.pages.personal.validation.sameAsOldPassword')));
	} else if (!pwdRegex.test(value)) {
		callback(new Error(t('message.pages.personal.validation.passwordComplexity')));
	} else {
		if (userPasswordInfo.newPassword2 !== '') {
			userPasswordFormRef.value.validateField('newPassword2');
		}
		callback();
	}
};
const validatePass2 = (rule: any, value: any, callback: any) => {
	if (value === '') {
		callback(new Error(t('message.pages.personal.validation.confirmPasswordRequired')));
	} else if (value !== userPasswordInfo.newPassword) {
		callback(new Error(t('message.pages.personal.validation.passwordMismatch')));
	} else {
		callback();
	}
};

const passwordRules = reactive({
	oldPassword: [
		{ required: true, message: t('message.pages.personal.validation.oldPasswordRequired'), trigger: 'blur' },
	],
	newPassword: [{ validator: validatePass, trigger: 'blur' }],
	newPassword2: [{ validator: validatePass2, trigger: 'blur' }],
});

const settingPassword = () => {
	userPasswordFormRef.value.validate((valid: boolean) => {
		if (valid) {
			api.UpdatePassword(userPasswordInfo).then((res: any) => {
				ElMessage.success(t('message.pages.personal.messages.passwordChangeSuccess'));
				setTimeout(() => {
					Session.remove('token');
					router.push('/login');
				}, 1000);
			});
		} else {
			ElMessage.error(t('message.pages.personal.messages.formValidationFailed'));
		}
	});
};
</script>

<style scoped lang="scss">
.personal-page {
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

	.cols {
		display: grid;
		grid-template-columns: 1fr;
		gap: 16px;
		align-items: start;

		.col {
			background: #1a1a1c;
			border: 1px solid #2a2a2a;
			border-radius: 12px;
			padding: 20px 24px;

			.col-head {
				display: flex;
				align-items: center;
				justify-content: space-between;
				margin-bottom: 18px;
				font-size: 15px;
				font-weight: 600;
				color: #f4f4f5;
			}
		}
	}

	.profile-col {
		.profile-main {
			display: flex;
			align-items: center;
			gap: 18px;
			padding-bottom: 18px;
			margin-bottom: 18px;
			border-bottom: 1px solid #2a2a2a;

			.welcome {
				.hello {
					font-size: 18px;
					font-weight: 600;
					color: #f4f4f5;
				}
				.acc {
					margin-top: 4px;
					font-size: 13px;
					color: #b1b4b8;
				}
				.role-tags {
					margin-top: 10px;
					display: flex;
					gap: 6px;
					flex-wrap: wrap;
				}
			}
		}

		.personal-form {
			:deep(.el-form-item__label) {
				color: #b1b4b8;
			}
			:deep(.el-input__wrapper) {
				background: #242424;
				box-shadow: 0 0 0 1px #333333 inset;
				border-radius: 8px;

				&:hover {
					box-shadow: 0 0 0 1px #444444 inset;
				}
				&.is-focus {
					box-shadow: 0 0 0 1.5px #409eff inset;
				}
			}
			.dept-tag {
				margin-left: 0;
			}
		}

		.form-button-section {
			display: flex;
			justify-content: flex-end;
			gap: 10px;
			padding-top: 14px;
			margin-top: 4px;
			border-top: 1px solid #2a2a2a;
		}
	}
}

:deep(.el-dialog) {
	background: #1a1a1c;
	border: 1px solid #2a2a2a;
	border-radius: 12px;
	color: #eaeaea;

	.el-dialog__title {
		color: #f4f4f5;
	}

	.el-form-item__label {
		color: #b1b4b8;
	}

	.el-input__wrapper {
		background: #242424;
		box-shadow: 0 0 0 1px #333333 inset;
		border-radius: 8px;
	}
}

@media (max-width: 960px) {
	.cols {
		grid-template-columns: 1fr;
	}
}
</style>
