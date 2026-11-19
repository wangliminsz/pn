import { RouteRecordRaw } from 'vue-router';

/**
 * 路由meta对象参数说明
 * meta: {
 *      proNotify:          菜单栏及 tagsView 栏、菜单搜索名称（国际化）
 *      isLink：        是否超链接菜单，开启外链条件，`1、isLink: 链接地址不为空`
 *      isHide：        是否隐藏此路由
 *      isKeepAlive：   是否缓存组件状态
 *      isAffix：       是否固定在 tagsView 栏上
 *      isIframe：      是否内嵌窗口，开启条件，`1、isIframe:true 2、isLink：链接地址不为空`
 *      roles：         当前路由权限标识，取角色管理。控制路由显示、隐藏。超级管理员：admin 普通角色：common
 *      icon：          菜单、tagsView 图标，阿里：加 `iconfont xxx`，fontawesome：加 `fa xxx`
 * }
 */

/**
 * 定义动态路由
 * 前端添加路由，请在顶级节点的 `children 数组` 里添加
 * @description 未开启 isRequestRoutes 为 true 时使用（前端控制路由），开启时第一个顶级 children 的路由将被替换成接口请求回来的路由数据
 * @description 各字段请查看 `/@/views/system/menu/component/addMenu.vue 下的 ruleForm`
 * @returns 返回路由菜单数据
 */
export const dynamicRoutes: Array<RouteRecordRaw> = [
	{
		path: '/',
		name: '/',
		component: () => import('/@/layout/tenant/index.vue'),
		redirect: '/home',
		meta: {
			isKeepAlive: true,
		},
		children: [],
	}
];

/**
 * 定义404、401界面
 * @link 参考：https://next.router.vuejs.org/zh/guide/essentials/history-mode.html#netlify
 */
export const notFoundAndNoPower = [
	{
		path: '/:path(.*)*',
		name: 'notFound',
		component: () => import('/@/views/system/error/404.vue'),
		meta: {
			proNotify: 'proNotify',
			isHide: true,
		},
	},
	{
		path: '/401',
		name: 'noPower',
		component: () => import('/@/views/system/error/401.vue'),
		meta: {
			proNotify: 'proNotify',
			isHide: true,
		},
	},
];

/**
 * 定义静态路由（默认路由）
 * 此路由不要动，前端添加路由的话，请在 `dynamicRoutes 数组` 中添加
 * @description 前端控制直接改 dynamicRoutes 中的路由，后端控制不需要修改，请求接口路由数据时，会覆盖 dynamicRoutes 第一个顶级 children 的内容（全屏，不包含 layout 中的路由出口）
 * @returns 返回路由菜单数据
 */
export const staticRoutes: Array<RouteRecordRaw> = [
	{
		path: '/login',
		name: 'login',
		component: () => import('/@/views/system/login/index.vue'),
		meta: {
			proNotify: 'proNotify',
		},
	},
	// 自助注册(独立布局, 免登录)
	{
		path: '/signup',
		name: 'signup',
		component: () => import('/@/views/signup/index.vue'),
		meta: {
			proNotify: 'proNotify',
		},
	},
	{
		path: '/signup/check',
		name: 'signupCheck',
		component: () => import('/@/views/signup/checkIndex.vue'),
		meta: {
			proNotify: 'proNotify',
		},
	},
	{
		path: '/signup/verify',
		name: 'signupVerify',
		component: () => import('/@/views/signup/verify.vue'),
		meta: {
			proNotify: 'proNotify',
		},
	},
	{
		path: '/signup/pay',
		name: 'signupPay',
		component: () => import('/@/views/signup/activate.vue'),
		meta: {
			proNotify: 'proNotify',
		},
	},
	{
		path: '/demo',
		name: 'demo',
		component: () => import('/@/views/system/demo/index.vue'),
		meta: {
			proNotify: 'proNotify'
		},
	},
	// 超级管理员独立控制台(单级侧栏, 仅超管可访问)
	{
		path: '/admin',
		name: 'admin',
		component: () => import('/@/layout/console/index.vue'),
		redirect: '/admin/dashboard',
		meta: {
			proNotify: 'proNotify',
		},
		children: [
			{
				path: '/admin/dashboard',
				name: 'adminDashboard',
				component: () => import('/@/views/admin/dashboard/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
			{
				path: '/admin/tenant',
				name: 'adminTenant',
				component: () => import('/@/views/admin/tenant/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
			{
				path: '/admin/linebot',
				name: 'adminLinebot',
				component: () => import('/@/views/admin/linebot/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
			{
				path: '/admin/today',
				name: 'adminToday',
				component: () => import('/@/views/admin/today/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
			{
				path: '/admin/superadmin',
				name: 'adminSuperadmin',
				component: () => import('/@/views/admin/superadmin/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
			{
				path: '/admin/personal',
				name: 'adminPersonal',
				component: () => import('/@/views/system/personal/index.vue'),
				meta: {
					proNotify: 'proNotify',
					roles: ['admin'],
				},
			},
		],
	},
];
