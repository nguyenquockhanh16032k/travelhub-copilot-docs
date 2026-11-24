import { api } from './api'
import type { ExpenseReportPage } from '../types/reports'

export async function getExpenseReport(
  page: number,
  size: number,
): Promise<ExpenseReportPage> {
  const response = await api.get<ExpenseReportPage>('/reports/expenses', {
    params: { page, size },
  })
  return response.data
}
