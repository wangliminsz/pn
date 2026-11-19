import { createRouter, createWebHashHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = createRouter({
	history: createWebHashHistory(),
	routes: [
		{
			path: '/',
			redirect: '/properties',
		},
		{
			path: '/login',
			name: 'login',
			component: () => import('@/views/LoginView.vue'),
			meta: { guest: true },
		},
		{
			path: '/properties',
			name: 'properties',
			component: () => import('@/views/PropertyListView.vue'),
			meta: { requiresAuth: true },
		},
		{
			path: '/properties/new',
			name: 'property-create',
			component: () => import('@/views/PropertyFormView.vue'),
			meta: { requiresAuth: true },
		},
		{
			path: '/properties/:id/edit',
			name: 'property-edit',
			component: () => import('@/views/PropertyFormView.vue'),
			meta: { requiresAuth: true },
		},
		{
			path: '/:pathMatch(.*)*',
			redirect: '/properties',
		},
	],
	scrollBehavior() {
		return { top: 0 };
	},
});

router.beforeEach((to) => {
	const auth = useAuthStore();
	if (to.meta.requiresAuth && !auth.token) {
		return { name: 'login', query: { redirect: to.fullPath } };
	}
	if (to.meta.guest && auth.token) {
		return { name: 'properties' };
	}
	return true;
});

export default router;
