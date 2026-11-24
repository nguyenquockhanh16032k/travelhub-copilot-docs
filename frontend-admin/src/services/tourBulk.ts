import { api } from './api'

export type BulkFormat = 'csv' | 'xlsx'

export interface TourImportIssue {
  row: number
  slug: string
  errors: string[]
}

export interface TourImportResult {
  preview: boolean
  valid_rows: number
  error_rows: number
  errors: TourImportIssue[]
  created: number
}

function fileNameFromHeader(header: string | undefined, fallback: string): string {
  const match = header?.match(/filename="([^"]+)"/i)
  return match?.[1] || fallback
}

export async function downloadTourFile(
  format: BulkFormat,
  template = false,
): Promise<void> {
  const response = await api.get<Blob>('/admin/tours/bulk/export', {
    params: { format, template },
    responseType: 'blob',
  })
  const blob = response.data
  const fallback = 'travelhub_tours_' + (template ? 'template' : 'export') + '.' + format
  const name = fileNameFromHeader(response.headers['content-disposition'], fallback)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  URL.revokeObjectURL(url)
}

export async function uploadTourFile(
  file: File,
  preview = true,
): Promise<TourImportResult> {
  const form = new FormData()
  form.append('file', file, file.name)
  const response = await api.post<TourImportResult>('/admin/tours/bulk/import', form, {
    params: { preview },
  })
  return response.data
}
