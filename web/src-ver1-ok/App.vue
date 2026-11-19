<template>
	<el-config-provider :size="getGlobalComponentSize" :locale="getGlobalI18n">
		<!-- v-show="themeConfig.lockScreenTime > 1" -->
		<router-view v-show="themeConfig.lockScreenTime > 1" />
		<LockScreen v-if="themeConfig.isLockScreen" />
		<Setings ref="setingsRef" v-show="themeConfig.lockScreenTime > 1" />
		<CloseFull v-if="!themeConfig.isLockScreen" />
<!--		<Upgrade v-if="getVersion" />-->
	</el-config-provider>
</template>

<script setup lang="ts" name="app">
import { defineAsyncComponent, computed, ref, onBeforeMount, onMounted, onUnmounted, nextTick, watch, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { storeToRefs } from 'pinia';
import { useTagsViewRoutes } from '/@/stores/tagsViewRoutes';
import { useThemeConfig } from '/@/stores/themeConfig';
import other from '/@/utils/other';
import { Local, Session } from '/@/utils/storage';
import mittBus from '/@/utils/mitt';
import setIntroduction from '/@/utils/setIconfont';
import websocket from '/@/utils/websocket';

// 引入组件
const LockScreen = defineAsyncComponent(() => import('/@/layout/lockScreen/index.vue'));
const Setings = defineAsyncComponent(() => import('/@/layout/navBars/breadcrumb/setings.vue'));
const CloseFull = defineAsyncComponent(() => import('/@/layout/navBars/breadcrumb/closeFull.vue'));
const Upgrade = defineAsyncComponent(() => import('/@/layout/upgrade/index.vue'));
import { ElMessageBox, ElNotification, NotificationHandle } from 'element-plus';
import { useCore } from '/@/utils/cores';
// 定义变量内容
const { messages, locale } = useI18n();
const setingsRef = ref();
const route = useRoute();
const stores = useTagsViewRoutes();
const storesThemeConfig = useThemeConfig();
const { themeConfig } = storeToRefs(storesThemeConfig);
const core = useCore();
const router = useRouter();
// 获取版本号
const getVersion = computed(() => {
	let isVersion = false;
	if (route.path !== '/login') {
		// @ts-ignore
		if ((Local.get('version') && Local.get('version') !== __VERSION__) || !Local.get('version')) isVersion = true;
	}
	return isVersion;
});
// 获取全局组件大小
const getGlobalComponentSize = computed(() => {
	return other.globalComponentSize();
});
// 获取全局 i18n
const getGlobalI18n = computed(() => {
	return messages.value[locale.value];
});
// 设置初始化，防止刷新时恢复默认
onBeforeMount(() => {
	// 设置批量第三方 icon 图标
	setIntroduction.cssCdn();
	// 设置批量第三方 js
	setIntroduction.jsCdn();
});
// 页面加载时
onMounted(() => {
	// 全局弹窗安全默认:
	// 1) Enter 键拦截: 只要非输入型确认框(ElMessageBox)开着, Enter 一律当作「取消」, 从行为上杜绝误确认/误删。
	//    (prompt 弹窗有输入框则放行, 让 Enter 正常提交输入)
	// 2) 尽力把初始焦点放到「取消」按钮(观感; EP focus-trap 会晚些抢回 OK, 故这里仅作增强, 真正保障靠第 1 条)。
	const interceptEnterAsCancel = (e: KeyboardEvent) => {
		if (e.key !== 'Enter') return;
		const box = document.querySelector('.el-message-box');
		if (!box) return;
		if (box.querySelector('.el-message-box__input')) return; // prompt: 允许 Enter 提交输入框
		const btns = box.querySelector('.el-message-box__btns');
		if (!btns) return;
		const cancel = btns.querySelector('.el-button:not(.el-button--primary)');
		if (cancel instanceof HTMLElement) {
			e.stopPropagation();
			e.preventDefault();
			cancel.click();
		}
	};
	document.addEventListener('keydown', interceptEnterAsCancel, true);

	const focusMessageCancel = () => {
		document.querySelectorAll('.el-message-box').forEach((box) => {
			if (box.querySelector('.el-message-box__input')) return; // prompt 有输入框, 不抢输入焦点
			const cancel = box.querySelector('.el-message-box__btns .el-button:not(.el-button--primary)');
			if (cancel instanceof HTMLElement) cancel.focus({ preventScroll: true });
		});
	};
	const focusCancelWindow = () => {
		[0, 60, 150, 300, 500, 800, 1200, 2000, 3000].forEach((ms) => window.setTimeout(focusMessageCancel, ms));
	};
	const mo = new MutationObserver((muts) => {
		for (const m of muts) {
			if (m.type === 'childList' && m.addedNodes.length) {
				if (document.querySelector('.el-message-box')) focusCancelWindow();
				break;
			}
		}
	});
	mo.observe(document.body, { childList: true, subtree: true });
	if (document.querySelector('.el-message-box')) focusCancelWindow();
	document.addEventListener('visibilitychange', () => {
		if (!document.hidden) focusMessageCancel();
	});

	nextTick(() => {
		// 监听布局配'置弹窗点击打开
		mittBus.on('openSetingsDrawer', () => {
			setingsRef.value.openDrawer();
		});
    // 设置皮肤缓存版本，每次更新版本可以所有用户清空缓存
    const themeConfigVersion = '1.0.0'
		// 获取缓存中的布局配置
    if (Local.get('themeConfigVersion') !== themeConfigVersion) {
        Local.clear();
        Local.set('themeConfigVersion', themeConfigVersion);
	      window.location.reload();
        return
    }
		if (Local.get('themeConfig')) {
			storesThemeConfig.setThemeConfig({ themeConfig: Local.get('themeConfig') });
			document.documentElement.style.cssText = Local.get('themeConfigStyle');
		}
		// 默认强制开启深色主题(护眼)，覆盖旧浅色缓存
		document.documentElement.setAttribute('data-theme', 'dark');
		// 声明 color-scheme:dark, 阻止 Chrome 自动深色模式把已深色的页面/SVG 反转成白色
		document.documentElement.style.colorScheme = 'dark';
		// 获取缓存中的全屏配置
		if (Session.get('isTagsViewCurrenFull')) {
			stores.setCurrenFullscreen(Session.get('isTagsViewCurrenFull'));
		}
	});
});
// 页面销毁时，关闭监听布局配置/i18n监听
onUnmounted(() => {
	mittBus.off('openSetingsDrawer', () => {});
});
// 监听路由的变化，设置网站标题
watch(
    () => route.path,
    () => {
      other.useTitle();
      other.useFavicon();
      if (!websocket.websocket) {
        //websockt 模块
        try {
          websocket.init(wsReceive)
        } catch (e) {
          console.log('websocket错误');
        }
      }
    },
    {
      deep: true,
    }
);

// 独立整页路由(落地页/登录/注册/结算)使用浏览器级滚动; 带 layout 的后台页面仍保持 overflow hidden
const pageScrollPaths = ['/welcome', '/checkout', '/login', '/signup', '/signup/check', '/signup/verify', '/signup/pay', '/401', '/404'];
const syncPageScroll = (path: string) => {
	document.body.classList.toggle('page-scroll', pageScrollPaths.includes(path));
};
watch(() => route.path, (path) => syncPageScroll(path), { immediate: true });

// websocket相关代码
import { messageCenterStore } from '/@/stores/messageCenter';
const wsReceive = (message: any) => {
  const data = JSON.parse(message.data);
  const { unread } = data;
  const messageCenter = messageCenterStore();
  messageCenter.setUnread(unread);
  if (data.contentType === 'SYSTEM') {
    ElNotification({
      title: '系统消息',
      message: data.content,
      type: 'success',
      position: 'bottom-right',
      duration: 5000,
    });
  } else if (data.contentType === 'Content') {
    ElMessageBox.confirm(data.content, data.notificationTitle, {
      confirmButtonText: data.notificationButton,
      dangerouslyUseHTMLString: true,
      cancelButtonText: '关闭',
      type: 'info',
      closeOnClickModal: false,
    }).then(() => {
      ElMessageBox.close();
      const path = data.path;
      if (route.path === path) {
        core.bus.emit('onNewTask', { name: 'onNewTask' });
      } else {
        router.push({ path});
      }
    })
        .catch(() => {});
  }

};
onBeforeUnmount(() => {
  // 关闭连接
  websocket.close();
});
</script>
