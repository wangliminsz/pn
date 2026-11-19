<template>
	<el-form ref="formRef" size="large" class="login-content-form" :model="form" :rules="rules"
		@keyup.enter="submit">
		<el-form-item class="login-animation1" prop="password">
			<el-input :type="isShowPassword ? 'text' : 'password'" v-model="form.password" clearable
				:placeholder="$t('message.pages.login.resetPwd.passwordPlaceholder')" autocomplete="new-password">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-Unlock /></el-icon>
				</template>
				<template #suffix>
					<i class="iconfont el-input__icon login-content-password"
						:class="isShowPassword ? 'icon-yincangmima' : 'icon-xianshimima'"
						@click="isShowPassword = !isShowPassword">
					</i>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation2" prop="password2">
			<el-input :type="isShowPassword ? 'text' : 'password'" v-model="form.password2" clearable
				:placeholder="$t('message.pages.login.resetPwd.password2Placeholder')" autocomplete="new-password">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-Unlock /></el-icon>
				</template>
				<template #suffix>
					<i class="iconfont el-input__icon login-content-password"
						:class="isShowPassword ? 'icon-yincangmima' : 'icon-xianshimima'"
						@click="isShowPassword = !isShowPassword">
					</i>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation3">
			<el-button type="primary" class="login-content-submit" round :loading="resetting" @click="submit">
				<span>{{ $t('message.pages.login.resetPwd.btnText') }}</span>
			</el-button>
		</el-form-item>
	</el-form>
	<div class="reset-extra">
		<div class="reset-hint">{{ $t('message.pages.login.resetPwd.hint') }}</div>
		<el-button link type="primary" class="reset-back" @click="$router.replace('/login')">{{ $t('message.pages.login.resetPwd.back') }}</el-button>
	</div>
</template>

<script lang="ts" setup name="resetPwdToken">
import { computed, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import * as loginApi from './../api';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const token = computed(() => (route.query?.token as string) || '');
const form = reactive({ password: '', password2: '' });
const resetting = ref(false);
const isShowPassword = ref(false);
const formRef = ref<any>();

const rules = {
	password: [
		{ required: true, message: () => t('message.pages.login.resetPwd.passwordRequired'), trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (!/(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/.test(value || '')) cb(new Error(t('message.pages.login.resetPwd.passwordComplexity')));
			else cb();
		}, trigger: 'blur' },
	],
	password2: [
		{ required: true, message: () => t('message.pages.login.resetPwd.confirmRequired'), trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (value !== form.password) cb(new Error(t('message.pages.login.resetPwd.mismatch')));
			else cb();
		}, trigger: 'blur' },
	],
};

const submit = () => {
	formRef.value.validate(async (valid: boolean) => {
		if (!valid) return;
		resetting.value = true;
		try {
			const res: any = await loginApi.ConfirmReset(token.value, form.password);
			if (res.code === 2000) {
				ElMessage.success(res.msg || t('message.pages.login.resetPwd.success'));
				router.replace('/login?redirect=/');
			} else {
				ElMessage.error(res.msg || t('message.pages.login.resetPwd.failed'));
			}
		} finally {
			resetting.value = false;
		}
	});
};
</script>

<style scoped lang="scss">
.login-content-form {
	margin-top: 0;

	@for $i from 1 through 5 {
		.login-animation#{$i} {
			opacity: 0;
			animation-name: error-num;
			animation-duration: 0.5s;
			animation-fill-mode: forwards;
			animation-delay: calc($i/10) + s;
		}
	}

	.login-content-password {
		display: inline-block;
		width: 20px;
		cursor: pointer;

		&:hover {
			color: #a5a8ae;
		}
	}

	.login-content-submit {
		width: 100%;
		margin-top: 15px;
	}
}

.reset-extra {
	.reset-hint {
		margin-top: 16px;
		font-size: 12px;
		color: var(--pn-muted, #b1b4b8);
		text-align: center;
	}
	.reset-back {
		display: block;
		margin: 10px auto 0;
	}
}
</style>
