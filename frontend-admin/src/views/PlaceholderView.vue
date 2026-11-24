<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">{{ title }}</h1>
    <v-alert type="info" variant="tonal">
      This management screen is prepared for the next Admin core-screen increment.
    </v-alert>
  </div>
</template>
