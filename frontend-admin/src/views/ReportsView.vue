<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getExpenseReport } from '../services/reports'
import type { ExpenseReportRow } from '../types/reports'

const items = ref<ExpenseReportRow[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await getExpenseReport(page.value, pageSize)
    items.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load the expense report.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Reports</h1>
    <v-alert type="info" variant="tonal" class="mb-4">
      Recorded expenses are grouped by currency and status. Values in different
      currencies are not combined, and statuses are not interpreted as paid or
      recognized costs.
    </v-alert>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
      <template #append>
        <v-btn variant="text" @click="load">Retry</v-btn>
      </template>
    </v-alert>
    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-if="!loading && !items.length" type="info" variant="tonal">
      No recorded expenses to report.
    </v-alert>
    <v-table v-else-if="items.length">
      <thead>
        <tr>
          <th>Tour</th>
          <th>Departure date</th>
          <th>Category</th>
          <th>Currency</th>
          <th>Status</th>
          <th>Recorded total</th>
          <th>Records</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in items"
          :key="`${row.departure_id}-${row.category}-${row.currency}-${row.status}-${index}`"
        >
          <td>{{ row.tour_title }}</td>
          <td>{{ row.departure_start_date }}</td>
          <td>{{ row.category }}</td>
          <td>{{ row.currency }}</td>
          <td>{{ row.status }}</td>
          <td>{{ row.total_amount }} {{ row.currency }}</td>
          <td>{{ row.expense_count }}</td>
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
  </div>
</template>
