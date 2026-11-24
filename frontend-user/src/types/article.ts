export interface ArticleCategory { id: string; name: string; slug: string }
export interface PublicArticle {
  id: string
  title: string
  slug: string
  body: string
  cover_image_url: string | null
  category_id: string | null
  category: ArticleCategory | null
  published_at: string | null
  seo_title: string | null
  seo_description: string | null
}
export interface ArticlePage {
  items: PublicArticle[]
  total: number
  page: number
  size: number
  pages: number
}
