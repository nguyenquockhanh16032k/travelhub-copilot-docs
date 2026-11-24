import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AxiosResponse } from 'axios'
vi.mock('./api', () => ({ api: { get: vi.fn() } }))
import { api } from './api'
import { getPublicArticle, listPublicArticles, listPublicCategories } from './articles'
import type { ArticlePage } from '../types/article'

describe('public articles API', () => {
  beforeEach(() => vi.clearAllMocks())
  it('filters and paginates on backend', async () => {
    const page: ArticlePage = { items: [], total: 0, page: 2, size: 12, pages: 0 }
    vi.mocked(api.get).mockResolvedValue({ data: page } as AxiosResponse<ArticlePage>)
    const signal = new AbortController().signal
    await expect(listPublicArticles(2, 12, ' coast ', 'category-id', signal)).resolves.toEqual(page)
    expect(api.get).toHaveBeenCalledWith('/articles', {
      params: { page: 2, size: 12, search: 'coast', category_id: 'category-id' }, signal,
    })
  })
  it('encodes article slug', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { title: 'Story' } } as AxiosResponse)
    await getPublicArticle('a/b')
    expect(api.get).toHaveBeenCalledWith('/articles/a%2Fb')
  })
  it('fetches categories', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] } as AxiosResponse)
    await expect(listPublicCategories()).resolves.toEqual([])
    expect(api.get).toHaveBeenCalledWith('/categories')
  })
})
