import { api } from './api'
import type {
  TourExpense,
  TourExpensePage,
  TourExpensePayload,
} from '../types/operations'

export async function listExpenses(
  departureId: string,
  page: number,
  size: number,
): Promise<TourExpensePage> {
  const response = await api.get<TourExpensePage>(
    `/departures/${departureId}/expenses`,
    { params: { page, size } },
  )
  return response.data
}

export async function createExpense(
  departureId: string,
  payload: TourExpensePayload,
): Promise<TourExpense> {
  const response = await api.post<TourExpense>(
    `/departures/${departureId}/expenses`,
    payload,
  )
  return response.data
}

export async function updateExpense(
  departureId: string,
  expenseId: string,
  payload: TourExpensePayload,
): Promise<TourExpense> {
  const response = await api.patch<TourExpense>(
    `/departures/${departureId}/expenses/${expenseId}`,
    payload,
  )
  return response.data
}
