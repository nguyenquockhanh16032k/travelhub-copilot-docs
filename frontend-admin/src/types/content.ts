export type ArticleStatus = 'draft' | 'published' | 'archived'

export interface Category {
  id: string
  name: string
  slug: string
}

export interface Article {
  id: string
  category_id: string | null
  author_id: string | null
  title: string
  slug: string
  body: string
  cover_image_url: string | null
  status: ArticleStatus
  seo_title: string | null
  seo_description: string | null
  published_at: string | null
  category: Category | null
}

export interface ArticlePage {
  items: Article[]
  total: number
  page: number
  size: number
  pages: number
}

export interface ArticlePayload {
  title: string
  slug: string
  body: string
  category_id: string | null
  cover_image_url: string | null
  status: ArticleStatus
  seo_title: string | null
  seo_description: string | null
}

export interface CategoryPayload {
  name: string
  slug: string
}
