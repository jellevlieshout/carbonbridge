import { get, post } from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuctionConfig {
    auction_type: string;
    starting_price_per_tonne_eur: number;
    reserve_price_per_tonne_eur: number | null;
    buy_now_price_per_tonne_eur: number | null;
    min_bid_increment_eur: number;
    auto_extend_minutes: number;
    auto_extend_duration_minutes: number;
}

export interface Auction {
    id: string;
    seller_id: string;
    listing_id: string;
    created_by: 'human' | 'agent';
    config: AuctionConfig;
    quantity_tonnes: number;
    starts_at: string | null;
    ends_at: string | null;
    effective_ends_at: string | null;
    extensions_count: number;
    status: 'scheduled' | 'active' | 'ended' | 'settled' | 'failed' | 'cancelled' | 'bought_now';
    current_high_bid_eur: number | null;
    current_high_bidder_id: string | null;
    bid_count: number;
    winner_id: string | null;
    winning_price_per_tonne_eur: number | null;
    order_id: string | null;
    settled_at: string | null;
    // Joined listing metadata
    project_name: string | null;
    project_type: string | null;
    project_country: string | null;
    vintage_year: number | null;
    co_benefits: string[];
    verification_status: string | null;
}

export interface Bid {
    id: string;
    auction_id: string;
    bidder_id: string;
    amount_per_tonne_eur: number;
    total_eur: number;
    placed_at: string | null;
    placed_by: 'human' | 'agent';
    status: 'active' | 'outbid' | 'won' | 'lost' | 'buy_now';
    is_buy_now: boolean;
}

export interface CreateAuctionRequest {
    listing_id: string;
    starting_price_per_tonne_eur: number;
    reserve_price_per_tonne_eur?: number | null;
    buy_now_price_per_tonne_eur?: number | null;
    min_bid_increment_eur?: number;
    quantity_tonnes: number;
    duration_hours: number;
    auto_extend_minutes?: number;
}

export interface PlaceBidRequest {
    amount_per_tonne_eur: number;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function auctionsSearch(params?: Record<string, string>): Promise<Auction[]> {
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    return await get(`/auctions/${query}`);
}

export async function auctionGetById(id: string): Promise<Auction> {
    return await get(`/auctions/${id}`);
}

export async function auctionGetBids(id: string): Promise<Bid[]> {
    return await get(`/auctions/${id}/bids`);
}

export async function auctionCreate(data: CreateAuctionRequest): Promise<Auction> {
    return await post('/auctions/', data);
}

export async function auctionPlaceBid(auctionId: string, data: PlaceBidRequest): Promise<Bid> {
    return await post(`/auctions/${auctionId}/bid`, data);
}

export async function auctionBuyNow(auctionId: string): Promise<Bid> {
    return await post(`/auctions/${auctionId}/buy-now`, {});
}

export async function auctionCancel(auctionId: string): Promise<Auction> {
    return await post(`/auctions/${auctionId}/cancel`, {});
}

export async function auctionsGetMine(): Promise<Auction[]> {
    return await get('/auctions/me');
}
