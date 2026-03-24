'use server';

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function sendOtp(phone: string) {
  try {
    const res = await fetch(`${API_URL}/auth/otp/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone }),
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
    
    // Set HTTP-only cookie
    const cookieStore = await cookies();
    cookieStore.set({
      name: 'token',
      value: token,
      httpOnly: true,
      path: '/',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 24 * 7, // 1 week
    });
    
    return { success: true };
  } catch (error) {
    return { success: false, message: 'Terjadi kesalahan jaringan' };
  }
}

export async function logout() {
  const cookieStore = await cookies();
  cookieStore.delete('token');
  redirect('/login');
}
