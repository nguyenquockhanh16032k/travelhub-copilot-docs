import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./api', () => ({
  api: {
    get: vi.fn(),
  },
}))

import { api } from './api'
import { listLinkableCustomerAccounts } from './customers'

describe('customer account linking service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads customer accounts that can be linked to a profile', async () => {
    const result = {
      items: [{ id: 'customer-user-id', email: 'customer@example.com' }],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    }
    vi.mocked(api.get).mockResolvedValue({ data: result })

    await expect(listLinkableCustomerAccounts()).resolves.toEqual(result)

    expect(api.get).toHaveBeenCalledWith('/customers/linkable-accounts', {
      params: {
        page: 1,
        size: 100,
        customer_id: undefined,
        search: undefined,
      },
    })
  })
})
