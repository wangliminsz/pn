<template>
	<div class="tenant-console">
		<!-- 单级侧栏 (复制超管控制台) -->
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
				<span class="foot-hint">{{ $t('message.pages.tenantLayout.foot') }}</span>
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
									<el-icon style="margin-right:6px"><ele-EditPen /></el-icon>{{ $t('message.pages.tenantLayout.changePwd') }}
								</el-dropdown-item>
								<el-dropdown-item command="logout" divided>
									<el-icon style="margin-right:6px"><ele-SwitchButton /></el-icon>{{ $t('message.pages.tenantLayout.logout') }}
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

<script setup lang="ts" name="tenantLayout">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Session } from '/@/utils/storage';
import { NextLoading } from '/@/utils/loading';
import { storeToRefs } from 'pinia';
import { useUserInfo } from '/@/stores/userInfo';
import logo from '/@/assets/img/proNotify_logo_black_trans.png';
import ChangePwdDialog from '/@/layout/console/ChangePwdDialog.vue';

const route = useRoute();
const { locale, t } = useI18n();
const { userInfos } = storeToRefs(useUserInfo());
const pwdDlgVisible = ref(false);

const userName = computed(() => userInfos.value.name || userInfos.value.username || t('message.pages.tenantLayout.defaultUser'));

const onUserCommand = (cmd: string) => {
	if (cmd === 'changePwd') {
		pwdDlgVisible.value = true;
	} else if (cmd === 'logout') {
		logout();
	}
};

const isTenantManager = computed(() =>
	(userInfos.value.role_info || []).some((r: any) => r.key === 'tenant_manager')
);

const menus = computed(() => [
	{ path: '/home', title: t('message.pages.tenantLayout.menu.home'), icon: 'ele-HomeFilled' },
	{ path: '/property', title: t('message.pages.tenantLayout.menu.property'), icon: 'ele-OfficeBuilding' },
	{ path: '/linebot', title: t('message.pages.tenantLayout.menu.lineBot'), icon: 'ele-MagicStick' },
	{ path: '/calendar', title: t('message.pages.tenantLayout.menu.calendar'), icon: 'ele-Calendar' },
	...(isTenantManager.value ? [{ path: '/org', title: t('message.pages.tenantLayout.menu.org'), icon: 'ele-Coordinate' }] : []),
	...(isTenantManager.value ? [{ path: '/broadcast', title: t('message.pages.tenantLayout.menu.broadcast'), icon: 'ele-ChatDotRound' }] : []),
	...(isTenantManager.value ? [{ path: '/groupdoc', title: t('message.pages.tenantLayout.menu.groupDoc'), icon: 'ele-FolderOpened' }] : []),
	{ path: '/changelog', title: t('message.pages.tenantLayout.menu.changelog'), icon: 'ele-Finished' },
	{ path: '/personal', title: t('message.pages.tenantLayout.menu.personal'), icon: 'ele-User' },
]);

const isActive = (path: string) => route.path === path;

const currentTitle = computed(() => menus.value.find((m) => isActive(m.path))?.title || t('message.pages.tenantLayout.menu.home'));

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
/* 与超管控制台完全一致的深色主题/布局 */
.tenant-console {
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
/* 覆盖全局 fastCrud 的 fs-page 高度, 避免与顶栏重叠(同超管控制台) */
.tenant-console .main-content {
	.fs-page,
	.fs-crud {
		height: auto !important;
		min-height: calc(100vh - 108px);
	}
}
</style>