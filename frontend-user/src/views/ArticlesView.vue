<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listPublicArticles, listPublicCategories } from '../services/articles'
import type { ArticleCategory, PublicArticle } from '../types/article'
import { safeCoverUrl, publishedDate } from '../utils/articlePresentation'

const route = useRoute()
const router = useRouter()
const articles = ref<PublicArticle[]>([])
const categories = ref<ArticleCategory[]>([])
const total = ref(0)
const pages = ref(0)
const loading = ref(false)
const error = ref('')
const keyword = ref('')
const selectedCategory = ref('')
const page = ref(1)
const size = 12
let requestId = 0
let controller: AbortController | null = null
let keywordTimer: ReturnType<typeof setTimeout> | undefined
const categoryOptions = computed(() => categories.value.map(c => ({ title: c.name, value: c.id })))

function queryString(value: unknown): string { return typeof value === 'string' ? value : '' }
function updateQuery(nextPage = 1, replace = false): void {
  const query = {
    ...(keyword.value.trim() ? { search: keyword.value.trim() } : {}),
    ...(selectedCategory.value ? { category: selectedCategory.value } : {}),
    ...(nextPage > 1 ? { page: String(nextPage) } : {}),
  }
  void (replace ? router.replace({ path: '/articles', query }) : router.push({ path: '/articles', query }))
}
function scheduleSearch(): void {
  if (keywordTimer) clearTimeout(keywordTimer)
  keywordTimer = setTimeout(() => updateQuery(1, true), 350)
}
function clearFilters(): void {
  if (keywordTimer) clearTimeout(keywordTimer)
  keyword.value = ''
  selectedCategory.value = ''
  updateQuery()
}
async function load(): Promise<void> {
  controller?.abort()
  controller = new AbortController()
  const ownId = ++requestId
  loading.value = true
  error.value = ''
  try {
    const result = await listPublicArticles(page.value, size, keyword.value, selectedCategory.value, controller.signal)
    if (ownId !== requestId) return
    articles.value = result.items
    total.value = result.total
    pages.value = result.pages
  } catch {
    if (ownId !== requestId || controller.signal.aborted) return
    articles.value = []
    total.value = 0
    pages.value = 0
    error.value = 'Unable to load articles. Please try again.'
  } finally {
    if (ownId === requestId) loading.value = false
  }
}
watch(() => route.query, () => {
  keyword.value = queryString(route.query.search).slice(0, 255)
  selectedCategory.value = queryString(route.query.category)
  const parsed = Number(queryString(route.query.page))
  page.value = Number.isSafeInteger(parsed) && parsed > 0 ? parsed : 1
  void load()
}, { immediate: true })
void listPublicCategories().then(value => { categories.value = value }).catch(() => { /* optional filter */ })
onBeforeUnmount(() => {
  controller?.abort()
  if (keywordTimer) clearTimeout(keywordTimer)
})
</script>

<template>
  <v-container class="py-8">
    <h1 class="text-h4 font-weight-bold mb-2">Travel stories &amp; guides</h1>
    <p class="text-medium-emphasis mb-6">Discover travel ideas, guides and updates.</p>
    <v-card variant="tonal" class="mb-6">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="6">
            <v-text-field v-model="keyword" label="Search articles" prepend-inner-icon="mdi-magnify"
              :maxlength="255" hide-details="auto" @update:model-value="scheduleSearch"
              @keyup.enter="updateQuery(1)" />
          </v-col>
          <v-col cols="12" sm="7" md="4">
            <v-select v-model="selectedCategory" :items="categoryOptions" label="Category" clearable
              hide-details="auto" @update:model-value="updateQuery(1)" />
          </v-col>
          <v-col cols="12" sm="5" md="2">
            <v-btn block variant="outlined" @click="clearFilters">Clear filters</v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
    <p aria-live="polite" class="text-body-2 mb-4">{{ total }} articles found</p>
    <v-progress-linear v-if="loading" indeterminate aria-label="Loading articles" class="mb-4" />
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append><v-btn variant="text" @click="load">Retry</v-btn></template>
    </v-alert>
    <v-row v-if="!loading && !error && articles.length">
      <v-col v-for="article in articles" :key="article.id" cols="12" sm="6" lg="4">
        <v-card height="100%" class="d-flex flex-column">
          <v-img v-if="safeCoverUrl(article.cover_image_url)"
            :src="safeCoverUrl(article.cover_image_url)" height="170" cover :alt="article.title" />
          <div v-else class="d-flex align-center justify-center bg-surface-variant" style="height: 170px">
            <v-icon size="48" icon="mdi-book-open-page-variant-outline" />
          </div>
          <v-card-item>
            <v-card-subtitle>{{ article.category?.name || 'Travel guide' }}
              <span v-if="article.published_at"> · {{ publishedDate(article.published_at) }}</span>
            </v-card-subtitle>
            <v-card-title class="text-wrap">{{ article.title }}</v-card-title>
          </v-card-item>
          <v-card-text class="flex-grow-1">
            {{ article.seo_description || article.body.slice(0, 180) }}
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="text" :to="{ name: 'article-detail', params: { slug: article.slug } }">
              Read article
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
    <v-alert v-else-if="!loading && !error" type="info" variant="tonal">
      No published articles match your search.
    </v-alert>
    <v-pagination v-if="!loading && !error && pages > 1" :model-value="page"
      :length="pages" class="mt-6" @update:model-value="updateQuery($event)" />
  </v-container>
</template>
