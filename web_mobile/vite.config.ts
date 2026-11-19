import vue from '@vitejs/plugin-vue';
import { defineConfig, loadEnv } from 'vite';
import { resolve } from 'path';

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd());
	return {
		base: './',
		plugins: [vue()],
		resolve: {
			alias: {
				'@': resolve(__dirname, 'src'),
			},
		},
		server: {
			host: '0.0.0.0',
			port: 8090,
			open: false,
			proxy: {
				'/api': {
					target: env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
					changeOrigin: true,
				},
			},
		},
		build: {
			outDir: 'dist',
			chunkSizeWarningLimit: 900,
		},
	};
});
