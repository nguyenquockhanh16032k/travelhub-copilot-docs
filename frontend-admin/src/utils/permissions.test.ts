import { describe, expect, it } from 'vitest'

import { hasPermission } from './permissions'

describe('role permissions', () => {
  it('grants STAFF only the approved operational screens and actions', () => {
    const roles = ['STAFF']

    expect(hasPermission(roles, 'dashboard:read')).toBe(true)
    expect(hasPermission(roles, 'bookings:create')).toBe(true)
    expect(hasPermission(roles, 'bookings:write')).toBe(true)
    expect(hasPermission(roles, 'customers:write')).toBe(true)
    expect(hasPermission(roles, 'assignments:read')).toBe(true)
    expect(hasPermission(roles, 'tours:write')).toBe(false)
    expect(hasPermission(roles, 'itineraries:write')).toBe(false)
    expect(hasPermission(roles, 'articles:read')).toBe(false)
    expect(hasPermission(roles, 'payments:read')).toBe(false)
    expect(hasPermission(roles, 'expenses:read')).toBe(false)
    expect(hasPermission(roles, 'reports:read')).toBe(false)
    expect(hasPermission(roles, 'users:read')).toBe(false)
  })

  it('preserves full business access for ADMIN and SUPER_ADMIN', () => {
    for (const role of ['ADMIN', 'SUPER_ADMIN']) {
      expect(hasPermission([role], 'tours:write')).toBe(true)
      expect(hasPermission([role], 'payments:read')).toBe(true)
      expect(hasPermission([role], 'reports:read')).toBe(true)
    }

    expect(hasPermission(['ADMIN'], 'users:manage_staff')).toBe(true)
    expect(hasPermission(['ADMIN'], 'users:manage_admin')).toBe(false)
    expect(hasPermission(['SUPER_ADMIN'], 'users:manage_admin')).toBe(true)
  })
})
