<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { createExpense, listExpenses, updateExpense } from '../services/expenses'
import { listAdminDepartures } from '../services/departures'
import { listSuppliers } from '../services/suppliers'
import type { AdminDeparture } from '../types/catalog'
import type {
  Supplier,
  TourExpense,
  TourExpensePayload,
} from '../types/operations'

const departures = ref<AdminDeparture[]>([])
const suppliers = ref<Supplier[]>([])
const expenses = ref<TourExpense[]>([])
const selectedDeparture = ref<AdminDeparture | null>(null)
const departurePage = ref(1)
const departureTotal = ref(0)
const expensePage = ref(1)
const expenseTotal = ref(0)
const pageSize = 20
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<TourExpense | null>(null)
const form = ref<TourExpensePayload>({
  supplier_id: null,
  category: '',
  amount: '',
  currency: '',
  status: '',
  note: null,
})

async function loadDepartures(): Promise<void> {
  const result = await listAdminDepartures(departurePage.value, pageSize)
  departures.value = result.items
  departureTotal.value = result.total
}

async function loadExpenses(): Promise<void> {
  if (!selectedDeparture.value) {
    expenses.value = []
    expenseTotal.value = 0
    return
  }
  const result = await listExpenses(
    selectedDeparture.value.id,
    expensePage.value,
    pageSize,
  )
  expenses.value = result.items
  expenseTotal.value = result.total
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadDepartures(), loadExpenses()])
  } catch {
    error.value = 'Unable to load departures or expenses.'
  } finally {
    loading.value = false
  }
}

