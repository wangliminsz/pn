import http from './http';

const PROPERTY_PREFIX = '/api/property/property/';

export interface PropertyListQuery {
	page?: number;
	limit?: number;
	keyword?: string;
	name?: string;
	ordering?: string;
}

export async function listProperties(query: PropertyListQuery): Promise<any> {
	return http.get(PROPERTY_PREFIX, { params: query });
}

export async function getProperty(id: number | string): Promise<any> {
	return http.get(`${PROPERTY_PREFIX}${id}/`);
}

export async function createProperty(data: Record<string, unknown>): Promise<any> {
	return http.post(PROPERTY_PREFIX, data);
}

export async function updateProperty(id: number | string, data: Record<string, unknown>): Promise<any> {
	return http.put(`${PROPERTY_PREFIX}${id}/`, data);
}

export async function deleteProperty(id: number | string): Promise<any> {
	return http.delete(`${PROPERTY_PREFIX}${id}/`);
}

export async function getOwnerOptions(): Promise<any> {
	return http.get('/api/system/user/options/');
}

export async function getLineBotOptions(): Promise<any> {
	return http.get('/api/notify/linebot/options/');
}
