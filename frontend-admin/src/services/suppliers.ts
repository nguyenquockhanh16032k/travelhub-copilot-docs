import { api } from './api'
import type {
  Supplier,
  SupplierPage,
  SupplierPayload,
} from '../types/operations'

export async function listSuppliers(
  page: number,
  size: number,
  search?: string,
): Promise<SupplierPage> {
  const response = await api.get<SupplierPage>('/suppliers', {
    params: { page, size, search: search || undefined },
  })
  return response.data
}

export async function createSupplier(
  payload: SupplierPayload,
): Promise<Supplier> {
  const response = await api.post<Supplier>('/suppliers', payload)
  return response.data
}

export async function updateSupplier(
  supplierId: string,
  payload: SupplierPayload,
): Promise<Supplier> {
  const response = await api.patch<Supplier>(
    `/suppliers/${supplierId}`,
    payload,
  )
  return response.data
}
