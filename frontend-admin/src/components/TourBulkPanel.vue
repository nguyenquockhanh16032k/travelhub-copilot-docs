<script setup lang="ts">
import { computed, ref } from 'vue'
import { downloadTourFile, uploadTourFile, type BulkFormat, type TourImportResult } from '../services/tourBulk'

const emit = defineEmits<{ imported: [] }>()
const file = ref<File | null>(null)
const busy = ref(false)
const error = ref('')
const result = ref<TourImportResult | null>(null)
const format = ref<BulkFormat>('xlsx')
const canCommit = computed(() => !!file.value && result.value?.preview === true &&
  result.value.error_rows === 0 && result.value.valid_rows > 0)

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  file.value = input.files?.[0] ?? null
  result.value = null
  error.value = ''
  if (file.value && (!/\.(csv|xlsx)$/i.test(file.value.name) || file.value.size > 2 * 1024 * 1024)) {
    error.value = 'Choose a .csv or .xlsx file no larger than 2 MiB.'
    file.value = null
  }
}

async function exportFile(template: boolean): Promise<void> {
  busy.value = true
  error.value = ''
  try {
    await downloadTourFile(format.value, template)
  } catch {
    error.value = 'Download failed. Check permissions or try again.'
  } finally {
    busy.value = false
  }
}

async function preview(): Promise<void> {
  if (!file.value) return
  busy.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await uploadTourFile(file.value, true)
  } catch {
    error.value = 'Could not inspect this file. Verify the format and headers.'
  } finally {
    busy.value = false
  }
}

async function commit(): Promise<void> {
  if (!file.value || !canCommit.value) return
  if (!window.confirm('Create all validated tours as drafts? Existing tours will not be changed.')) return
  busy.value = true
  error.value = ''
  try {
    const response = await uploadTourFile(file.value, false)
    result.value = response
    if (response.error_rows === 0 && response.created > 0) emit('imported')
  } catch {
    error.value = 'Import failed. No rows should be imported; review the server error and retry.'
    result.value = null
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <v-card variant="outlined" class="mb-4">
    <v-card-title>Import / Export tours</v-card-title>
    <v-card-subtitle>CSV or Excel (.xlsx) · Up to 500 new tours per import · Draft only</v-card-subtitle>
    <v-card-text>
      <div class="d-flex flex-wrap ga-2 align-center mb-4">
        <v-select v-model="format" label="Download format" :items="['xlsx', 'csv']"
          style="max-width: 165px" density="compact" hide-details />
        <v-btn variant="outlined" :disabled="busy" prepend-icon="mdi-download"
          @click="exportFile(false)">Export tours</v-btn>
        <v-btn variant="text" :disabled="busy" prepend-icon="mdi-file-download-outline"
          @click="exportFile(true)">Download template</v-btn>
      </div>
      <label class="text-body-2 font-weight-medium" for="tour-bulk-file">Upload a file to preview</label>
      <input id="tour-bulk-file" class="d-block my-2" type="file" accept=".csv,.xlsx"
        :disabled="busy" @change="onFileChange" />
      <div class="d-flex flex-wrap ga-2 mt-3">
        <v-btn color="primary" variant="outlined" :disabled="!file || busy"
          prepend-icon="mdi-file-search-outline" @click="preview">Preview import</v-btn>
        <v-btn color="primary" :disabled="!canCommit || busy"
          prepend-icon="mdi-check" @click="commit">Import as drafts</v-btn>
      </div>
      <v-progress-linear v-if="busy" indeterminate class="mt-3" />
      <v-alert v-if="error" class="mt-3" type="error" variant="tonal">{{ error }}</v-alert>
      <v-alert v-if="result" class="mt-3" :type="result.error_rows ? 'warning' : 'success'" variant="tonal">
        {{ result.valid_rows }} valid · {{ result.error_rows }} invalid · {{ result.created }} created.
        <span v-if="result.preview">This is a preview; nothing has been saved.</span>
      </v-alert>
      <v-table v-if="result?.errors.length" density="compact" class="mt-3">
        <thead><tr><th>Row</th><th>Slug</th><th>Error</th></tr></thead>
        <tbody>
          <tr v-for="issue in result.errors" :key="issue.row">
            <td>{{ issue.row }}</td>
            <td>{{ issue.slug }}</td>
            <td>{{ issue.errors.join('; ') }}</td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>
