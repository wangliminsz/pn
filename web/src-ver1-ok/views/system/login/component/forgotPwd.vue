<template>
	<div class="forgot-box">
		<el-form ref="formRef" size="large" class="login-content-form" :model="form" :rules="rules" label-position="top"
			@keyup.enter="submit">
			<el-form-item class="login-animation1" prop="email">
				<el-input v-model="form.email" :placeholder="$t('message.pages.login.forgotPwd.emailPlaceholder')" clearable autocomplete="off">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Message /></el-icon>
					</template>
				</el-input>
			</el-form-item>
			<el-form-item class="login-animation2">
				<el-button type="primary" class="login-content-submit" round :loading="sending" @click="submit">
					<span>{{ $t('message.pages.login.forgotPwd.btnText') }}</span>
				</el-button>
			</el-form-item>
		</el-form>
		<div class="forgot-extra">
			<div class="forgot-hint">{{ $t('message.pages.login.forgotPwd.hint') }}</div>
			<el-button link type="primary" class="forgot-back" @click="emit('back')">{{ $t('message.pages.login.forgotPwd.back') }}</el-button>
		</div>
	</div>
</template>

<script lang="ts" setup name="forgotPwd">
import { reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import * as loginApi from './../api';

const emit = defineEmits(['back']);
const { t } = useI18n();

const form = reactive({ email: '' });
const sending = ref(false);
const formRef = ref<any>();
const rules = {
	email: [{ required: true, message: () => t('message.pages.login.forgotPwd.emailRequired'), trigger: 'blur' }],
};

const submit = async () => {
	formRef.value.validate(async (valid: boolean) => {
		if (!valid) return;
		sending.value = true;
		try {
			const res: any = await loginApi.SendResetEmail(form.email);
			if (res.code === 2000) ElMessage.success(res.msg || t('message.pages.login.forgotPwd.success'));
		} finally {
			sending.value = false;
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

	.login-content-submit {
		width: 100%;
		margin-top: 15px;
	}
}

.forgot-extra {
	.forgot-hint {
		margin-top: 16px;
		font-size: 12px;
		color: var(--pn-muted, #b1b4b8);
		text-align: center;
	}
	.forgot-back {
		display: block;
		margin: 10px auto 0;
	}
}
</style>
