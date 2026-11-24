<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { isAxiosError } from 'axios'
import { useRoute } from 'vue-router'

import { listBookings } from '../services/bookings'
import {
  createFinancialException,
  createPayment,
  listPayments,
  verifyPayment,
  verifyPaymentAsException,
} from '../services/payments'
import type { Booking } from '../types/booking'
import type {
  AdminPayment,
  PaymentCreatePayload,
  PaymentExceptionCreatePayload,
  PaymentExceptionVerifyPayload,
  PaymentMethod,
  PaymentStatus,
} from '../types/payment'
import { useAuthStore } from '../stores/auth'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const route = useRoute()
const canManagePayments = computed(() =>
  hasPermission(auth.user?.roles, 'payments:write'),
)
const payments = ref<AdminPayment[]>([])
const page = ref(1)
const size = 20
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')
const search = ref('')
const statusFilter = ref<PaymentStatus | ''>('')
const methodFilter = ref<PaymentMethod | ''>('')
const resolutionFilter = ref<'' | 'true' | 'false'>('')

const paymentDialog = ref(false)
const exceptionMode = ref(false)
const bookingSearch = ref('')
const bookingSearchLoading = ref(false)
const bookingOptions = ref<Booking[]>([])
const selectedBooking = ref<Booking | null>(null)
const idempotencyKey = ref('')
const form = ref({
  booking_id: '',
  amount: '',
  currency: 'VND',
  method: 'bank_transfer' as PaymentMethod,
  transaction_reference: '',
  notes: '',
})
const exceptionReason = ref('')
const exceptionConfirmed = ref(false)

const verificationDialog = ref(false)
const exceptionVerificationDialog = ref(false)
const selectedPayment = ref<AdminPayment | null>(null)
const verificationReason = ref('')
const verificationConfirmed = ref(false)

const statusOptions = [
  { title: 'All statuses', value: '' },
  { title: 'Pending', value: 'pending' },
  { title: 'Paid', value: 'paid' },
  { title: 'Failed', value: 'failed' },
  { title: 'Refunded', value: 'refunded' },
]
const methodOptions = [
  { title: 'All methods', value: '' },
  { title: 'Cash', value: 'cash' },
  { title: 'Bank transfer', value: 'bank_transfer' },
  { title: 'Card', value: 'card' },
  { title: 'Other', value: 'other' },
]
const resolutionOptions = [
  { title: 'All resolution states', value: '' },
  { title: 'Requires resolution', value: 'true' },
  { title: 'No resolution required', value: 'false' },
]
const paymentMethods = methodOptions.slice(1)
const bookingPickerOptions = computed(() =>
  bookingOptions.value.map((booking) => ({
    ...booking,
    picker_label: `${booking.reference} · ${booking.contact_name} · ${booking.status}`,
  })),
)

function requestKey(): string {
  return window.crypto.randomUUID()
}

watch(
  [form, exceptionReason],
  () => {
    if (paymentDialog.value && !saving.value) {
      idempotencyKey.value = requestKey()
    }
  },
  { deep: true },
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listPayments(page.value, size, {
      search: search.value,
      status: statusFilter.value,
      method: methodFilter.value,
      bookingId:
        typeof route.query.booking_id === 'string'
          ? route.query.booking_id
          : undefined,
      requiresResolution:
        resolutionFilter.value === ''
          ? undefined
          : resolutionFilter.value === 'true',
    })
    payments.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load payment records.'
  } finally {
    loading.value = false
  }
}

async function applyFilters(): Promise<void> {
  page.value = 1
  await load()
}

function openPaymentDialog(isException: boolean): void {
  exceptionMode.value = isException
  form.value = {
    booking_id: '',
    amount: '',
    currency: 'VND',
    method: 'bank_transfer',
    transaction_reference: '',
    notes: '',
  }
  bookingSearch.value = ''
  bookingOptions.value = []
  selectedBooking.value = null
  exceptionReason.value = ''
  exceptionConfirmed.value = false
  idempotencyKey.value = requestKey()
  paymentDialog.value = true
}

