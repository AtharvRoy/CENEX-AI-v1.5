/**
 * Authentication API client
 */

import apiClient from './client';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    full_name: string;
    tier: string;
  };
}

export async function login(credentials: LoginRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post('/api/auth/login', credentials);
  
  // Store token
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', data.access_token);
  }
  
  return data;
}

export async function register(userData: RegisterRequest): Promise<AuthResponse> {
  const { data } = await apiClient.post('/api/auth/register', userData);
  
  // Store token
  if (typeof window !== 'undefined') {
    localStorage.setItem('access_token', data.access_token);
  }
  
  return data;
}

export async function logout() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token');
  }
}

export async function getCurrentUser() {
  const { data } = await apiClient.get('/api/auth/me');
  return data;
}
