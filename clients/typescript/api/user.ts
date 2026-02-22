import { get, put } from './client';

export interface OnboardingData {
    role: 'buyer' | 'seller' | 'both';
    company_name: string;
    sector?: string;
    country?: string;
    company_size_employees?: number;
    buyer_profile?: {
        annual_co2_tonnes_estimate?: number;
        primary_offset_motivation?: 'compliance' | 'esg_reporting' | 'brand' | 'personal';
        preferred_project_types?: string[];
        preferred_regions?: string[];
        budget_per_tonne_max_eur?: number;
    };
}

export async function userDataGet(): Promise<any> {
    return await get('/user_data');
}

export async function userOnboardingSubmit(data: OnboardingData): Promise<any> {
    return await put('/user_data/onboarding', data);
}