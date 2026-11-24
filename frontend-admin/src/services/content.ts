import { api } from './api'
import type {
  Article,
  ArticlePage,
  ArticlePayload,
  Category,
  CategoryPayload,
} from '../types/content'

export async function listCategories(): Promise<Category[]> {
  const response = await api.get<Category[]>('/categories')
  return response.data
}

export async function createCategory(
  payload: CategoryPayload,
): Promise<Category> {
  const response = await api.post<Category>('/categories', payload)
  return response.data
}

export async function listArticles(
  page: number,
  size: number,
  search?: string,
): Promise<ArticlePage> {
  const response = await api.get<ArticlePage>('/admin/articles', {
    params: { page, size, search: search || undefined },
  })
  return response.data
}

export async function createArticle(payload: ArticlePayload): Promise<Article> {
  const response = await api.post<Article>('/articles', payload)
  return response.data
}

export async function updateArticle(
  articleId: string,
  payload: ArticlePayload,
): Promise<Article> {
  const response = await api.patch<Article>(
    `/articles/${articleId}`,
    payload,
  )
  return response.data
}
