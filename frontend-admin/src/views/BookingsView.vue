<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import {
  createBooking,
  changeBookingStatus,
  getBooking,
  listBookings,
  updateBooking,
} from '../services/bookings'
import { listCustomers } from '../services/customers'
import { listAdminDepartures } from '../services/departures'
import { useAuthStore } from '../stores/auth'
import { listPayments } from '../services/payments'
import type {
  Booking,
  BookingCreatePayload,
  BookingStatus,
  BookingStatusHistoryEntry,
  BookingTravelerInput,
  BookingUpdatePayload,
} from '../types/booking'
import type { AdminPaymentPage } from '../types/payment'
import type { AdminDeparture } from '../types/catalog'
import type { Customer } from '../types/customer'
import { hasPermission } from '../utils/permissions'

const auth = useAuthStore()
const route = useRoute()
const canCreateBookings = computed(() =>
  hasPermission(auth.user?.roles, 'bookings:create'),
)
const canUpdateBookings = computed(() =>
  hasPermission(auth.user?.roles, 'bookings:write'),
)
const canChangeBookingStatus = computed(() =>
  hasPermission(auth.user?.roles, 'bookings:status'),
)
const canViewFinancials = computed(() =>
  hasPermission(auth.user?.roles, 'payments:read'),
)
const bookings = ref<Booking[]>([])
const departures = ref<AdminDeparture[]>([])
const customers = ref<Customer[]>([])
const page = ref(1)
const size = ref(20)
const total = ref(0)
const statusFilter = ref<BookingStatus | ''>('')
const loading = ref(false)
const detailsLoading = ref(false)
const actionLoading = ref(false)
const error = ref('')
const success = ref('')
const selectedBooking = ref<Booking | null>(null)
const paymentPage = ref<AdminPaymentPage | null>(null)
const paymentHistoryPage = ref(1)
const paymentHistorySize = 20
const paymentHistoryLoading = ref(false)
const detailsDialog = ref(false)
const actionDialog = ref(false)
const createDialog = ref(false)
const editDialog = ref(false)
const optionsLoading = ref(false)
const actionStatus = ref<'confirmed' | 'cancelled'>('confirmed')
const actionReason = ref('')
const createForm = ref<BookingCreatePayload>({
  departure_id: '',
  customer_id: '',
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  travelers: [{ full_name: '', traveler_type: 'adult' }],
  notes: null,
})
const editForm = ref<BookingUpdatePayload>({
  contact_name: '',
  contact_email: '',
  contact_phone: '',
  travelers: [],
})

const statusOptions = [
  { title: 'All statuses', value: '' },
  { title: 'Pending', value: 'pending' },
  { title: 'Confirmed', value: 'confirmed' },
  { title: 'Cancelled', value: 'cancelled' },
  { title: 'Completed', value: 'completed' },
]
const departureOptions = computed(() =>
  departures.value.map((departure) => ({
    ...departure,
    label: `${departure.tour_title} · ${departure.start_date} · ${departure.available_seats} seats`,
  })),
)
const selectedCreateDeparture = computed(() =>
  departures.value.find(
    (departure) => departure.id === createForm.value.departure_id,
  ),
)
const canAddTraveler = computed(
  () =>
    selectedCreateDeparture.value !== undefined &&
    createForm.value.travelers.length <
      Math.min(selectedCreateDeparture.value.available_seats, 100),
)

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const result = await listBookings(
      page.value,
      size.value,
      statusFilter.value || undefined,
    )
    bookings.value = result.items
    total.value = result.total
  } catch {
    error.value = 'Unable to load bookings.'
  } finally {
    loading.value = false
  }
}

async function applyStatusFilter(): Promise<void> {
  page.value = 1
  await load()
}

async function openDetails(booking: Booking | string): Promise<void> {
  const bookingId = typeof booking === 'string' ? booking : booking.id
  detailsDialog.value = true
  detailsLoading.value = true
  error.value = ''
  paymentHistoryPage.value = 1
  try {
    const [details, payments] = await Promise.all([
      getBooking(bookingId),
      canViewFinancials.value
        ? listPayments(1, paymentHistorySize, { bookingId })
        : Promise.resolve(null),
    ])
    selectedBooking.value = details
    paymentPage.value = payments
  } catch {
    detailsDialog.value = false
    error.value = 'Unable to load booking details.'
  } finally {
    detailsLoading.value = false
  }
}

