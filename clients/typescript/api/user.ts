import { get, post } from './client';

export async function userDataGet(): Promise<any> {
    return await get('/user_data');
}