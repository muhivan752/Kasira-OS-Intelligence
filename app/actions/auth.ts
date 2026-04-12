'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const API_URL = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1';
const SECURE_COOKIES = process.env.NEXT_PUBLIC_SECURE_COOKIES === 'true';

export async function sendOtp(phone: string, purpose: 'login' | 'register' = 'login') {
  try {
    const res = await fetch(`${API_URL}/auth/otp/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, purpose }),
    });
    
    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || 'Gagal mengirim OTP' };
    }
    
    return { success: true, message: 'OTP berhasil dikirim' };
  } catch (error) {
    return { success: false, message: 'Terjadi kesalahan jaringan' };
  }
}

export async function verifyOtp(phone: string, otp: string) {
  try {
    const res = await fetch(`${API_URL}/auth/otp/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, otp }),
    });
    
    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || 'OTP tidak valid' };
    }
    
    const token = data.data.access_token;
    const tenantId = data.data.tenant_id;
    const outletId = data.data.outlet_id;
    
    // Set HTTP-only cookie
    const cookieStore = await cookies();
    cookieStore.set({
      name: 'token',
      value: token,
      httpOnly: true,
      path: '/',
      secure: SECURE_COOKIES,
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });
    
    if (tenantId) {
      cookieStore.set({
        name: 'tenant_id',
        value: tenantId,
        httpOnly: true,
        path: '/',
        secure: SECURE_COOKIES,
        maxAge: 60 * 60 * 24 * 7,
      });
    }
    
    if (outletId) {
      cookieStore.set({
        name: 'outlet_id',
        value: outletId,
        httpOnly: true,
        path: '/',
        secure: SECURE_COOKIES,
        maxAge: 60 * 60 * 24 * 7,
      });
    }
    
    return { success: true };
  } catch (error) {
    return { success: false, message: 'Terjadi kesalahan jaringan' };
  }
}

export async function registerTenant(phone: string, businessName: string, ownerName: string, pin: string, otp: string, businessType: string = 'cafe', referralCode?: string) {
  try {
    const body: Record<string, string> = { phone, business_name: businessName, owner_name: ownerName, pin, otp, business_type: businessType };
    if (referralCode) body.referral_code = referralCode;
    const res = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || 'Registrasi gagal' };
    }

    const token = data.data.access_token;
    const tenantId = data.data.tenant_id;
    const outletId = data.data.outlet_id;

    const cookieStore = await cookies();
    cookieStore.set({ name: 'token', value: token, httpOnly: true, path: '/', secure: SECURE_COOKIES, maxAge: 60 * 60 * 24 * 7 });
    if (tenantId) cookieStore.set({ name: 'tenant_id', value: tenantId, httpOnly: true, path: '/', secure: SECURE_COOKIES, maxAge: 60 * 60 * 24 * 7 });
    if (outletId) cookieStore.set({ name: 'outlet_id', value: outletId, httpOnly: true, path: '/', secure: SECURE_COOKIES, maxAge: 60 * 60 * 24 * 7 });

    return { success: true };
  } catch {
    return { success: false, message: 'Terjadi kesalahan jaringan' };
  }
}

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete('token');
  cookieStore.delete('tenant_id');
  cookieStore.delete('outlet_id');
  redirect('/login');
}
