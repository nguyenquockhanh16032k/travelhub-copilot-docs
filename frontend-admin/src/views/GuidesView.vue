<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import { createGuide, listGuides, updateGuide } from '../services/guides'
import type { Guide, GuidePayload } from '../types/operations'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const canManageGuides = computed(() =>
  hasPermission(auth.user?.roles, 'guides:write'),
)
const guides = ref<Guide[]>([])
const page = ref(1)
const size = 20
const total = ref(0)
const search = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<Guide | null>(null)
const form = ref<GuidePayload>({
  full_name: '',
  email: null,
  phone: null,
  user_id: null,
})

async function load(): Promise<boolean> {
  loading.value = true
  error.value = ''
  try {
    const result = await listGuides(page.value, size, search.value)
    guides.value = result.items
    total.value = result.total
    return true
  } catch {
    error.value = 'Unable to load guides.'
    return false
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.value = { full_name: '', email: null, phone: null, user_id: null }
  dialog.value = true
}

function openEdit(guide: Guide): void {
  editing.value = guide
  form.value = {
    full_name: guide.full_name,
    email: guide.email,
    phone: guide.phone,
    user_id: guide.user_id,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  if (!form.value.full_name.trim()) {
    error.value = 'Enter a guide name.'
    return
  }
  loading.value = true
  error.value = ''
  success.value = ''
  const successMessage = editing.value ? 'Guide updated.' : 'Guide created.'
  try {
    const payload = {
      ...form.value,
      full_name: form.value.full_name.trim(),
      email: form.value.email?.trim() || null,
      phone: form.value.phone?.trim() || null,
      user_id: form.value.user_id?.trim() || null,
    }
    if (editing.value) {
      await updateGuide(editing.value.id, payload)
    } else {
      await createGuide(payload)
    }
    dialog.value = false
  } catch {
    error.value = 'Unable to save guide. Check the contact details and user ID.'
    loading.value = false
    return
  }
  const refreshed = await load()
  if (refreshed) {
    success.value = successMessage
  } else {
    error.value = 'Guide saved, but the list could not be refreshed.'
  }
}

async function searchGuides(): Promise<void> {
  page.value = 1
  await load()
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Guides</h1>
      <v-spacer />
      <v-btn
        v-if="canManageGuides"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreate"
      >
        Add guide
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-form class="d-flex ga-2 mb-4" @submit.prevent="searchGuides">
      <v-text-field
        v-model="search"
        label="Search guides"
        density="compact"
        hide-details
      />
      <v-btn type="submit" variant="outlined">Search</v-btn>
    </v-form>

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-if="!loading && !guides.length" type="info" variant="tonal">
      No guides found.
    </v-alert>
    <v-table v-else-if="guides.length">
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Phone</th>
          <th>Linked user</th>
          <th v-if="canManageGuides" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="guide in guides" :key="guide.id">
          <td>{{ guide.full_name }}</td>
          <td>{{ guide.email || '—' }}</td>
          <td>{{ guide.phone || '—' }}</td>
          <td>{{ guide.user_id || '—' }}</td>
          <td v-if="canManageGuides">
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEdit(guide)"
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

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>{{ editing ? 'Edit guide' : 'Add guide' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.full_name" label="Full name" required />
          <v-text-field v-model="form.email" label="Email" type="email" />
          <v-text-field v-model="form.phone" label="Phone" />
          <v-text-field
            v-model="form.user_id"
            label="Linked user ID (optional)"
            hint="Use an existing user UUID, or leave blank."
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submit">
            Save
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
