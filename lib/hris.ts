export type HrisResult<T> = { success: true; data: T; message?: string } | { success: false; message: string; uncertain?: boolean };
export type HrEmployee = { id: string; code: string; name: string; position: string; outlet_id: string; user_id: string | null; phone: string | null; started_on: string; ended_on: string | null; is_active: boolean; notes: string | null; row_version: number };
export type HrRecord = { id: string; employee_id: string; employee_name: string; outlet_id: string; work_date: string; row_version: number; starts_at?: string; ends_at?: string; notes?: string | null; status?: string; clock_in?: string | null; clock_out?: string | null; reason?: string | null; source?: string; minutes?: number | null };
export type HrKind = 'employees' | 'schedules' | 'attendance';
export type HrSetup = { is_manager: boolean; permissions: string[]; self_employee: HrEmployee | null; open_attendance: HrRecord | null; workspace_key: string; outlets: { id: string; name: string; timezone: string }[]; account_admin?: boolean; shop_username?: string | null; business_name?: string | null; roles?: { id: string; name: string; scope: string; outlet_ids: string[] }[]; accounts: { id: string; name: string; username?: string | null; row_version?: number; role_id?: string | null; password_enabled?: boolean; employee_id?: string | null }[] };
export type HrFilters = { outlet_id: string; start: string; end: string; kind: HrKind; search: string; active: string; skip: number };
export type HrWorkspace = { items: (HrEmployee | HrRecord)[]; total: number; skip: number; limit: number; timezone: string; generated_at: string; scope: string; summary: { active_employees: number | null; scheduled: number | null; present: number | null; leave: number | null; open: number | null; unrecorded_started: number | null } };
export type HrPending = { path: string; method: 'POST' | 'PUT'; title: string; workspace_key?: string; password_required?: boolean; payload: Record<string, unknown> & { client_request_id: string } };

export function outletDate(value: Date | string, zone: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(value));
  const part = (name: string) => parts.find(p => p.type === name)?.value || '';
  return `${part('year')}-${part('month')}-${part('day')}`;
}
export function addDays(day: string, amount: number): string { const value = new Date(`${day}T12:00:00Z`); value.setUTCDate(value.getUTCDate() + amount); return value.toISOString().slice(0, 10); }
export function localTime(value: string | null | undefined, zone: string): string {
  if (!value) return '';
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(value));
  const p = (name: string) => parts.find(part => part.type === name)?.value || '';
  return `${p('year')}-${p('month')}-${p('day')}T${p('hour')}:${p('minute')}`;
}
export function zonedIso(value: string, zone: string): string | null {
  if (!value) return null;
  const target = Date.parse(`${value}:00Z`);
  if (!Number.isFinite(target)) throw new Error('Jam belum valid');
  let instant = target;
  for (let i = 0; i < 4; i++) { const wall = Date.parse(`${localTime(new Date(instant).toISOString(), zone)}:00Z`); instant += target - wall; }
  if (localTime(new Date(instant).toISOString(), zone) !== value) throw new Error('Jam tidak tersedia di zona waktu outlet');
  return new Date(instant).toISOString();
}
export function hrTime(value: string | null | undefined, zone: string): string {
  return value ? new Intl.DateTimeFormat('id-ID', { timeZone: zone, day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value)) : 'Belum dicatat';
}
export function hrDay(value: string): string { const day = new Date(`${value}T12:00:00Z`); return Number.isFinite(day.getTime()) ? new Intl.DateTimeFormat('id-ID', { timeZone: 'UTC', day: 'numeric', month: 'short', year: 'numeric' }).format(day) : 'Tanggal belum dipilih'; }
export function zoneLabel(zone: string): string { return ({ 'Asia/Jakarta': 'WIB', 'Asia/Makassar': 'WITA', 'Asia/Jayapura': 'WIT' } as Record<string, string>)[zone] || zone; }