async function findBookings(): Promise<void> {
  bookingSearchLoading.value = true
  error.value = ''
  try {
    const result = await listBookings(1, 20, undefined, bookingSearch.value)
    bookingOptions.value = result.items
    if (!result.items.length) {
      error.value = 'No bookings matched that search.'
    }
  } catch {
    error.value = 'Unable to search bookings.'
  } finally {
    bookingSearchLoading.value = false
  }
}

function selectBooking(bookingId: string | null): void {
  selectedBooking.value =
    bookingOptions.value.find((booking) => booking.id === bookingId) ?? null
  form.value.booking_id = selectedBooking.value?.id ?? ''
  form.value.currency = selectedBooking.value?.currency ?? 'VND'
}

function validPaymentForm(): boolean {
  const amount = form.value.amount.trim()
  const [whole, fraction = ''] = amount.split('.')
  const amountInCents = /^\d{1,12}(\.\d{1,2})?$/.test(amount)
    ? BigInt(whole) * 100n + BigInt((fraction + '00').slice(0, 2))
    : 0n
  if (
    !form.value.booking_id ||
    !/^\d{1,12}(\.\d{1,2})?$/.test(amount) ||
    amountInCents <= 0n ||
    !form.value.currency
  ) {
    error.value = 'Choose a booking and enter an amount greater than zero with up to two decimals.'
    return false
  }
  if (exceptionMode.value && !exceptionReason.value.trim()) {
    error.value = 'A reason is required for a financial exception.'
    return false
  }
  if (exceptionMode.value && !exceptionConfirmed.value) {
    error.value = 'Confirm that the money was actually received before continuing.'
    return false
  }
  return true
}

async function submitPayment(): Promise<void> {
  if (!validPaymentForm()) return
  saving.value = true
  error.value = ''
  success.value = ''
  const details = {
    booking_id: form.value.booking_id,
    amount: form.value.amount.trim(),
    currency: form.value.currency,
    method: form.value.method,
    transaction_reference:
      form.value.transaction_reference.trim() || null,
    notes: form.value.notes.trim() || null,
  }
  try {
    if (exceptionMode.value) {
      const payload: PaymentExceptionCreatePayload = {
        ...details,
        status: 'paid',
        reason: exceptionReason.value.trim(),
        confirmation: true,
      }
      await createFinancialException(payload, idempotencyKey.value)
      success.value = 'Financial exception recorded and flagged for resolution.'
    } else {
      const payload: PaymentCreatePayload = {
        ...details,
        status: 'pending',
      }
      await createPayment(payload, idempotencyKey.value)
      success.value = 'Payment recorded as pending verification.'
    }
    paymentDialog.value = false
    await load()
  } catch {
    error.value = exceptionMode.value
      ? 'Unable to record the financial exception. Check the booking and reason.'
      : 'Unable to record payment. Check the balance, booking status and transaction reference.'
  } finally {
    saving.value = false
  }
}

function openVerification(payment: AdminPayment): void {
  selectedPayment.value = payment
  verificationDialog.value = true
}

function needsException(code: string | undefined): boolean {
  return (
    code === 'OVERPAYMENT_EXCEPTION_REQUIRED' ||
    code === 'FINANCIAL_EXCEPTION_REQUIRED'
  )
}

function getErrorCode(value: unknown): string | undefined {
  if (!isAxiosError(value)) return undefined
  const body = value.response?.data as
    | { detail?: { code?: string } }
    | undefined
  return body?.detail?.code
}

async function submitVerification(): Promise<void> {
  if (!selectedPayment.value) return
  saving.value = true
  error.value = ''
  try {
    await verifyPayment(selectedPayment.value.id)
    verificationDialog.value = false
    success.value = 'Payment verified.'
    await load()
  } catch (reason) {
    const code = getErrorCode(reason)
    if (needsException(code)) {
      verificationDialog.value = false
      verificationReason.value = ''
      verificationConfirmed.value = false
      exceptionVerificationDialog.value = true
    } else {
      error.value = 'Unable to verify this payment.'
    }
  } finally {
    saving.value = false
  }
}

async function submitVerificationException(): Promise<void> {
  if (!selectedPayment.value) return
  if (!verificationReason.value.trim() || !verificationConfirmed.value) {
    error.value = 'A reason and explicit confirmation are required.'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const payload: PaymentExceptionVerifyPayload = {
      reason: verificationReason.value.trim(),
      confirmation: true,
    }
    await verifyPaymentAsException(selectedPayment.value.id, payload)
    exceptionVerificationDialog.value = false
    success.value = 'Payment recorded as a financial exception for resolution.'
    await load()
  } catch {
    error.value = 'Unable to record this financial exception.'
  } finally {
    saving.value = false
  }
}

