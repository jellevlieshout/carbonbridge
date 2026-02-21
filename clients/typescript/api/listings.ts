import { get, post, put, del } from './client';

export interface Listing {
    id: string;
    seller_id: string;
    registry_name: string;
    registry_project_id: string | null;
    serial_number_range: string | null;
    project_name: string;
    project_type: string;
    project_country: string | null;
    vintage_year: number | null;
    quantity_tonnes: number;
    quantity_reserved: number;
    quantity_sold: number;
    price_per_tonne_eur: number;
    verification_status: string;
    methodology: string | null;
    co_benefits: string[];
    description: string | null;
    supporting_documents: string[];
    status: string;
}

export interface ListingSearchResponse {
    listings: Listing[];
    count: number;
}

export interface ListingCreateRequest {
    registry_name: string;
    registry_project_id?: string | null;
    serial_number_range?: string | null;
    project_name: string;
    project_type?: string;
    project_country?: string | null;
    vintage_year?: number | null;
    quantity_tonnes: number;
    price_per_tonne_eur: number;
    methodology?: string | null;
    co_benefits?: string[];
    description?: string | null;
    supporting_documents?: string[];
}

export async function listingCreate(data: ListingCreateRequest): Promise<Listing> {
    return await post('/listings/', data);
}

export async function listingsGet(): Promise<ListingSearchResponse> {
    return await get('/listings/');
}

export async function listingsGetMine(): Promise<ListingSearchResponse> {
    return await get('/listings/me');
}

export async function listingGetById(id: string): Promise<Listing> {
    return await get(`/listings/${id}`);
}

export async function listingUpdate(id: string, data: Partial<Listing>): Promise<Listing> {
    return await put(`/listings/${id}`, data);
}

export async function listingDelete(id: string): Promise<void> {
    return await del(`/listings/${id}`);
}

export async function listingVerify(id: string): Promise<Listing> {
    return await post(`/listings/${id}/verify`, {});
}
