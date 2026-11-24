import { api } from './api'
import type {
  Customer,
  CustomerAccountPage,
  CustomerPage,
  CustomerPayload,
} from '../types/customer'

export async function listLinkableCustomerAccounts(
  customerId?: string,
  search?: string,
): Promise<CustomerAccountPage> {
  const response = await api.get<CustomerAccountPage>(
    '/customers/linkable-accounts',
    {
      params: {
        page: 1,
        size: 100,
        customer_id: customerId,
        search: search?.trim() || undefined,
      },
    },
  )
  return response.data
}

export async function listCustomers(
  page: number,
  size: number,
  search?: string,
): Promise<CustomerPage> {
  const response = await api.get<CustomerPage>('/customers', {
    params: { page, size, search: search || undefined },
  })
  return response.data
}

export async function createCustomer(
  payload: CustomerPayload,
): Promise<Customer> {
  const response = await api.post<Customer>('/customers', payload)
  return response.data
}

export async function updateCustomer(
  customerId: string,
  payload: CustomerPayload,
): Promise<Customer> {
  const response = await api.patch<Customer>(
    `/customers/${customerId}`,
    payload,
  )
  return response.data
}
