import { api } from './api'
import type { ArticleCategory, ArticlePage, PublicArticle } from '../types/article'

export async function listPublicArticles(
  page = 1, size = 12, search = '', categoryId = '', signal?: AbortSignal,
): Promise<ArticlePage> {
  const response = await api.get<ArticlePage>('/articles', {
    params: { page, size, search: search.trim() || undefined, category_id: categoryId || undefined },
    signal,
  })
  return response.data
}
export async function listPublicCategories(): Promise<ArticleCategory[]> {
  const response = await api.get<ArticleCategory[]>('/categories')
  return response.data
}
export async function getPublicArticle(slug: string): Promise<PublicArticle> {
  const response = await api.get<PublicArticle>('/articles/' + encodeURIComponent(slug))
  return response.data
}