async function loadPaymentHistory(pageNumber: number): Promise<void> {
  if (!selectedBooking.value || !canViewFinancials.value) return
  paymentHistoryLoading.value = true
  error.value = ''
  try {
    paymentPage.value = await listPayments(
      pageNumber,
      paymentHistorySize,
      { bookingId: selectedBooking.value.id },
    )
    paymentHistoryPage.value = pageNumber
  } catch {
    error.value = 'Unable to load payment history.'
  } finally {
    paymentHistoryLoading.value = false
  }
}

async function openCreateDialog(): Promise<void> {
  createDialog.value = true
  optionsLoading.value = true
  error.value = ''
  try {
    const [departureResult, customerResult] = await Promise.all([
      listAdminDepartures(1, 100),
      listCustomers(1, 100),
    ])
    departures.value = departureResult.items
    customers.value = customerResult.items
    createForm.value = {
      departure_id: '',
      customer_id: '',
      contact_name: '',
      contact_email: '',
      contact_phone: '',
      travelers: [{ full_name: '', traveler_type: 'adult' }],
      notes: null,
    }
    if (!customers.value.length) {
      error.value = 'Create a customer record before creating a staff booking.'
    } else if (!departures.value.length) {
      error.value = 'There are no departures available for booking.'
    }
  } catch {
    createDialog.value = false
    error.value = 'Unable to load customers and departures.'
  } finally {
    optionsLoading.value = false
  }
}

function syncCustomerContact(customerId: string | null): void {
  const customer = customers.value.find((item) => item.id === customerId)
  if (!customer) return
  createForm.value.contact_name = customer.full_name
  createForm.value.contact_email = customer.email ?? ''
  createForm.value.contact_phone = customer.phone ?? ''
  if (createForm.value.travelers.length === 1) {
    createForm.value.travelers[0].full_name = customer.full_name
  }
}

function addCreateTraveler(): void {
  if (!canAddTraveler.value) return
  createForm.value.travelers.push({ full_name: '', traveler_type: 'adult' })
}

function removeCreateTraveler(index: number): void {
  if (createForm.value.travelers.length > 1) {
    createForm.value.travelers.splice(index, 1)
  }
}

async function submitCreateBooking(): Promise<void> {
  if (
    !createForm.value.departure_id ||
    !createForm.value.customer_id ||
    !createForm.value.contact_name.trim() ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(createForm.value.contact_email.trim()) ||
    !createForm.value.contact_phone.trim() ||
    createForm.value.travelers.some(
      (traveler) => !traveler.full_name.trim() || !traveler.traveler_type.trim(),
    )
  ) {
    error.value = 'Complete the customer, contact and traveler details.'
    return
  }
  if (
    selectedCreateDeparture.value &&
    createForm.value.travelers.length >
      selectedCreateDeparture.value.available_seats
  ) {
    error.value = 'The departure does not have enough seats for these travelers.'
    return
  }

  actionLoading.value = true
  error.value = ''
  success.value = ''
  try {
    await createBooking({
      ...createForm.value,
      contact_name: createForm.value.contact_name.trim(),
      contact_email: createForm.value.contact_email.trim(),
      contact_phone: createForm.value.contact_phone.trim(),
      travelers: createForm.value.travelers.map((traveler) => ({
        full_name: traveler.full_name.trim(),
        traveler_type: traveler.traveler_type.trim(),
      })),
    })
    createDialog.value = false
    success.value = 'Booking created.'
    await load()
  } catch {
    error.value = 'Unable to create the booking. Recheck seats and customer details.'
  } finally {
    actionLoading.value = false
  }
}

function openEditDialog(booking: Booking): void {
  selectedBooking.value = booking
  editForm.value = {
    contact_name: booking.contact_name,
    contact_email: booking.contact_email,
    contact_phone: booking.contact_phone,
    travelers: booking.travelers.map((traveler) => ({
      full_name: traveler.full_name,
      traveler_type: traveler.traveler_type,
    })),
  }
  editDialog.value = true
}

async function submitBookingUpdate(): Promise<void> {
  if (!selectedBooking.value) return
  const travelers = editForm.value.travelers ?? []
  if (
    !editForm.value.contact_name?.trim() ||
    !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
      (editForm.value.contact_email ?? '').trim(),
    ) ||
    !editForm.value.contact_phone?.trim() ||
    travelers.some(
      (traveler) => !traveler.full_name.trim() || !traveler.traveler_type.trim(),
    )
  ) {
    error.value = 'Complete the contact and traveler details.'
    return
  }

  actionLoading.value = true
  error.value = ''
  success.value = ''
  try {
    selectedBooking.value = await updateBooking(selectedBooking.value.id, {
      ...editForm.value,
      contact_name: editForm.value.contact_name.trim(),
      contact_email: (editForm.value.contact_email ?? '').trim(),
      contact_phone: editForm.value.contact_phone.trim(),
      travelers: travelers.map((traveler: BookingTravelerInput) => ({
        full_name: traveler.full_name.trim(),
        traveler_type: traveler.traveler_type.trim(),
      })),
    })
    editDialog.value = false
    success.value = 'Booking details updated.'
    await load()
  } catch {
    error.value = 'Unable to update booking details.'
  } finally {
    actionLoading.value = false
  }
}

