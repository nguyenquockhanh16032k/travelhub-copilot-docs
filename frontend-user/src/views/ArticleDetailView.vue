<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getPublicArticle } from '../services/articles'
import type { PublicArticle } from '../types/article'
import { publishedDate, safeCoverUrl } from '../utils/articlePresentation'

const route = useRoute()
const article = ref<PublicArticle | null>(null)
const loading = ref(false)
const error = ref('')
const originalTitle = document.title
let requestId = 0
async function load(): Promise<void> {
  const slug = route.params.slug
  const ownId = ++requestId
  article.value = null
  error.value = ''
  document.title = originalTitle
  if (typeof slug !== 'string' || !slug) { error.value = 'Article not found.'; return }
  loading.value = true
  try {
    const result = await getPublicArticle(slug)
    if (ownId !== requestId) return
    article.value = result
    document.title = (result.seo_title || result.title) + ' | TravelHub'
  } catch {
    if (ownId !== requestId) return
    error.value = 'Article not found or no longer published.'
  } finally {
    if (ownId === requestId) loading.value = false
  }
}
watch(() => route.params.slug, () => { void load() }, { immediate: true })
onBeforeUnmount(() => { requestId += 1; document.title = originalTitle })
</script>

<template>
  <v-container class="py-8" style="max-width: 900px">
    <v-btn to="/articles" variant="text" prepend-icon="mdi-arrow-left" class="mb-4">All articles</v-btn>
    <v-progress-linear v-if="loading" indeterminate aria-label="Loading article" />
    <v-alert v-else-if="error" type="warning" variant="tonal">{{ error }}</v-alert>
    <article v-else-if="article">
      <div class="text-caption text-medium-emphasis mb-3">
        {{ article.category?.name || 'Travel guide' }}
        <span v-if="article.published_at"> · {{ publishedDate(article.published_at) }}</span>
      </div>
      <h1 class="text-h3 font-weight-bold mb-5">{{ article.title }}</h1>
      <v-img v-if="safeCoverUrl(article.cover_image_url)" :src="safeCoverUrl(article.cover_image_url)"
        :alt="article.title" max-height="420" cover class="mb-6 rounded-lg" />
      <!-- Stored content is rendered as escaped plain text, never v-html. -->
      <div class="text-body-1 article-body">{{ article.body }}</div>
    </article>
  </v-container>
</template>
<style scoped>
.article-body { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.85; }
</style>