async function selectDeparture(departure: AdminDeparture): Promise<void> {
  selectedDeparture.value = departure
  expensePage.value = 1
  loading.value = true
  error.value = ''
  try {
    await loadExpenses()
  } catch {
    expenses.value = []
    expenseTotal.value = 0
    error.value = 'Unable to load expenses for this departure.'
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  if (!selectedDeparture.value) return
  editing.value = null
  form.value = {
    supplier_id: null,
    category: '',
    amount: '',
    currency: selectedDeparture.value.currency,
    status: '',
    note: null,
  }
  dialog.value = true
}

function openEdit(expense: TourExpense): void {
  editing.value = expense
  form.value = {
    supplier_id: expense.supplier_id,
    category: expense.category,
    amount: expense.amount,
    currency: expense.currency,
    status: expense.status,
    note: expense.note,
  }
  if (
    expense.supplier &&
    !suppliers.value.some((supplier) => supplier.id === expense.supplier_id)
  ) {
    suppliers.value = [...suppliers.value, expense.supplier]
  }
  dialog.value = true
}

function isValidAmount(value: string): boolean {
  const match = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(value.trim())
  if (!match) return false
  const minorUnits =
    BigInt(match[1]) * 100n + BigInt((match[2] ?? '').padEnd(2, '0'))
  return minorUnits > 0n
}

async function submit(): Promise<void> {
  if (
    !selectedDeparture.value ||
    !form.value.category.trim() ||
    !isValidAmount(form.value.amount) ||
    !/^[A-Za-z]{3}$/.test(form.value.currency.trim()) ||
    !form.value.status.trim()
  ) {
    error.value =
      'Enter a category, positive amount (up to 2 decimals), three-letter currency, and status.'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  const payload = {
    ...form.value,
    category: form.value.category.trim(),
    amount: form.value.amount.trim(),
    currency: form.value.currency.trim().toUpperCase(),
    status: form.value.status.trim(),
    note: form.value.note?.trim() || null,
  }
  const successMessage = editing.value ? 'Expense updated.' : 'Expense recorded.'
  try {
    if (editing.value) {
      await updateExpense(
        selectedDeparture.value.id,
        editing.value.id,
        payload,
      )
    } else {
      await createExpense(selectedDeparture.value.id, payload)
    }
    dialog.value = false
  } catch {
    error.value = 'Unable to save expense. Check the supplier and amount.'
    loading.value = false
    return
  }

  try {
    await loadExpenses()
    success.value = successMessage
  } catch {
    expenses.value = []
    expenseTotal.value = 0
    error.value = 'Expense saved, but the list could not be refreshed.'
  } finally {
    loading.value = false
  }
}

async function loadSuppliers(search?: string | null): Promise<void> {
  try {
    const result = await listSuppliers(1, 100, search ?? undefined)
    suppliers.value = result.items
    if (
      editing.value?.supplier &&
      !suppliers.value.some(
        (supplier) => supplier.id === editing.value?.supplier_id,
      )
    ) {
      suppliers.value = [...suppliers.value, editing.value.supplier]
    }
  } catch {
    error.value = 'Unable to load suppliers.'
  }
}

onMounted(() => {
  void Promise.all([load(), loadSuppliers()])
})
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Tour expenses</h1>
    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <h2 class="text-h6 mb-2">Departures</h2>
    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert
      v-if="!loading && !departures.length"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      No departures found.
    </v-alert>
    <v-table v-else-if="departures.length" class="mb-2">
      <thead>
        <tr>
          <th>Tour</th>
          <th>Dates</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="departure in departures" :key="departure.id">
          <td>{{ departure.tour_title }}</td>
          <td>{{ departure.start_date }} – {{ departure.end_date }}</td>
          <td>{{ departure.status }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              @click="selectDeparture(departure)"
            >
              Manage expenses
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-pagination
      v-if="departureTotal > pageSize"
      v-model="departurePage"
      :length="Math.ceil(departureTotal / pageSize)"
      :disabled="loading"
      @update:model-value="load"
    />

    <template v-if="selectedDeparture">
      <div class="d-flex align-center mt-8 mb-2">
        <div>
          <h2 class="text-h6">Expenses</h2>
          <div class="text-body-2">
            {{ selectedDeparture.tour_title }} ·
            {{ selectedDeparture.start_date }} ·
            {{ selectedDeparture.status }}
          </div>
        </div>
        <v-spacer />
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">
          Record expense
        </v-btn>
      </div>
      <v-alert
        v-if="!loading && !expenses.length"
        type="info"
        variant="tonal"
      >
        No expenses recorded for this departure.
      </v-alert>
      <v-table v-else-if="expenses.length">
        <thead>
          <tr>
            <th>Category</th>
            <th>Supplier</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Note</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="expense in expenses" :key="expense.id">
            <td>{{ expense.category }}</td>
            <td>{{ expense.supplier?.name || '—' }}</td>
            <td>{{ expense.amount }} {{ expense.currency }}</td>
            <td>{{ expense.status }}</td>
            <td>{{ expense.note || '—' }}</td>
            <td>
              <v-btn size="small" variant="text" @click="openEdit(expense)">
                Edit
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-pagination
        v-if="expenseTotal > pageSize"
        v-model="expensePage"
        :length="Math.ceil(expenseTotal / pageSize)"
        :disabled="loading"
        @update:model-value="loadExpenses"
      />
    </template>

    <v-dialog v-model="dialog" max-width="650">
      <v-card>
        <v-card-title>
          {{ editing ? 'Edit expense' : 'Record expense' }}
        </v-card-title>
        <v-card-text>
          <v-autocomplete
            v-model="form.supplier_id"
            :items="suppliers"
            item-title="name"
            item-value="id"
            label="Supplier (optional)"
            clearable
            @update:search="loadSuppliers"
          />
          <v-text-field v-model="form.category" label="Expense category" required />
          <v-text-field
            v-model="form.amount"
            label="Amount"
            inputmode="decimal"
            hint="Use up to 2 decimal places."
            persistent-hint
            required
          />
          <v-text-field
            v-model="form.currency"
            label="Currency code"
            maxlength="3"
            required
          />
          <v-text-field v-model="form.status" label="Status" required />
          <v-textarea v-model="form.note" label="Supporting note" />
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
