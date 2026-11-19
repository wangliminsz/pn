import axios from 'axios';

export const TOKEN_KEY = 'pn_mobile_token';
export const USER_KEY = 'pn_mobile_user';

const http = axios.create({
	baseURL: import.meta.env.VITE_API_BASE || '/',
	timeout: 25000,
	headers: {
		'Content-Type': 'application/json;charset=utf-8',
	},
});

http.interceptors.request.use((config) => {
	const token = localStorage.getItem(TOKEN_KEY);
	if (token) {
		config.headers.Authorization = `JWT ${token}`;
	}
	config.headers['Accept-Language'] = 'en';
	return config;
});

let redirecting = false;

function handleUnauthorized() {
	localStorage.removeItem(TOKEN_KEY);
	localStorage.removeItem(USER_KEY);
	if (redirecting) return;
	redirecting = true;
	if (!window.location.hash.startsWith('#/login')) {
		window.location.hash = '#/login';
		window.location.reload();
	}
}

http.interceptors.response.use(
	(response) => {
		const body = response.data;
		if (body && typeof body === 'object' && 'code' in body) {
			if (body.code === 2000) return body;
			if (body.code === 401) {
				handleUnauthorized();
			}
			return Promise.reject({ ...body, msg: body.msg || 'Request failed' });
		}
		return body;
	},
	(error) => {
		if (error?.response?.status === 401) {
			handleUnauthorized();
		}
		const body = error?.response?.data;
		return Promise.reject(body && typeof body === 'object' ? body : error);
	},
);

export default http;
