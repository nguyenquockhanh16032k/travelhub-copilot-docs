<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const authMessage = ref('')

onMounted(() => {
  void auth.restoreSession()
})

watch(
  () => auth.isAuthenticated,
  (authenticated) => {
    if (!authenticated && router.currentRoute.value.meta.requiresCustomerAuth) {
      void router.replace('/login')
    }
  },
)

async function signOut(): Promise<void> {
  authMessage.value = ''
  try {
    await auth.signOut()
  } catch {
    authMessage.value =
      'Your local session was cleared, but sign-out could not be confirmed with the server.'
  }
}
</script>

<template>
  <v-app>
    <v-app-bar color="surface" elevation="1">
      <v-container class="d-flex align-center py-0">
        <v-btn to="/" variant="text" class="text-h6 font-weight-bold px-0">
          TravelHub
        </v-btn>
        <v-spacer />
        <v-btn to="/" variant="text">Home</v-btn>
        <v-btn to="/tours" variant="text">Explore tours</v-btn>
        <v-btn v-if="auth.user" to="/my/bookings" variant="text">
          My bookings
        </v-btn>
        <v-btn v-if="!auth.user" to="/login" variant="text">
          Customer sign in
        </v-btn>
        <v-btn v-else variant="text" @click="signOut">Sign out</v-btn>
      </v-container>
    </v-app-bar>

    <v-main>
      <v-container v-if="authMessage">
        <v-alert type="warning" variant="tonal">{{ authMessage }}</v-alert>
      </v-container>
      <router-view />
    </v-main>

    <v-footer class="mt-10">
      <v-container class="text-center text-medium-emphasis">
        TravelHub · Discover your next trip
      </v-container>
    </v-footer>
  </v-app>
</template>
