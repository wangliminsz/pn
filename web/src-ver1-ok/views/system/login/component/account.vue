<template>
	<el-form ref="formRef" size="large" class="login-content-form" :model="state.ruleForm" :rules="rules" @keyup.enter="loginClick">
		<el-form-item class="login-animation1">
			<el-input type="text" :placeholder="$t('message.pages.login.account.accountPlaceholder1')" v-model="ruleForm.username"
				clearable autocomplete="off">
				<template #prefix>
					<el-icon class="el-input__icon"><ele-Message /></el-icon>
				</template>
			</el-input>
		</el-form-item>
		<el-form-item class="login-animation2">
			<el-input :type="isShowPassword ? 'text' : 'password'" :placeholder="$t('message.pages.login.account.accountPlaceholder2')"
				v-model="ruleForm.password" autocomplete="new-password" name="login-pwd">
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
		<el-form-item v-if="isShowCaptcha" class="login-animation3 captcha-item">
			<div class="captcha-row">
				<el-input type="text" :placeholder="$t('message.pages.login.account.accountPlaceholder3')"
					v-model="state.ruleForm.captcha" clearable autocomplete="off" @keyup.enter="loginClick">
					<template #prefix>
						<el-icon class="el-input__icon"><ele-Key /></el-icon>
					</template>
				</el-input>
				<img v-if="captchaImg" class="captcha-img" :src="captchaImg" alt="captcha"
					:title="$t('message.pages.login.validation.refreshCaptcha')" @click="getCaptcha" />
			</div>
		</el-form-item>
		<el-form-item class="login-animation4">
			<el-button type="primary" class="login-content-submit" round @click="loginClick"
				:loading="loading.signIn">
				<span>{{ $t('message.pages.login.account.accountBtnText') }}</span>
			</el-button>
		</el-form-item>
		<div class="forgot-row">
			<span class="forgot-link" @click="openForgot">{{ $t('message.pages.login.account.forgotPassword') }}</span>
			<span class="signup-link" @click="$router.push('/signup')">{{ $t('message.pages.login.account.signup') }}</span>
		</div>
	</el-form>  <!--      申请试用-->
  <div style="text-align: center" v-if="showApply()">
    <el-button class="login-content-apply" link type="primary" plain round @click="applyBtnClick">
      <span>{{ $t('message.pages.login.account.apply') }}</span>
    </el-button>
  </div>
</template>

