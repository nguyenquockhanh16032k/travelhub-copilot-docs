<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const email = ref('')
const password = ref('')

async function submit(): Promise<void> {
  try {
    await auth.signIn(email.value, password.value)
    const redirect = typeof route.query.redirect === 'string'
      ? route.query.redirect
      : '/dashboard'
    await router.replace(redirect)
  } catch {
    // Store exposes a user-facing error message.
  }
}
</script>

<template>
  <v-container class="d-flex justify-center">
    <v-card max-width="420" width="100%" elevation="2">
      <v-card-title class="text-h5 py-6">TravelHub Admin</v-card-title>
      <v-card-text>
        <v-alert
          v-if="auth.error"
          type="error"
          variant="tonal"
          class="mb-4"
        >
          {{ auth.error }}
        </v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field
            v-model="email"
            label="Email"
            type="email"
            autocomplete="username"
            required
          />
          <v-text-field
            v-model="password"
            label="Password"
            type="password"
            autocomplete="current-password"
            min-length="8"
            required
          />
          <v-btn
            type="submit"
            color="primary"
            block
            :loading="auth.loading"
          >
            Sign in
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </v-container>
</template>