function paymentColor(status: PaymentStatus): string {
  if (status === 'paid') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'failed') return 'error'
  return 'default'
}

onMounted(() => {
  void load()
})
watch(
  () => route.query.booking_id,
  () => {
    page.value = 1
    void load()
  },
)
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <h1 class="text-h4">Payments</h1>
      <v-spacer />
      <v-btn
        v-if="canManagePayments"
        color="primary"
        prepend-icon="mdi-cash-plus"
        @click="openPaymentDialog(false)"
      >
        Record payment
      </v-btn>
      <v-btn
        v-if="canManagePayments"
        color="warning"
        variant="outlined"
        prepend-icon="mdi-alert"
        @click="openPaymentDialog(true)"
      >
        Record financial exception
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>
    <v-alert
      v-if="typeof route.query.booking_id === 'string'"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      Showing payment history for the selected booking.
      <v-btn
        size="small"
        variant="text"
        to="/payments"
        class="ml-2"
      >
        Clear booking filter
      </v-btn>
    </v-alert>

    <v-row class="mb-2">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="search"
          label="Search booking, contact or transaction reference"
          prepend-inner-icon="mdi-magnify"
          clearable
          @keyup.enter="applyFilters"
          @click:clear="applyFilters"
        />
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-select
          v-model="statusFilter"
          label="Payment status"
          :items="statusOptions"
          item-title="title"
          item-value="value"
          @update:model-value="applyFilters"
        />
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-select
          v-model="methodFilter"
          label="Payment method"
          :items="methodOptions"
          item-title="title"
          item-value="value"
          @update:model-value="applyFilters"
        />
      </v-col>
      <v-col cols="12" sm="6" md="2">
        <v-select
          v-model="resolutionFilter"
          label="Resolution"
          :items="resolutionOptions"
          item-title="title"
          item-value="value"
          @update:model-value="applyFilters"
        />
      </v-col>
      <v-col cols="12" md="2" class="d-flex justify-end">
        <v-btn icon="mdi-filter" aria-label="Apply payment filters" @click="applyFilters" />
      </v-col>
    </v-row>

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />
    <v-alert v-else-if="!payments.length" type="info" variant="tonal">
      No payment records match these filters.
    </v-alert>
    <div v-else class="overflow-x-auto">
      <v-table>
        <thead>
          <tr>
            <th>Booking</th>
            <th>Payment</th>
            <th>Booking total</th>
            <th>Verified / balance</th>
            <th>Method and reference</th>
            <th>Recorded / verified by</th>
            <th>Status and resolution</th>
            <th>Recorded</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="payment in payments" :key="payment.id">
            <td>
              <div class="font-weight-medium">{{ payment.booking_reference }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ payment.booking_status }}
              </div>
            </td>
            <td>{{ payment.amount }} {{ payment.currency }}</td>
            <td>{{ payment.booking_total }} {{ payment.currency }}</td>
            <td>
              <div>{{ payment.verified_paid_amount }} paid</div>
              <div>{{ payment.outstanding_balance }} outstanding</div>
              <div v-if="payment.overpaid_amount !== '0.00'" class="text-error">
                {{ payment.overpaid_amount }} overpaid
              </div>
              <div class="text-caption">{{ payment.payment_completion_status }}</div>
            </td>
            <td>
              <div>{{ payment.method.replace('_', ' ') }}</div>
              <div class="text-caption">{{ payment.transaction_reference || '—' }}</div>
            </td>
            <td>
              <div>Recorded: {{ payment.recorded_by || '—' }}</div>
              <div>Verified: {{ payment.verified_by || '—' }}</div>
            </td>
            <td>
              <v-chip size="small" :color="paymentColor(payment.status)">
                {{ payment.status }}
              </v-chip>
              <div
                v-if="payment.requires_resolution"
                class="text-caption text-error mt-1"
              >
                Requires resolution
                <div>{{ payment.resolution_reason }}</div>
              </div>
              <div v-if="payment.notes" class="text-caption mt-1">
                {{ payment.notes }}
              </div>
            </td>
            <td>{{ new Date(payment.recorded_at).toLocaleString() }}</td>
            <td>
              <v-btn
                v-if="canManagePayments && payment.status === 'pending'"
                size="small"
                variant="text"
                @click="openVerification(payment)"
              >
                Verify
              </v-btn>
              <v-btn
                :to="`/bookings?booking=${payment.booking_id}`"
                size="small"
                variant="text"
              >
                Booking
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>
    <v-pagination
      v-if="total > size"
      v-model="page"
      :length="Math.ceil(total / size)"
      class="mt-4"
      @update:model-value="load"
    />

    <v-dialog v-model="paymentDialog" max-width="700">
      <v-card>
        <v-card-title>
          {{ exceptionMode ? 'Record financial exception' : 'Record manual payment' }}
        </v-card-title>
        <v-card-text>
          <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
            {{ error }}
          </v-alert>
          <v-alert v-if="exceptionMode" type="warning" variant="tonal" class="mb-4">
            Use only for money actually received that exceeds the outstanding
            balance or belongs to an expired, cancelled or rejected booking.
            This does not reactivate the booking or initiate a refund.
          </v-alert>
          <v-text-field
            v-model="bookingSearch"
            label="Search booking reference or contact"
            prepend-inner-icon="mdi-magnify"
            :loading="bookingSearchLoading"
            @keyup.enter="findBookings"
            @click:append-inner="findBookings"
          />
          <v-btn
            class="mb-3"
            variant="outlined"
            :loading="bookingSearchLoading"
            @click="findBookings"
          >
            Find bookings
          </v-btn>
          <v-autocomplete
            :model-value="form.booking_id"
            :items="bookingPickerOptions"
            item-title="picker_label"
            item-value="id"
            label="Booking"
            @update:model-value="selectBooking"
          />
          <v-alert v-if="selectedBooking" type="info" variant="tonal" class="mb-3">
            Booking total: {{ selectedBooking.total_amount }}
            {{ selectedBooking.currency }} · Status: {{ selectedBooking.status }}
          </v-alert>
          <v-text-field
            v-model="form.amount"
            :label="`Amount received (${form.currency})`"
            inputmode="decimal"
            required
          />
          <v-select
            v-model="form.method"
            label="Payment method"
            :items="paymentMethods"
            item-title="title"
            item-value="value"
          />
          <v-text-field
            v-model="form.transaction_reference"
            label="Transaction reference (optional)"
            maxlength="255"
          />
          <v-textarea
            v-model="form.notes"
            label="Internal payment notes"
            maxlength="5000"
            rows="2"
          />
          <template v-if="exceptionMode">
            <v-textarea
              v-model="exceptionReason"
              label="Administrative reason"
              maxlength="1000"
              rows="3"
              required
            />
            <v-checkbox
              v-model="exceptionConfirmed"
              label="I confirm this money was actually received and requires manual resolution."
              hide-details
            />
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="paymentDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="saving"
            @click="submitPayment"
          >
            {{ exceptionMode ? 'Record exception' : 'Record pending payment' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="verificationDialog" max-width="520">
      <v-card>
        <v-card-title>Verify recorded payment</v-card-title>
        <v-card-text>
          <p>
            Confirm that {{ selectedPayment?.amount }}
            {{ selectedPayment?.currency }} was received. Normal verification
            enforces the outstanding balance and booking status.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="verificationDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" @click="submitVerification">
            Verify payment
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="exceptionVerificationDialog" max-width="600">
      <v-card>
        <v-card-title>Verify as financial exception</v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" class="mb-4">
            This payment cannot be verified through the normal workflow. Use
            this exception only for money actually received. Booking status and
            seats will not be restored.
          </v-alert>
          <v-textarea
            v-model="verificationReason"
            label="Administrative reason"
            maxlength="1000"
            rows="3"
            required
          />
          <v-checkbox
            v-model="verificationConfirmed"
            label="I confirm the receipt and understand this requires manual resolution."
            hide-details
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            variant="text"
            @click="exceptionVerificationDialog = false"
          >
            Cancel
          </v-btn>
          <v-btn
            color="warning"
            :loading="saving"
            @click="submitVerificationException"
          >
            Record exception
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
