export function errorMessage(err: unknown, fallback = 'Something went wrong'): string {
	const anyErr = err as any;
	const raw = anyErr?.response?.data?.msg ?? anyErr?.data?.msg ?? anyErr?.msg ?? anyErr?.message ?? fallback;
	if (Array.isArray(raw)) return raw.join(' ');
	if (typeof raw === 'string' && raw.trim()) return raw;
	if (raw && typeof raw === 'object') {
		const first = Object.values(raw)[0];
		if (Array.isArray(first)) return String(first[0]);
		if (first) return String(first);
	}
	return fallback;
}
