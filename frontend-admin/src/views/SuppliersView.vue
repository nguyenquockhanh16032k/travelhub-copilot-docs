<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  createSupplier,
  listSuppliers,
  updateSupplier,
} from '../services/suppliers'
import type { Supplier, SupplierPayload } from '../types/operations'

const suppliers = ref<Supplier[]>([])
const page = ref(1)
const total = ref(0)
const pageSize = 20
const search = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<Supplier | null>(null)
const form = ref<SupplierPayload>({ name: '', service_category: '' })

async function load(): Promise<boolean> {
  loading.value = true
  error.value = ''
  try {
    const result = await listSuppliers(page.value, pageSize, search.value)
    suppliers.value = result.items
    total.value = result.total
    return true
  } catch {
    error.value = 'Unable to load suppliers.'
    return false
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editing.value = null
  form.value = { name: '', service_category: '' }
  dialog.value = true
}

function openEdit(supplier: Supplier): void {
  editing.value = supplier
  form.value = {
    name: supplier.name,
    service_category: supplier.service_category,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  const name = form.value.name.trim()
  const serviceCategory = form.value.service_category.trim()
  if (!name || !serviceCategory) {
    error.value = 'Enter a supplier name and service category.'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  const successMessage = editing.value
    ? 'Supplier updated.'
    : 'Supplier created.'
  try {
    const payload = { name, service_category: serviceCategory }
    if (editing.value) {
      await updateSupplier(editing.value.id, payload)
    } else {
      await createSupplier(payload)
    }
    dialog.value = false
  } catch {
    error.value = 'Unable to save supplier.'
    loading.value = false
    return
  }

  const refreshed = await load()
  if (refreshed) {
    success.value = successMessage
  } else {
    error.value = 'Supplier saved, but the list could not be refreshed.'
  }
}

async function searchSuppliers(): Promise<void> {
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
      <h1 class="text-h4">Suppliers</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">
        Add supplier
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-form class="d-flex ga-2 mb-4" @submit.prevent="searchSuppliers">
      <v-text-field
        v-model="search"
        label="Search suppliers"
        density="compact"
        hide-details
      />
      <v-btn type="submit" variant="outlined">Search</v-btn>
    </v-form>

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-if="!loading && !suppliers.length" type="info" variant="tonal">
      No suppliers found.
    </v-alert>
    <v-table v-else-if="suppliers.length">
      <thead>
        <tr>
          <th>Name</th>
          <th>Service category</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="supplier in suppliers" :key="supplier.id">
          <td>{{ supplier.name }}</td>
          <td>{{ supplier.service_category }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEdit(supplier)"
            >
              Edit
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-pagination
      v-if="total > pageSize"
      v-model="page"
      :length="Math.ceil(total / pageSize)"
      :disabled="loading"
      @update:model-value="load"
    />

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editing ? 'Edit supplier' : 'Add supplier' }}
        </v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Supplier name" required />
          <v-text-field
            v-model="form.service_category"
            label="Service category"
            required
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
