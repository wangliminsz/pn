import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import { getUserInfo, login as loginApi, type LoginPayload } from '@/api/auth';
import { TOKEN_KEY, USER_KEY } from '@/api/http';

function readUser(): any {
	try {
		return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
	} catch {
		return null;
	}
}

export const useAuthStore = defineStore('auth', () => {
	const token = ref(localStorage.getItem(TOKEN_KEY) || '');
	const user = ref<any>(readUser());

	const isLoggedIn = computed(() => Boolean(token.value));
	const displayName = computed(() => user.value?.name || user.value?.username || 'Account');
	const initial = computed(() => (displayName.value || 'A').trim().charAt(0).toUpperCase());

	function setToken(value: string) {
		token.value = value;
		if (value) localStorage.setItem(TOKEN_KEY, value);
		else localStorage.removeItem(TOKEN_KEY);
	}

	function setUser(value: any) {
		user.value = value;
		if (value) localStorage.setItem(USER_KEY, JSON.stringify(value));
		else localStorage.removeItem(USER_KEY);
	}

	function clearSession() {
		token.value = '';
		user.value = null;
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(USER_KEY);
	}

	async function loadUser() {
		const res = await getUserInfo();
		setUser(res.data);
		return res.data;
	}

	async function signIn(payload: LoginPayload) {
		const res = await loginApi(payload);
		setToken(res.data.access);
		try {
			await loadUser();
		} catch (err) {
			clearSession();
			throw err;
		}
		return res.data;
	}

	async function signOut() {
		clearSession();
	}

	async function restore() {
		if (token.value && !user.value) {
			try {
				await loadUser();
			} catch {
				clearSession();
			}
		}
	}

	return {
		token,
		user,
		isLoggedIn,
		displayName,
		initial,
		setToken,
		setUser,
		clearSession,
		loadUser,
		signIn,
		signOut,
		restore,
	};
});
