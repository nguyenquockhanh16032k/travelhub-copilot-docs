<template>
  <v-container class="py-12" style="max-width: 640px">
    <v-alert type="error" variant="tonal" title="Access denied">
      Your account does not have permission to open this page.
    </v-alert>
    <v-btn class="mt-4" to="/dashboard" color="primary">
      Back to dashboard
    </v-btn>
  </v-container>
</template>
