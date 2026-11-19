import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
import { defineConfig, loadEnv, ConfigEnv } from 'vite';
import vueSetupExtend from 'vite-plugin-vue-setup-extend';
// import vueJsx from '@vitejs/plugin-vue-jsx'
import { generateVersionFile } from "/@/utils/upgrade";

const pathResolve = (dir: string) => {
	return resolve(__dirname, '.', dir);
};

const alias: Record<string, string> = {
	'/@': pathResolve('./src/'),
	'@great-dream': pathResolve('./node_modules/@great-dream/'),
	'@views': pathResolve('./src/views'),
	'vue-i18n': 'vue-i18n/dist/vue-i18n.cjs.js',
	'@dvaformflow':pathResolve('./src/viwes/plugins/dvaadmin_form_flow/src/')
};

const viteConfig = defineConfig((mode: ConfigEnv) => {
	const env = loadEnv(mode.mode, process.cwd());
	// 当Vite构建时，生成版本文件
	generateVersionFile()
	return {
		plugins: [vue(), /* vueJsx(), */ vueSetupExtend()],
		root: process.cwd(),
		resolve: { alias },
		base: mode.command === 'serve' ? './' : env.VITE_PUBLIC_PATH,
		optimizeDeps: {
			include: ['element-plus/es/locale/lang/zh-cn', 'element-plus/es/locale/lang/en', 'element-plus/es/locale/lang/zh-tw', '@vxe-ui/core', 'dom-zindex', 'vxe-table'],
		},
		server: {
			host: '0.0.0.0',
			port: env.VITE_PORT as unknown as number,
			open: false,
			hmr: true,
			proxy: {
				'/gitee': {
					target: 'https://gitee.com',
					ws: true,
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/gitee/, ''),
				},
			},
		},
		build: {
			outDir: env.VITE_DIST_PATH || 'dist',
			chunkSizeWarningLimit: 1500,
			rollupOptions: {
				output: {
					entryFileNames: `assets/[name].[hash].js`,
					chunkFileNames: `assets/[name].[hash].js`,
					assetFileNames: `assets/[name].[hash].[ext]`,
					compact: true,
					// 按包名拆 chunk(比对象写法更细: element-plus/vxe/fast-crud 等各自独立)
					manualChunks(id) {
						if (id.includes('node_modules')) {
							if (id.includes('/echarts/') || id.includes('/zrender/')) return 'echarts';
							if (id.includes('/element-plus/')) return 'elem';
							if (id.includes('/@element-plus/icons-vue/')) return 'elem-icons';
							if (id.includes('/@vueuse/') || id.includes('/vueuse/')) return 'vueuse';
							if (id.includes('/vxe-table/') || id.includes('/vxe-pc-ui/')) return 'vxe';
							if (id.includes('/fast-crud/')) return 'fastcrud';
							if (id.includes('/axios/')) return 'axios';
							if (id.includes('/dayjs/')) return 'dayjs';
							if (id.includes('/lodash/')) return 'lodash';
							if (id.includes('/vue-router/') || id.includes('/pinia/') || id.includes('/vue/')) return 'vue';
							// 其余 node_modules 交给 Vite 自动拆(动态 import 的库自动独立成 chunk)
						}
						return undefined;
					},
				},
			},
		},
		css: { preprocessorOptions: { css: { charset: false } } },
		define: {
			__VUE_I18N_LEGACY_API__: JSON.stringify(false),
			__VUE_I18N_FULL_INSTALL__: JSON.stringify(false),
			__INTLIFY_PROD_DEVTOOLS__: JSON.stringify(false),
			__VERSION__: JSON.stringify(process.env.npm_package_version),
		},
	};
});

export default viteConfig;
