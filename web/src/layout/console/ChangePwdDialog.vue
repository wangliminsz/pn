<template>
	<el-dialog :model-value="visible" :title="title" width="440px" append-to-body destroy-on-close
		:close-on-click-modal="false" @update:model-value="close">
		<el-form ref="formRef" :model="form" :rules="rules" label-width="96px" label-position="left">
			<el-form-item label="旧密码" prop="oldPassword">
				<el-input v-model="form.oldPassword" type="password" show-password clearable placeholder="请输入当前密码" />
			</el-form-item>
			<el-form-item label="新密码" prop="newPassword">
				<el-input v-model="form.newPassword" type="password" show-password clearable placeholder="8-30 位，含字母和数字" />
			</el-form-item>
			<el-form-item label="确认新密码" prop="newPassword2">
				<el-input v-model="form.newPassword2" type="password" show-password clearable placeholder="再次输入新密码" />
			</el-form-item>
		</el-form>
		<template #footer>
			<el-button @click="close">取消</el-button>
			<el-button type="primary" :loading="saving" @click="submit">保存</el-button>
		</template>
	</el-dialog>
</template>

<style scoped lang="scss">
/* Simple Better: 校验时只显示红边框, 不显示红色提示文字 */
:deep(.el-form-item__error) {
	display: none !important;
}
</style>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import { request } from '/@/utils/service';
import { Session } from '/@/utils/storage';
import { useRouter } from 'vue-router';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{ close: [] }>();
const router = useRouter();

const title = '修改密码';
const formRef = ref<any>();
const saving = ref(false);
const form = reactive({ oldPassword: '', newPassword: '', newPassword2: '' });

// 新密码: 8-30 位且含字母和数字
const pwdRegex = /(?=.*[0-9])(?=.*[a-zA-Z]).{8,30}/;
const rules = {
	oldPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
	newPassword: [
		{ required: true, message: '请输入新密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (!pwdRegex.test(value)) {
				cb(new Error('新密码需 8-30 位，含字母和数字'));
			} else {
				cb();
			}
		}, trigger: 'blur' },
	],
	newPassword2: [
		{ required: true, message: '请再次输入新密码', trigger: 'blur' },
		{ validator: (_: any, value: string, cb: Function) => {
			if (value !== form.newPassword) {
				cb(new Error('两次输入的新密码不一致'));
			} else {
				cb();
			}
		}, trigger: 'blur' },
	],
};

const close = () => {
	form.oldPassword = '';
	form.newPassword = '';
	form.newPassword2 = '';
	emit('close');
};

const submit = () => {
	formRef.value.validate((valid: boolean) => {
		if (!valid) return;
		saving.value = true;
		request({
			url: '/api/system/user/change_password/',
			method: 'put',
			data: { ...form },
		})
			.then((res: any) => {
				if (res.code === 2000) {
					ElMessage.success('密码修改成功，请重新登录');
					close();
					setTimeout(() => {
						Session.remove('token');
						router.push('/login');
					}, 800);
				} else {
					ElMessage.error(res.msg || '修改失败');
				}
			})
			.finally(() => {
				saving.value = false;
			});
	});
};
</script>
