import { Md5 } from 'ts-md5';
import http from './http';

export interface LoginPayload {
	username: string;
	password: string;
	captcha?: string;
	captchaKey?: string;
}

export async function getCaptcha(): Promise<any> {
	return http.get('/api/captcha/');
}

export async function login(payload: LoginPayload): Promise<any> {
	return http.post('/api/login/', {
		...payload,
		password: Md5.hashStr(payload.password),
	});
}

export async function getUserInfo(): Promise<any> {
	return http.get('/api/system/user/user_info/');
}