function openStatusAction(status: 'confirmed' | 'cancelled'): void {
  actionStatus.value = status
  actionReason.value = ''
  actionDialog.value = true
}

async function submitStatusAction(): Promise<void> {
  if (!selectedBooking.value) return

  actionLoading.value = true
  error.value = ''
  success.value = ''
  try {
    const updated = await changeBookingStatus(
      selectedBooking.value.id,
      actionStatus.value,
      actionReason.value,
    )
    selectedBooking.value = updated
    actionDialog.value = false
    success.value =
      actionStatus.value === 'confirmed'
        ? 'Booking confirmed successfully.'
        : 'Booking cancelled successfully.'
    await load()
  } catch {
    error.value =
      actionStatus.value === 'confirmed'
        ? 'Unable to confirm booking.'
        : 'Unable to cancel booking.'
  } finally {
    actionLoading.value = false
  }
}

function sortedHistory(history: BookingStatusHistoryEntry[]) {
  return [...history].sort(
    (left, right) =>
      new Date(left.changed_at).getTime() - new Date(right.changed_at).getTime(),
  )
}

function historySubtitle(entry: BookingStatusHistoryEntry): string {
  const changedAt = new Date(entry.changed_at).toLocaleString()
  return entry.reason ? `${changedAt} · ${entry.reason}` : changedAt
}

