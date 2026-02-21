import { get } from './client';

export interface OrderLineItem {
    listing_id: string;
    quantity: number;
    price_per_tonne: number;
    subtotal: number;
}

export interface Order {
    id: string;
    buyer_id: string;
    status: string;
    line_items: OrderLineItem[];
    total_eur: number;
    stripe_payment_intent_id: string | null;
    stripe_client_secret: string | null;
    retirement_requested: boolean;
}

export async function ordersGetMine(): Promise<Order[]> {
    return await get('/orders/');
}

export async function orderGetById(id: string): Promise<Order> {
    return await get(`/orders/${id}`);
}
