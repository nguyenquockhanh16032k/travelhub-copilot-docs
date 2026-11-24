export type Permission =
  | 'dashboard:read'
  | 'tours:read'
  | 'tours:write'
  | 'departures:read'
  | 'departures:write'
  | 'bookings:read'
  | 'bookings:create'
  | 'bookings:write'
  | 'bookings:status'
  | 'customers:read'
  | 'customers:write'
  | 'itineraries:read'
  | 'itineraries:write'
  | 'guides:read'
  | 'guides:write'
  | 'assignments:read'
  | 'assignments:write'
  | 'articles:read'
  | 'articles:write'
  | 'payments:read'
  | 'payments:write'
  | 'suppliers:read'
  | 'suppliers:write'
  | 'expenses:read'
  | 'expenses:write'
  | 'reports:read'
  | 'users:read'
  | 'users:manage_staff'
  | 'users:manage_admin'
  | 'system:settings'

const businessPermissions: readonly Permission[] = [
  'dashboard:read',
  'tours:read',
  'tours:write',
  'departures:read',
  'departures:write',
  'bookings:read',
  'bookings:create',
  'bookings:write',
  'bookings:status',
  'customers:read',
  'customers:write',
  'itineraries:read',
  'itineraries:write',
  'guides:read',
  'guides:write',
  'assignments:read',
  'assignments:write',
  'articles:read',
  'articles:write',
  'payments:read',
  'payments:write',
  'suppliers:read',
  'suppliers:write',
  'expenses:read',
  'expenses:write',
  'reports:read',
]

const adminPermissions: readonly Permission[] = [
  ...businessPermissions,
  'users:read',
  'users:manage_staff',
]

const rolePermissions: Readonly<Record<string, ReadonlySet<Permission>>> = {
  SUPER_ADMIN: new Set([
    ...adminPermissions,
    'users:manage_admin',
    'system:settings',
  ]),
  ADMIN: new Set(adminPermissions),
  STAFF: new Set([
    'dashboard:read',
    'tours:read',
    'departures:read',
    'bookings:read',
    'bookings:create',
    'bookings:write',
    'bookings:status',
    'customers:read',
    'customers:write',
    'itineraries:read',
    'guides:read',
    'assignments:read',
  ]),
}

export function hasPermission(
  roles: readonly string[] | undefined,
  permission: Permission,
): boolean {
  return Boolean(
    roles?.some((role) => rolePermissions[role]?.has(permission)),
  )
}