<script lang="ts">
import { toRefs, reactive, defineComponent, computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { FormInstance, FormRules } from 'element-plus';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
import { storeToRefs } from 'pinia';
import { useThemeConfig } from '/@/stores/themeConfig';
import { initFrontEndControlRoutes } from '/@/router/frontEnd';
import { initBackEndControlRoutes } from '/@/router/backEnd';
import { Session } from '/@/utils/storage';
import { NextLoading } from '/@/utils/loading';
import mittBus from '/@/utils/mitt';
import * as loginApi from '/@/views/system/login/api';
import { useUserInfo } from '/@/stores/userInfo';
import { DictionaryStore } from '/@/stores/dictionary';
import { SystemConfigStore } from '/@/stores/systemConfig';
import { BtnPermissionStore } from '/@/plugin/permission/store.permission';
import { Md5 } from 'ts-md5';
import { errorMessage } from '/@/utils/message';
import {getBaseURL} from "/@/utils/baseUrl";

export default defineComponent({
	name: 'loginAccount',
	setup() {
		const { t } = useI18n();
		const openForgot = () => mittBus.emit('openForgot');
		const storesThemeConfig = useThemeConfig();
		const { themeConfig } = storeToRefs(storesThemeConfig);
		const { userInfos } = storeToRefs(useUserInfo());
		const route = useRoute();
		const router = useRouter();
		const state = reactive({
			isShowPassword: false,
			ruleForm: {
				username: '',
				password: '',
				captcha: '',
				captchaKey: '',
			},
			loading: {
				signIn: false,
			},
		});
		const rules = reactive<FormRules>({});
		const formRef = ref();

		// 验证码(深色 SVG): 依系统配置决定是否显示
		const captchaImg = ref('');
		const captchaLoading = ref(false);
		// 是否显示验证码: 读取 GlobalTheme 后由 captcha_state 决定
		const isShowCaptcha = ref(false);

		const getCaptcha = async () => {
			captchaLoading.value = true;
			try {
				const res: any = await loginApi.getCaptcha();
				const data = res.data || {};
				if (data.image_base) {
					captchaImg.value = data.image_base;
					state.ruleForm.captchaKey = data.key;
					state.ruleForm.captcha = '';
					if (!isShowCaptcha.value) isShowCaptcha.value = true;
				}
			} catch (e) {
				console.error(e);
			} finally {
				captchaLoading.value = false;
			}
		};

		const applyBtnClick = async () => {
			window.open(getBaseURL('/api/system/apply_for_trial/'));
		};
		const loginClick = async () => {
			if (!state.ruleForm.username || !state.ruleForm.password) {
				errorMessage(t('message.pages.login.validation.fillLoginInfo'))
				return;
			}
			if (isShowCaptcha.value && (!state.ruleForm.captcha || !state.ruleForm.captchaKey)) {
				errorMessage(t('message.pages.login.validation.captchaRequired') || '请输入验证码');
				return;
			}
			loginApi.login({ ...state.ruleForm, password: Md5.hashStr(state.ruleForm.password) })
				.then(async (res: any) => {
					if (res.code === 2000) {
              const {data} = res
              Cookies.set('username', res.data.username);
              Session.remove('userInfo'); // 丢弃旧会话缓存的用户信息(如旧的 pwd_change_count), 避免首登改密被绕过
              Session.set('token', res.data.access);
              useUserInfo().setPwdChangeCount(data.pwd_change_count)
              if(data.pwd_change_count==0){
                return router.push('/login');
              }
							if (!themeConfig.value.isRequestRoutes) {
								// 前端控制路由，2、请注意执行顺序
								initFrontEndControlRoutes();
								loginSuccess();
							} else {
								// 模拟后端控制路由，isRequestRoutes 为 true，则开启后端控制路由
								// 添加完动态路由，再进行 router 跳转，否则可能报错 No match found for location with path "/"
								await initBackEndControlRoutes();
								// 执行完 initBackEndControlRoutes，再执行 signInSuccess
								loginSuccess();
							}
						}
					}).catch((err: any) => {
						// 登录错误
						console.error(err);
					});
		};



		// 登录成功后的跳转
		const loginSuccess = () => {
			//获取所有字典
			DictionaryStore().getSystemDictionarys();
			// 登录成功，跳到转首页
      const pwd_change_count = userInfos.value.pwd_change_count ?? 0
      if(pwd_change_count > 0){
        // 超级管理员: 进入独立控制台
        if (userInfos.value.is_superuser) {
          router.push('/admin/dashboard');
        } else if (route.query?.redirect) {
          // 如果是复制粘贴的路径，非首页/登录页，那么登录成功后重定向到对应的路径中
          const paramsRaw = (route.query?.params as string) || '';
          router.push({
        		path: <string>route.query?.redirect,
        		query: Object.keys(paramsRaw).length > 0 ? JSON.parse(paramsRaw) : '',
        	});
        } else {
        	router.push('/');
        }
        // 关闭 loading
        state.loading.signIn = true;
      }
			// 添加 loading，防止第一次进入界面时出现短暂空白
			NextLoading.start();
		};
		onMounted(() => {
			//获取系统配置
			SystemConfigStore().getSystemConfigs();
			// 预取验证码(后端开启验证码时返回图片, 否则自动隐藏)
			getCaptcha();
			// 防止浏览器把上次改密/登录的密码自动填充回来: 挂载后强制清空并保持未填充状态
			state.ruleForm.password = '';
			state.ruleForm.username = '';
			// 浏览器密码管理器常在渲染后短暂延迟内自动填充, 需错峰再清一次 + 聚焦再清(用户点击时)
			const clearAutofill = () => {
				state.ruleForm.password = '';
			};
			requestAnimationFrame(() => requestAnimationFrame(() => clearAutofill()));
			setTimeout(clearAutofill, 400);
			setTimeout(clearAutofill, 1200);
		});
    // 是否显示申请试用按钮
    const showApply = () => {
      return window.location.href.indexOf('public') != -1
    }

		return {
			loginClick,
			loginSuccess,
			isShowCaptcha,
			captchaImg,
			captchaLoading,
			getCaptcha,
			openForgot,
			state,
			formRef,
			rules,
      applyBtnClick,
      showApply,
			...toRefs(state),
		};
	},
});
</script>

<style scoped lang="scss">
// 定义error-num动画的关键帧
@keyframes error-num {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-content-form {
	margin-top: 0;

	@for $i from 1 through 4 {
		.login-animation#{$i} {
			opacity: 0;
			animation-name: error-num;
			animation-duration: 0.5s;
			animation-fill-mode: forwards;
			animation-delay: #{ $i/10 }s;
		}
	}

	.login-content-password {
		display: inline-block;
		width: 20px;
		cursor: pointer;

		&:hover {
			color: #909397;
		}
	}

	.login-content-submit {
		width: 100%;
		margin-top: 15px;
	}

	.captcha-item {
		margin-top: 4px;
	}

	.captcha-row {
		display: flex;
		align-items: stretch;
		gap: 12px;
		width: 100%;

		:deep(.el-input) {
			flex: 1;
		}

		.captcha-img {
			width: 110px;
			height: 40px;
			border-radius: 8px;
			border: 1px solid rgba(255, 255, 255, 0.14);
			cursor: pointer;
			object-fit: cover;
			flex-shrink: 0;
			transition: opacity 0.2s ease;

			&:hover {
				opacity: 0.85;
			}
		}
	}
}
// 忘记密码/注册入口
.forgot-row {
	margin-top: 12px;
	display: flex;
	justify-content: space-between;
	align-items: center;
	.forgot-link {
		font-size: 13px;
		color: #b1b4b8;
		cursor: pointer;
		&:hover {
			color: #409eff;
		}
	}
	.signup-link {
		font-size: 13px;
		color: #b1b4b8;
		cursor: pointer;
		&:hover {
			color: #409eff;
		}
	}
}
</style>
