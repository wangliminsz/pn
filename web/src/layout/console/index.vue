<template>
	<div class="console">
		<!-- 单级侧栏 -->
		<aside class="console-side">
			<div class="side-logo">
				<img :src="logo" alt="proNotify" />
			</div>
			<nav class="side-nav">
				<router-link v-for="item in menus" :key="item.path" :to="item.path" class="nav-item"
					:class="{ active: isActive(item.path) }">
					<el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
					<span class="nav-label">{{ item.title }}</span>
				</router-link>
			</nav>
			<div class="side-foot">
				<span class="foot-hint">{{ $t('message.pages.consoleLayout.foot') }}</span>
			</div>
		</aside>

		<!-- 内容区 -->
		<div class="console-main">
			<header class="main-topbar">
				<span class="topbar-title">{{ currentTitle }}</span>
				<div class="topbar-right">
					<span class="lang" @click="toggleLang">{{ langLabel }}</span>
					<el-dropdown trigger="click" @command="onUserCommand">
						<span class="user-chip">
							<el-icon class="user-ico"><ele-User /></el-icon>
							<span class="user-name">{{ userName }}</span>
							<el-icon class="caret"><ele-ArrowDown /></el-icon>
						</span>
						<template #dropdown>
							<el-dropdown-menu>
								<el-dropdown-item command="changePwd">
									<el-icon style="margin-right:6px"><ele-EditPen /></el-icon>{{ $t('message.pages.consoleLayout.changePwd') }}
								</el-dropdown-item>
								<el-dropdown-item command="logout" divided>
									<el-icon style="margin-right:6px"><ele-SwitchButton /></el-icon>{{ $t('message.pages.consoleLayout.logout') }}
								</el-dropdown-item>
							</el-dropdown-menu>
						</template>
					</el-dropdown>
					<el-icon class="logout" @click="logout"><ele-SwitchButton /></el-icon>
				</div>
			</header>
			<main class="main-content">
				<router-view />
			</main>
		</div>

		<ChangePwdDialog :visible="pwdDlgVisible" @close="pwdDlgVisible = false" />
	</div>
</template>

<script setup lang="ts" name="consoleLayout">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Session } from '/@/utils/storage';
import { NextLoading } from '/@/utils/loading';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
import logo from '/@/assets/img/proNotify_logo_black_trans.png';
import ChangePwdDialog from './ChangePwdDialog.vue';

const route = useRoute();
const { locale, t } = useI18n();
const { userInfos } = storeToRefs(useUserInfo());
const pwdDlgVisible = ref(false);

const userName = computed(() => userInfos.value.name || userInfos.value.username || t('message.pages.consoleLayout.defaultUser'));

const onUserCommand = (cmd: string) => {
	if (cmd === 'changePwd') {
		pwdDlgVisible.value = true;
	} else if (cmd === 'logout') {
		logout();
	}
};

const menus = computed(() => [
	{ path: '/admin/dashboard', title: t('message.pages.consoleLayout.menu.dashboard'), icon: 'ele-DataBoard' },
	{ path: '/admin/tenant', title: t('message.pages.consoleLayout.menu.tenant'), icon: 'ele-OfficeBuilding' },
	{ path: '/admin/today', title: t('message.pages.consoleLayout.menu.today'), icon: 'ele-AlarmClock' },
	{ path: '/admin/linebot', title: t('message.pages.consoleLayout.menu.lineBot'), icon: 'ele-ChatDotRound' },
	{ path: '/admin/superadmin', title: t('message.pages.consoleLayout.menu.superadmin'), icon: 'ele-UserFilled' },
	{ path: '/admin/personal', title: t('message.pages.consoleLayout.menu.personal'), icon: 'ele-User' },
]);

const isActive = (path: string) => route.path === path;

const currentTitle = computed(() => menus.value.find((m) => isActive(m.path))?.title || t('message.pages.consoleLayout.menu.dashboard'));

const langLabel = computed(() => {
	const map: Record<string, string> = { 'zh-cn': '中文', en: 'EN', 'zh-tw': '繁中', th: 'ไทย' };
	return map[locale.value] || 'EN';
});

const toggleLang = () => {
	const order = ['en', 'zh-cn', 'th', 'zh-tw'];
	const next = order[(order.indexOf(locale.value) + 1) % order.length];
	locale.value = next;
};

const logout = () => {
	Session.clear();
	window.location.reload();
};

