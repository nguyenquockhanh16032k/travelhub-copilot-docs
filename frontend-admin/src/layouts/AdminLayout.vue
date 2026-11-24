<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { hasPermission, type Permission } from '../utils/permissions'

const router = useRouter()
const auth = useAuthStore()

const allNavigation = [
  { title: 'Dashboard', to: '/dashboard', icon: 'mdi-view-dashboard', permission: 'dashboard:read' },
  { title: 'Tours', to: '/tours', icon: 'mdi-map-marker-path', permission: 'tours:read' },
  { title: 'Departures', to: '/departures', icon: 'mdi-calendar-range', permission: 'departures:read' },
  { title: 'Bookings', to: '/bookings', icon: 'mdi-ticket-confirmation', permission: 'bookings:read' },
  { title: 'Payments', to: '/payments', icon: 'mdi-cash-multiple', permission: 'payments:read' },
  { title: 'Customers', to: '/customers', icon: 'mdi-account-group', permission: 'customers:read' },
  { title: 'Itineraries', to: '/itineraries', icon: 'mdi-format-list-numbered', permission: 'itineraries:read' },
  { title: 'Guides', to: '/guides', icon: 'mdi-account-tie', permission: 'guides:read' },
  {
    title: 'Tour assignments',
    to: '/assignments',
    icon: 'mdi-account-multiple-check',
    permission: 'assignments:read',
  },
  { title: 'Suppliers', to: '/suppliers', icon: 'mdi-truck', permission: 'suppliers:read' },
  { title: 'Tour expenses', to: '/expenses', icon: 'mdi-cash-minus', permission: 'expenses:read' },
  { title: 'Articles', to: '/articles', icon: 'mdi-newspaper', permission: 'articles:read' },
  { title: 'Reports', to: '/reports', icon: 'mdi-chart-box-outline', permission: 'reports:read' },
  { title: 'Users and roles', to: '/users', icon: 'mdi-account-key', permission: 'users:read' },
]

const displayName = computed(() => auth.user?.email ?? '')
const navigation = computed(() =>
  allNavigation.filter((item) =>
    hasPermission(auth.user?.roles, item.permission as Permission),
  ),
)

async function handleSignOut(): Promise<void> {
  await auth.signOut()
  await router.replace('/login')
}

function handleSessionExpired(): void {
  void auth.signOut().finally(() => {
    void router.replace('/login')
  })
}

onMounted(() => {
  window.addEventListener('travelhub-session-expired', handleSessionExpired)
})

onUnmounted(() => {
  window.removeEventListener('travelhub-session-expired', handleSessionExpired)
})
</script>

<template>
  <v-app>
    <v-navigation-drawer permanent>
      <v-list-item title="TravelHub" subtitle="Admin" />
      <v-divider />
      <v-list nav>
        <v-list-item
          v-for="item in navigation"
          :key="item.to"
          :to="item.to"
          :title="item.title"
          :prepend-icon="item.icon"
        />
      </v-list>
    </v-navigation-drawer>

    <v-app-bar>
      <v-spacer />
      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" prepend-icon="mdi-account-circle" variant="text">
            {{ displayName }}
          </v-btn>
        </template>
        <v-list>
          <v-list-item title="Sign out" prepend-icon="mdi-logout" @click="handleSignOut" />
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>
