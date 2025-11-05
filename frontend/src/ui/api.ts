import axios from 'axios'
const ENV = (import.meta as any).env as { VITE_API_URL?: string } | undefined
export const API = ENV?.VITE_API_URL ?? 'http://localhost:8000'
export function authHeaders() {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}
export const http = axios.create({ baseURL: API })
