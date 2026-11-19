import * as process from 'process';
import fs from 'fs';

// 版本升级提示已停用(mute): 保留 exported 函数签名, 避免改动调用方。
// 不再校验前端版本、不再强制刷新、不再弹升级提示。

// 是否显示升级提示信息框
const IS_SHOW_UPGRADE_SESSION_KEY = 'isShowUpgrade';
const VERSION_KEY = 'DVADMIN3_VERSION';
const VERSION_FILE_NAME = 'version-build';

const META_ENV = import.meta.env;

export function showUpgrade() {
	return;
}

// 生产环境前端版本校验(已停用)
export async function checkVersion() {
	return;
}

export function generateVersionFile() {
	// 生成版本文件到public目录下version文件中
	const package_version = META_ENV?.npm_package_version ?? process.env?.npm_package_version;

	const version = `${package_version}.${new Date().getTime()}`;
	fs.writeFileSync(`public/${VERSION_FILE_NAME}`, version);
}