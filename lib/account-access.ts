export function validAccountAccess(value: any): boolean {
  return Boolean(value && ['owner', 'legacy', 'managed'].includes(value.enforcement_mode)
    && Array.isArray(value.permissions) && value.permissions.every((permission: unknown) => typeof permission === 'string')
    && Array.isArray(value.outlets) && value.outlets.every((outlet: any) => outlet && typeof outlet.id === 'string' && typeof outlet.name === 'string')
    && (value.enforcement_mode !== 'managed' || ['outlet', 'brand', 'tenant'].includes(value.scope)));
}
