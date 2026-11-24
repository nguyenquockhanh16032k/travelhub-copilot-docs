import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'

vi.mock('./api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}))

import { api } from './api'
import { uploadTourFile } from './tourBulk'

describe('tour CSV/XLSX import', () => {
  beforeEach(() => vi.clearAllMocks())

  it('previews before any commit and sends a multipart file', async () => {
    const preview = { preview: true, valid_rows: 1, error_rows: 0, errors: [], created: 0 }
    vi.mocked(api.post).mockResolvedValue({ data: preview } as AxiosResponse)
    const file = new File(
      ['title,slug,description,duration_days,destination\nMy Tour,my-tour,,2,Hue\n'],
      'tours.csv',
      { type: 'text/csv' },
    )
    await expect(uploadTourFile(file, true)).resolves.toEqual(preview)
    expect(api.post).toHaveBeenCalledWith(
      '/admin/tours/bulk/import',
      expect.any(FormData),
      { params: { preview: true } },
    )
    const form = vi.mocked(api.post).mock.calls[0]?.[1] as FormData
    expect((form.get('file') as File).name).toBe('tours.csv')
  })

  it('sends explicit commit request', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { preview: false, valid_rows: 1, error_rows: 0, errors: [], created: 1 },
    } as AxiosResponse)
    const file = new File(['dummy'], 'tours.xlsx')
    await uploadTourFile(file, false)
    expect(api.post).toHaveBeenCalledWith(
      '/admin/tours/bulk/import',
      expect.any(FormData),
      { params: { preview: false } },
    )
  })
})
