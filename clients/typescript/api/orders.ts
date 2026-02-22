import { get, post } from './client';

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
    stripe_payment_link_url: string | null;
    retirement_requested: boolean;
    retirement_reference: string | null;
}

export interface CreateOrderRequest {
    line_items: {
        listing_id: string;
        quantity: number;
    }[];
    retirement_requested?: boolean;
}

export async function ordersGetMine(): Promise<Order[]> {
    return await get('/orders/');
}

export async function orderGetById(id: string): Promise<Order> {
    return await get(`/orders/${id}`);
}

export async function orderCreate(req: CreateOrderRequest): Promise<Order> {
    return await post('/orders/', req);
}

export async function orderCancel(orderId: string): Promise<Order> {
    return await post(`/orders/${orderId}/cancel`, {});
}

export async function orderConfirmPayment(paymentIntentId: string): Promise<Order> {
    return await post('/orders/confirm-payment', { payment_intent_id: paymentIntentId });
}

export async function orderMockConfirm(orderId: string): Promise<Order> {
    return await post(`/orders/${orderId}/mock-confirm`, {});
}