onMounted(() => {
	NextLoading.done(600);
});
</script>

<style scoped lang="scss">
/* proNotify 深色主题: 与登录页 / 后台深色一致 (design-system/pronotify/MASTER.md) */
.console {
	// ---- 品牌 token（深色下提亮主色，与登录页 / 后台深色一致） ----
	--cn-primary: #409eff;
	--cn-primary-hover: #66b1ff;
	--cn-primary-soft: rgba(64, 158, 255, 0.12);
	--cn-accent: #ea580c;
	--cn-bg: #1f1f1f;
	--cn-side: #171717;
	--cn-card: #1a1a1c;
	--cn-card-2: #212121;
	--cn-input: #242424;
	--cn-border: #2a2a2a;
	--cn-border-strong: #333333;
	--cn-text: #dadada;
	--cn-text-strong: #eaeaea;
	--cn-muted: #b1b4b8;
	--cn-faint: #8f9297;

	display: flex;
	height: 100dvh;
	overflow: hidden;
	font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans Thai', sans-serif;
	color: var(--cn-text);
	background: var(--cn-bg);
}

// 侧栏
.console-side {
	width: 230px;
	flex-shrink: 0;
	background: var(--cn-side);
	border-right: 1px solid var(--cn-border);
	display: flex;
	flex-direction: column;

	.side-logo {
		padding: 22px 20px 24px;
		border-bottom: 1px solid var(--cn-border);

		img {
			display: block;
			width: 172px;
			height: auto;
		}
	}

	.side-nav {
		flex: 1;
		padding: 14px 12px;
		display: flex;
		flex-direction: column;
		gap: 4px;

		.nav-item {
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 12px 14px;
			border-radius: 10px;
			color: var(--cn-muted);
			text-decoration: none;
			cursor: pointer;
			transition: all 0.2s ease;

			.nav-icon {
				font-size: 18px;
			}

			.nav-label {
				font-size: 14px;
				font-weight: 500;
			}

			&:hover {
				background: rgba(255, 255, 255, 0.04);
				color: var(--cn-text);
			}

			&.active {
				background: rgba(64, 158, 255, 0.14);
				color: #ffffff;

				.nav-icon {
					color: var(--cn-primary);
				}
			}
		}
	}

	.side-foot {
		padding: 16px 20px;
		border-top: 1px solid var(--cn-border);

		.foot-hint {
			font-size: 12px;
			color: var(--cn-faint);
			letter-spacing: 0.02em;
		}
	}
}

// 主区
.console-main {
	flex: 1;
	display: flex;
	flex-direction: column;
	min-width: 0;

	.main-topbar {
		height: 60px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 24px;
		background: var(--cn-side);
		border-bottom: 1px solid var(--cn-border);

		.topbar-title {
			font-size: 16px;
			font-weight: 600;
			color: var(--cn-text);
		}

		.topbar-right {
			display: flex;
			align-items: center;
			gap: 20px;

			.lang {
				font-size: 13px;
				color: var(--cn-muted);
				cursor: pointer;
				transition: color 0.2s ease;

				&:hover {
					color: var(--cn-primary);
				}
			}

			.user-chip {
				display: flex;
				align-items: center;
				gap: 6px;
				padding: 5px 10px;
				border-radius: 8px;
				color: var(--cn-text);
				cursor: pointer;
				transition: background 0.2s ease;
				outline: none;

				.user-ico {
					font-size: 16px;
				}

				.user-name {
					font-size: 13px;
					max-width: 120px;
					overflow: hidden;
					text-overflow: ellipsis;
					white-space: nowrap;
				}

				.caret {
					font-size: 12px;
					color: var(--cn-faint);
				}

				&:hover {
					background: rgba(255, 255, 255, 0.06);
				}
			}

			.logout {
				font-size: 18px;
				color: var(--cn-muted);
				cursor: pointer;
				transition: color 0.2s ease;

				&:hover {
					color: var(--cn-primary);
				}
			}
		}
	}

	.main-content {
		flex: 1;
		overflow: auto;
		padding: 24px;
	}
}
</style>

<style lang="scss">
// 在控制台内覆盖全局 fastCrud 的 fs-page 高度, 避免与顶栏重叠
.console .main-content {
	.fs-page,
	.fs-crud {
		height: auto !important;
		min-height: calc(100vh - 108px);
	}
}
</style>
