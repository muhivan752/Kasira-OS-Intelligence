'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import type { OtpChannel } from '@/lib/brand';

const API_URL = (process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
const SECURE_COOKIES = process.env.NEXT_PUBLIC_SECURE_COOKIES === 'true';
type Result = { success: boolean; message?: string; code?: string; data?: any };
export type SendOtpResult = { success: true; channel: OtpChannel } | { success: false; message: string; code?: string };

async function authRequest(path: string, body?: unknown): Promise<Result> {
  try {
    const response = await fetch(`${API_URL}/auth/${path}`, {
      method: body ? 'POST' : 'GET', cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(15000),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.detail;
      return { success: false, message: typeof detail === 'string' ? detail : detail?.message || 'Permintaan gagal. Coba lagi.', code: detail?.code };
    }
    return { success: true, data: payload.data };
  } catch {
    return { success: false, message: 'Koneksi terputus. Periksa internet lalu coba lagi.' };
  }
}

async function saveSession(data: any) {
  const store = await cookies();
  for (const [name, value] of Object.entries({ token: data.access_token, tenant_id: data.tenant_id, outlet_id: data.outlet_id })) {
    if (typeof value === 'string' && value) {
      store.set({ name, value, httpOnly: true, sameSite: 'lax', secure: SECURE_COOKIES, path: '/', maxAge: 60 * 60 * 24 * 7 });
    } else { store.delete(name); }
  }
}

export async function getAuthProviders() { return authRequest('providers'); }
export async function sendOtp(phone: string, purpose: 'login' | 'register' | 'google' = 'login', channel: OtpChannel = 'sefrekuensi', idToken?: string): Promise<SendOtpResult> {
  const result = await authRequest('otp/send', { phone, purpose, channel, ...(idToken ? { id_token: idToken } : {}) });
  return result.success ? { success: true, channel: result.data.channel === 'sefrekuensi' ? 'sefrekuensi' : 'whatsapp' }
    : { success: false, message: result.message || 'Kode belum terkirim.', code: result.code };
}
export async function verifyOtp(phone: string, otp: string) {
  const result = await authRequest('otp/verify', { phone, otp });
  if (result.success) await saveSession(result.data);
  return { success: result.success, message: result.message };
}
export async function verifyRegistrationOtp(phone: string, otp: string) { return authRequest('otp/register/verify', { phone, otp }); }
export async function signInGoogle(idToken: string) {
  const result = await authRequest('google', { id_token: idToken });
  if (result.success && result.data.registered) await saveSession(result.data);
  return result;
}
export async function verifyGooglePhone(idToken: string, phone: string, otp: string) {
  const result = await authRequest('google/phone', { id_token: idToken, phone, otp });
  if (result.success && result.data.registered) await saveSession(result.data);
  return result;
}
export async function registerTenant(phone: string, businessName: string, ownerName: string, pin: string, otp: string, businessType = 'cafe', referralCode?: string, googleProof?: string, otpProof?: string) {
  const result = await authRequest('register', {
    phone, business_name: businessName, owner_name: ownerName, pin, business_type: businessType,
    ...(otp ? { otp } : {}), ...(referralCode ? { referral_code: referralCode } : {}),
    ...(googleProof ? { google_proof: googleProof } : {}), ...(otpProof ? { otp_proof: otpProof } : {}),
  });
  if (result.success) await saveSession(result.data);
  return { success: result.success, message: result.message };
}
export async function logout() {
  const store = await cookies();
  for (const name of ['token', 'tenant_id', 'outlet_id']) store.delete(name);
  redirect('/login');
}
