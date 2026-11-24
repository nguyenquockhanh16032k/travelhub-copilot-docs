<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  createCustomer,
  listLinkableCustomerAccounts,
  listCustomers,
  updateCustomer,
} from '../services/customers'
import type {
  Customer,
  CustomerAccountOption,
  CustomerPayload,
} from '../types/customer'

const customers = ref<Customer[]>([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const search = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<Customer | null>(null)
const accountOptions = ref<CustomerAccountOption[]>([])
const accountsLoading = ref(false)
const accountSearch = ref('')
const form = ref<CustomerPayload>({
  full_name: '',
  email: null,
  phone: null,
  address: null,
  user_id: null,
})

async function loadLinkableAccounts(
  customerId?: string,
  search?: string,
): Promise<boolean> {
  accountsLoading.value = true
  try {
    const result = await listLinkableCustomerAccounts(customerId, search)
    accountOptions.value = result.items
    return true
  } catch {
    error.value = 'Unable to load customer login accounts.'
    return false
  } finally {
    accountsLoading.value = false
  }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listCustomers(page.value, size.value, search.value)
    customers.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load customers.'
  } finally {
    loading.value = false
  }
}

async function openCreate(): Promise<void> {
  editing.value = null
  accountSearch.value = ''
  form.value = {
    full_name: '',
    email: null,
    phone: null,
    address: null,
    user_id: null,
  }
  error.value = ''
  if (!(await loadLinkableAccounts())) return
  dialog.value = true
}

async function openEdit(customer: Customer): Promise<void> {
  editing.value = customer
  accountSearch.value = ''
  form.value = {
    full_name: customer.full_name,
    email: customer.email,
    phone: customer.phone,
    address: customer.address,
    user_id: customer.user_id,
  }
  error.value = ''
  if (!(await loadLinkableAccounts(customer.id))) return
  dialog.value = true
}

async function submit(): Promise<void> {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (editing.value) {
      await updateCustomer(editing.value.id, form.value)
      success.value = 'Customer updated successfully.'
    } else {
      await createCustomer(form.value)
      success.value = 'Customer created successfully.'
    }
    dialog.value = false
    await load()
  } catch {
    error.value =
      editing.value
        ? 'Unable to update customer.'
        : 'Unable to create customer.'
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
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Customers</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">
        Create customer
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-text-field
      v-model="search"
      label="Search name, email or phone"
      prepend-inner-icon="mdi-magnify"
      clearable
      class="mb-4"
      @keyup.enter="load"
    />

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="!customers.length" type="info" variant="tonal">
      No customers found.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Name</th>
          <th>Email</th>
          <th>Login account</th>
          <th>Phone</th>
          <th>Address</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="customer in customers" :key="customer.id">
          <td>{{ customer.full_name }}</td>
          <td>{{ customer.email || '-' }}</td>
          <td>{{ customer.user_id ? 'Linked' : 'Not linked' }}</td>
          <td>{{ customer.phone || '-' }}</td>
          <td>{{ customer.address || '-' }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEdit(customer)"
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
      class="mt-4"
      @update:model-value="load"
    />

    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>
          {{ editing ? 'Edit customer' : 'Create customer' }}
        </v-card-title>
        <v-card-text>
          <v-text-field v-model="form.full_name" label="Full name" required />
          <v-text-field v-model="form.email" label="Email" type="email" />
          <v-text-field v-model="form.phone" label="Phone" />
          <v-textarea v-model="form.address" label="Address" />
          <v-autocomplete
            v-model="form.user_id"
            :items="accountOptions"
            item-title="email"
            item-value="id"
            label="Customer login account"
            clearable
            no-filter
            :search="accountSearch"
            :loading="accountsLoading"
            hint="Only provisioned CUSTOMER accounts are available. Clear to unlink."
            persistent-hint
            @update:search="
              (value) => {
                accountSearch = value
                void loadLinkableAccounts(editing?.id, value)
              }
            "
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="loading" @click="submit">
            {{ editing ? 'Save' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
