<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  createArticle,
  createCategory,
  listArticles,
  listCategories,
  updateArticle,
} from '../services/content'
import type {
  Article,
  ArticlePayload,
  ArticleStatus,
  Category,
} from '../types/content'

const articles = ref<Article[]>([])
const categories = ref<Category[]>([])
const page = ref(1)
const size = 20
const total = ref(0)
const search = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const categoryDialog = ref(false)
const editing = ref<Article | null>(null)
const form = ref<ArticlePayload>({
  title: '',
  slug: '',
  body: '',
  category_id: null,
  cover_image_url: null,
  status: 'draft',
  seo_title: null,
  seo_description: null,
})
const categoryForm = ref({ name: '', slug: '' })
const statuses: ArticleStatus[] = ['draft', 'published', 'archived']

async function loadCategories(): Promise<void> {
  categories.value = await listCategories()
}

async function load(): Promise<boolean> {
  loading.value = true
  error.value = ''
  try {
    const result = await listArticles(page.value, size, search.value)
    articles.value = result.items
    total.value = result.total
    return true
  } catch {
    error.value = 'Unable to load articles.'
    return false
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.value = {
    title: '',
    slug: '',
    body: '',
    category_id: null,
    cover_image_url: null,
    status: 'draft',
    seo_title: null,
    seo_description: null,
  }
  dialog.value = true
}

function openEdit(article: Article): void {
  editing.value = article
  form.value = {
    title: article.title,
    slug: article.slug,
    body: article.body,
    category_id: article.category_id,
    cover_image_url: article.cover_image_url,
    status: article.status,
    seo_title: article.seo_title,
    seo_description: article.seo_description,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  if (
    !form.value.title.trim() ||
    !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(form.value.slug.trim()) ||
    !form.value.body.trim()
  ) {
    error.value = 'Enter a title, valid slug, and article body.'
    return
  }
  loading.value = true
  error.value = ''
  success.value = ''
  const successMessage = editing.value ? 'Article updated.' : 'Article created.'
  const payload = {
    ...form.value,
    title: form.value.title.trim(),
    slug: form.value.slug.trim(),
    body: form.value.body,
    cover_image_url: form.value.cover_image_url?.trim() || null,
    seo_title: form.value.seo_title?.trim() || null,
    seo_description: form.value.seo_description?.trim() || null,
  }
  try {
    if (editing.value) {
      await updateArticle(editing.value.id, payload)
    } else {
      await createArticle(payload)
    }
    dialog.value = false
  } catch {
    error.value = 'Unable to save article. Check the category and slug.'
    loading.value = false
    return
  }
  const refreshed = await load()
  if (refreshed) success.value = successMessage
  else error.value = 'Article saved, but the list could not be refreshed.'
}

async function submitCategory(): Promise<void> {
  const name = categoryForm.value.name.trim()
  const slug = categoryForm.value.slug.trim()
  if (!name || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
    error.value = 'Enter a category name and valid slug.'
    return
  }
  try {
    await createCategory({ name, slug })
    await loadCategories()
    categoryDialog.value = false
    categoryForm.value = { name: '', slug: '' }
    success.value = 'Category created.'
  } catch {
    error.value = 'Unable to create category.'
  }
}

async function searchArticles(): Promise<void> {
  page.value = 1
  await load()
}

onMounted(() => {
  void Promise.all([load(), loadCategories()])
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Articles</h1>
      <v-spacer />
      <v-btn
        variant="outlined"
        prepend-icon="mdi-tag-plus"
        class="mr-2"
        @click="categoryDialog = true"
      >
        Add category
      </v-btn>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">
        Create article
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-form class="d-flex ga-2 mb-4" @submit.prevent="searchArticles">
      <v-text-field
        v-model="search"
        label="Search articles"
        density="compact"
        hide-details
      />
      <v-btn type="submit" variant="outlined">Search</v-btn>
    </v-form>

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-if="!loading && !articles.length" type="info" variant="tonal">
      No articles found.
    </v-alert>
    <v-table v-else-if="articles.length">
      <thead>
        <tr>
          <th>Title</th>
          <th>Category</th>
          <th>Status</th>
          <th>Published</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="article in articles" :key="article.id">
          <td>{{ article.title }}</td>
          <td>{{ article.category?.name || '—' }}</td>
          <td>{{ article.status }}</td>
          <td>{{ article.published_at || '—' }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEdit(article)"
            >
              Edit
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-pagination
      v-if="total > size"
      v-model="page"
      :length="Math.ceil(total / size)"
      :disabled="loading"
      @update:model-value="load"
    />

    <v-dialog v-model="dialog" max-width="800">
      <v-card>
        <v-card-title>{{ editing ? 'Edit article' : 'Create article' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.title" label="Title" required />
          <v-text-field v-model="form.slug" label="Slug" required />
          <v-select
            v-model="form.category_id"
            :items="categories"
            item-title="name"
            item-value="id"
            label="Category"
            clearable
          />
          <v-select
            v-model="form.status"
            :items="statuses"
            label="Status"
          />
          <v-text-field v-model="form.cover_image_url" label="Cover image URL" />
          <v-text-field v-model="form.seo_title" label="SEO title" />
          <v-textarea v-model="form.seo_description" label="SEO description" rows="2" />
          <v-textarea v-model="form.body" label="Article body" rows="10" required />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submit">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="categoryDialog" max-width="500">
      <v-card>
        <v-card-title>Add category</v-card-title>
        <v-card-text>
          <v-text-field v-model="categoryForm.name" label="Name" required />
          <v-text-field v-model="categoryForm.slug" label="Slug" required />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="categoryDialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitCategory">Save</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
