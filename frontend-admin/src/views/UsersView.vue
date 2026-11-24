<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import {
  createUser,
  listAssignableRoles,
  listUsers,
  updateUser,
} from '../services/users'
import type {
  AssignableRole,
  AssignableRoleOption,
  ManagedUser,
  UserCreatePayload,
  UserUpdatePayload,
} from '../types/user'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const users = ref<ManagedUser[]>([])
const roles = ref<AssignableRoleOption[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const search = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')
const dialog = ref(false)
const editing = ref<ManagedUser | null>(null)
const form = ref({
  email: '',
  password: '',
  role: 'STAFF' as AssignableRole,
  is_active: true,
})

const canManageAdmins = computed(() =>
  hasPermission(auth.user?.roles, 'users:manage_admin'),
)

function canManage(user: ManagedUser): boolean {
  if (user.roles.includes('SUPER_ADMIN')) return false
  if (user.roles.includes('ADMIN')) return canManageAdmins.value
  return user.roles.includes('STAFF')
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listUsers(page.value, pageSize, search.value)
    users.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load users.'
  } finally {
    loading.value = false
  }
}

async function loadRoles(): Promise<void> {
  try {
    roles.value = await listAssignableRoles()
  } catch {
    error.value = 'Unable to load assignable roles.'
  }
}

function openCreate(): void {
  editing.value = null
  form.value = {
    email: '',
    password: '',
    role: roles.value[0]?.code ?? 'STAFF',
    is_active: true,
  }
  dialog.value = true
}

function openEdit(user: ManagedUser): void {
  const assignableRole = roles.value.find((option) =>
    user.roles.includes(option.code),
  )?.code
  if (!assignableRole || !canManage(user)) return

  editing.value = user
  form.value = {
    email: user.email,
    password: '',
    role: assignableRole,
    is_active: user.is_active,
  }
  dialog.value = true
}

async function submit(): Promise<void> {
  const email = form.value.email.trim()
  if (!email || (!editing.value && !form.value.password)) {
    error.value = 'Enter an email and an initial password for a new user.'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (editing.value) {
      const payload: UserUpdatePayload = {
        email,
        role: form.value.role,
        is_active: form.value.is_active,
      }
      if (form.value.password) payload.password = form.value.password
      await updateUser(editing.value.id, payload)
      success.value = 'User updated.'
    } else {
      const payload: UserCreatePayload = {
        email,
        password: form.value.password,
        role: form.value.role,
      }
      await createUser(payload)
      success.value = 'User created.'
    }
    dialog.value = false
    await load()
  } catch {
    error.value = 'Unable to save user. Check the email, password and role.'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void Promise.all([load(), loadRoles()])
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Users and roles</h1>
      <v-spacer />
      <v-btn
        v-if="roles.length"
        color="primary"
        prepend-icon="mdi-account-plus"
        @click="openCreate"
      >
        Add user
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
      label="Search email"
      prepend-inner-icon="mdi-magnify"
      clearable
      class="mb-4"
      @keyup.enter="load"
    />

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-else-if="!users.length" type="info" variant="tonal">
      No manageable users found.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Email</th>
          <th>Role</th>
          <th>Status</th>
          <th>Created</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.email }}</td>
          <td>{{ user.roles.join(', ') }}</td>
          <td>{{ user.is_active ? 'Active' : 'Inactive' }}</td>
          <td>{{ new Date(user.created_at).toLocaleDateString() }}</td>
          <td>
            <v-btn
              v-if="canManage(user)"
              size="small"
              variant="text"
              prepend-icon="mdi-pencil"
              @click="openEdit(user)"
            >
              Manage
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

    <v-dialog v-model="dialog" max-width="560">
      <v-card>
        <v-card-title>{{ editing ? 'Manage user' : 'Create user' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="form.email"
            label="Email"
            type="email"
            autocomplete="username"
            required
          />
          <v-text-field
            v-model="form.password"
            :label="editing ? 'New password (optional)' : 'Initial password'"
            type="password"
            autocomplete="new-password"
            minlength="8"
            maxlength="128"
            :required="!editing"
          />
          <v-select
            v-model="form.role"
            :items="roles"
            item-title="code"
            item-value="code"
            label="Role"
          />
          <v-switch
            v-if="editing"
            v-model="form.is_active"
            label="Account active"
            color="primary"
            hide-details
          />
          <p v-if="!canManageAdmins" class="text-caption text-medium-emphasis">
            You can create CUSTOMER accounts and manage STAFF accounts.
          </p>
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
