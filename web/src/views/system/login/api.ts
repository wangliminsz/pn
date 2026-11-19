import { request } from "/@/utils/service";

export function getCaptcha() {
    return request({
        url: '/api/captcha/',
        method: 'get',
    });
}
export function login(params: object) {
    return request({
        url: '/api/login/',
        method: 'post',
        data: params
    });
}

export function loginChangePwd(data: object) {
    return request({
        url: '/api/system/user/login_change_password/',
        method: 'post',
        data: data
    });
}

export function getUserInfo() {
    return request({
        url: '/api/system/user/user_info/',
        method: 'get',
    });
}

export function getBackends() {
    return request({
        url: '/api/dvadmin3_social_oauth2/backend/get_login_backend/',
        method: 'get',
    });
}
// ---------------- 忘记密码(自助重置, 免登录) ----------------
export function SendResetEmail(email: string) {
    return request({
        url: '/api/system/user_reset/send/',
        method: 'post',
        data: { email },
    });
}

export function ConfirmReset(token: string, password: string) {
    return request({
        url: '/api/system/user_reset/confirm/',
        method: 'post',
        data: { token, password },
    });
}