onMounted(async () => {
  await load()
  const bookingId = route.query.booking
  if (typeof bookingId === 'string') {
    await openDetails(bookingId)
  }
})
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Bookings</h1>
      <v-spacer />
      <v-btn
        v-if="canCreateBookings"
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
      >
        Create booking
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" class="mb-4">
      {{ error }}
    </v-alert>
    <v-alert v-if="success" type="success" variant="tonal" class="mb-4">
      {{ success }}
    </v-alert>

    <v-select
      v-model="statusFilter"
      label="Filter by status"
      :items="statusOptions"
      item-title="title"
      item-value="value"
      class="mb-4"
      @update:model-value="applyStatusFilter"
    />

    <v-progress-linear v-if="loading" indeterminate />
    <v-alert v-else-if="!bookings.length" type="info" variant="tonal">
      No bookings found.
    </v-alert>
    <v-table v-else>
      <thead>
        <tr>
          <th>Reference</th>
          <th>Contact</th>
          <th>Departure ID</th>
          <th>Travelers</th>
          <th v-if="canViewFinancials">Total</th>
          <th>Status</th>
          <th />
        </tr>
      </thead>
      <tbody>
        <tr v-for="booking in bookings" :key="booking.id">
          <td>{{ booking.reference }}</td>
          <td>{{ booking.contact_name }}</td>
          <td class="text-truncate" style="max-width: 180px">
            {{ booking.departure_id }}
          </td>
          <td>{{ booking.passenger_count }}</td>
          <td v-if="canViewFinancials">
            {{ booking.total_amount }} {{ booking.currency }}
          </td>
          <td>{{ booking.status }}</td>
          <td>
            <v-btn
              size="small"
              variant="text"
              prepend-icon="mdi-eye"
              @click="openDetails(booking)"
            >
              Details
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

    <v-dialog v-model="detailsDialog" max-width="720">
      <v-card>
        <v-card-title>
          Booking {{ selectedBooking?.reference || '' }}
        </v-card-title>
        <v-card-text v-if="detailsLoading">
          <v-progress-linear indeterminate />
        </v-card-text>
        <v-card-text v-else-if="selectedBooking">
          <p>
            <strong>Status:</strong>
            {{ selectedBooking.status }}
          </p>
          <p>
            <strong>Contact:</strong>
            {{ selectedBooking.contact_name }} ·
            {{ selectedBooking.contact_email }} ·
            {{ selectedBooking.contact_phone }}
          </p>
          <p>
            <strong>Departure ID:</strong>
            {{ selectedBooking.departure_id }}
          </p>
          <p v-if="canViewFinancials">
            <strong>Total booking value:</strong>
            {{ selectedBooking.total_amount }} {{ selectedBooking.currency }}
          </p>
          <template v-if="canViewFinancials && paymentPage?.booking_summary">
            <v-alert type="info" variant="tonal" class="mt-4">
              Verified: {{ paymentPage.booking_summary.verified_paid_amount }}
              {{ paymentPage.booking_summary.currency }} · Outstanding:
              {{ paymentPage.booking_summary.outstanding_balance }}
              {{ paymentPage.booking_summary.currency }} ·
              {{ paymentPage.booking_summary.payment_completion_status }}
            </v-alert>
            <v-alert
              v-if="paymentPage.booking_summary.overpaid_amount !== '0.00'"
              type="error"
              variant="tonal"
            >
              Overpaid:
              {{ paymentPage.booking_summary.overpaid_amount }}
              {{ paymentPage.booking_summary.currency }} · requires manual
              resolution
            </v-alert>
            <h2 class="text-h6 mt-5 mb-2">Payment history</h2>
            <v-progress-linear
              v-if="paymentHistoryLoading"
              indeterminate
              class="mb-2"
            />
            <v-alert
              v-else-if="!paymentPage.items.length"
              type="info"
              variant="tonal"
            >
              No payments have been recorded for this booking.
            </v-alert>
            <div v-else class="overflow-x-auto">
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Method / reference</th>
                    <th>Recorded / verified by</th>
                    <th>Notes / resolution</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="payment in paymentPage.items" :key="payment.id">
                    <td>{{ new Date(payment.recorded_at).toLocaleString() }}</td>
                    <td>{{ payment.amount }} {{ payment.currency }}</td>
                    <td>
                      {{ payment.status }}
                      <div
                        v-if="payment.requires_resolution"
                        class="text-caption text-error"
                      >
                        Requires resolution
                      </div>
                    </td>
                    <td>
                      {{ payment.method.replace('_', ' ') }} ·
                      {{ payment.transaction_reference || '—' }}
                    </td>
                    <td>
                      <div>Recorded: {{ payment.recorded_by || '—' }}</div>
                      <div>Verified: {{ payment.verified_by || '—' }}</div>
                    </td>
                    <td>
                      <div v-if="payment.notes">{{ payment.notes }}</div>
                      <div
                        v-if="payment.resolution_reason"
                        class="text-error"
                      >
                        {{ payment.resolution_reason }}
                      </div>
                      <span v-if="!payment.notes && !payment.resolution_reason">—</span>
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </div>
            <v-pagination
              v-if="paymentPage.total > paymentHistorySize"
              v-model="paymentHistoryPage"
              :length="Math.ceil(paymentPage.total / paymentHistorySize)"
              @update:model-value="loadPaymentHistory"
            />
          </template>
          <p v-if="selectedBooking.notes">
            <strong>Notes:</strong> {{ selectedBooking.notes }}
          </p>

          <h2 class="text-h6 mt-5 mb-2">Travelers</h2>
          <v-alert v-if="!selectedBooking.travelers.length" type="info" variant="tonal">
            No traveler details available.
          </v-alert>
          <v-list v-else density="compact">
            <v-list-item
              v-for="traveler in selectedBooking.travelers"
              :key="traveler.id"
              :title="traveler.full_name"
              :subtitle="traveler.traveler_type"
            />
          </v-list>

          <h2 class="text-h6 mt-5 mb-2">Status history</h2>
          <v-alert
            v-if="!selectedBooking.status_history.length"
            type="info"
            variant="tonal"
          >
            No status history available.
          </v-alert>
          <v-list v-else density="compact">
            <v-list-item
              v-for="entry in sortedHistory(selectedBooking.status_history)"
              :key="entry.id"
              :title="`${entry.old_status || 'Created'} → ${entry.new_status}`"
              :subtitle="historySubtitle(entry)"
            />
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            v-if="canViewFinancials && selectedBooking"
            :to="{
              path: '/payments',
              query: { booking_id: selectedBooking.id },
            }"
            variant="text"
            prepend-icon="mdi-cash-multiple"
          >
            Manage payments
          </v-btn>
          <v-btn
            v-if="canUpdateBookings && (selectedBooking?.status === 'pending' || selectedBooking?.status === 'confirmed')"
            variant="text"
            prepend-icon="mdi-pencil"
            @click="selectedBooking && openEditDialog(selectedBooking)"
          >
            Edit details
          </v-btn>
          <v-btn
            v-if="canChangeBookingStatus && selectedBooking?.status === 'pending'"
            color="primary"
            variant="text"
            @click="openStatusAction('confirmed')"
          >
            Confirm
          </v-btn>
          <v-btn
            v-if="canChangeBookingStatus && (selectedBooking?.status === 'pending' || selectedBooking?.status === 'confirmed')"
            color="error"
            variant="text"
            @click="openStatusAction('cancelled')"
          >
            Cancel booking
          </v-btn>
          <v-btn variant="text" @click="detailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="createDialog" max-width="760">
      <v-card>
        <v-card-title>Create booking for a customer</v-card-title>
        <v-card-text>
          <v-progress-linear v-if="optionsLoading" indeterminate class="mb-4" />
          <v-select
            v-model="createForm.customer_id"
            :items="customers"
            item-title="full_name"
            item-value="id"
            label="Customer"
            :disabled="optionsLoading || !customers.length"
            @update:model-value="syncCustomerContact"
          />
          <v-select
            v-model="createForm.departure_id"
            :items="departureOptions"
            item-title="label"
            item-value="id"
            label="Departure"
            :disabled="optionsLoading || !departures.length"
          />
          <v-text-field
            v-model="createForm.contact_name"
            label="Booking contact name"
            maxlength="255"
            required
          />
          <v-text-field
            v-model="createForm.contact_email"
            label="Booking contact email"
            type="email"
            maxlength="255"
            required
          />
          <v-text-field
            v-model="createForm.contact_phone"
            label="Booking contact phone"
            maxlength="50"
            required
          />
          <h2 class="text-subtitle-1 mt-2">Travelers</h2>
          <v-row
            v-for="(traveler, index) in createForm.travelers"
            :key="index"
            align="center"
          >
            <v-col cols="12" sm="5">
              <v-text-field
                v-model="traveler.full_name"
                :label="`Traveler ${index + 1} full name`"
                maxlength="255"
                required
              />
            </v-col>
            <v-col cols="9" sm="5">
              <v-text-field
                v-model="traveler.traveler_type"
                label="Traveler type"
                maxlength="20"
                required
              />
            </v-col>
            <v-col cols="3" sm="2">
              <v-btn
                v-if="createForm.travelers.length > 1"
                icon="mdi-delete-outline"
                variant="text"
                color="error"
                :aria-label="`Remove traveler ${index + 1}`"
                @click="removeCreateTraveler(index)"
              />
            </v-col>
          </v-row>
          <v-btn
            variant="outlined"
            prepend-icon="mdi-account-plus"
            :disabled="!canAddTraveler"
            @click="addCreateTraveler"
          >
            Add traveler
          </v-btn>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="createDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="actionLoading"
            :disabled="optionsLoading || !departures.length || !customers.length"
            @click="submitCreateBooking"
          >
            Create booking
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="editDialog" max-width="720">
      <v-card>
        <v-card-title>Edit booking contact and travelers</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="editForm.contact_name"
            label="Contact name"
            maxlength="255"
            required
          />
          <v-text-field
            v-model="editForm.contact_email"
            label="Contact email"
            type="email"
            maxlength="255"
            required
          />
          <v-text-field
            v-model="editForm.contact_phone"
            label="Contact phone"
            maxlength="50"
            required
          />
          <h2 class="text-subtitle-1 mt-2">Travelers</h2>
          <v-row
            v-for="(traveler, index) in editForm.travelers"
            :key="index"
            align="center"
          >
            <v-col cols="7">
              <v-text-field
                v-model="traveler.full_name"
                :label="`Traveler ${index + 1} full name`"
                maxlength="255"
                required
              />
            </v-col>
            <v-col cols="5">
              <v-text-field
                v-model="traveler.traveler_type"
                label="Traveler type"
                maxlength="20"
                required
              />
            </v-col>
          </v-row>
          <p class="text-caption text-medium-emphasis">
            Traveler count cannot be changed here; use the booking workflow for
            any seat-count adjustment.
          </p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="editDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            :loading="actionLoading"
            @click="submitBookingUpdate"
          >
            Save changes
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="actionDialog" max-width="520">
      <v-card>
        <v-card-title>
          {{ actionStatus === 'confirmed' ? 'Confirm booking' : 'Cancel booking' }}
        </v-card-title>
        <v-card-text>
          <p v-if="actionStatus === 'cancelled'">
            This will cancel the booking and release its reserved seats. This
            action cannot be undone.
          </p>
          <v-textarea
            v-model="actionReason"
            label="Reason (optional)"
            maxlength="1000"
            rows="3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="actionDialog = false">Keep booking</v-btn>
          <v-btn
            :color="actionStatus === 'cancelled' ? 'error' : 'primary'"
            :loading="actionLoading"
            @click="submitStatusAction"
          >
            {{ actionStatus === 'confirmed' ? 'Confirm booking' : 'Cancel booking' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
