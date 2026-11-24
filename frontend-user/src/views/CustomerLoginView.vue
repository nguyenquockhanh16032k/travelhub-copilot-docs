<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')

async function submit(): Promise<void> {
  try {
    await auth.signIn(email.value.trim(), password.value)
    const requestedPath = route.query.redirect
    const redirect =
      typeof requestedPath === 'string' &&
      requestedPath.startsWith('/') &&
      !requestedPath.startsWith('//') &&
      requestedPath !== '/login'
        ? requestedPath
        : '/my/bookings'
    await router.replace(redirect)
  } catch {
    return
  }
}
</script>

<template>
  <v-container class="py-12" style="max-width: 520px">
    <v-card>
      <v-card-title class="text-h5">Customer sign in</v-card-title>
      <v-card-text>
        <p class="text-medium-emphasis mb-4">
          Sign in to view bookings linked to your TravelHub customer profile.
          Customer accounts are provisioned by TravelHub staff.
        </p>
        <v-alert v-if="auth.error" type="error" variant="tonal" class="mb-4">
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
