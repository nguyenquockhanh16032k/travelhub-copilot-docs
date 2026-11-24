import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import ToursView from '../views/ToursView.vue'
import TourDetailView from '../views/TourDetailView.vue'
import BookingView from '../views/BookingView.vue'
import BookingConfirmationView from '../views/BookingConfirmationView.vue'
import CustomerLoginView from '../views/CustomerLoginView.vue'
import CustomerBookingsView from '../views/CustomerBookingsView.vue'
import CustomerBookingDetailView from '../views/CustomerBookingDetailView.vue'
import { hasStoredSession } from '../services/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/tours', component: ToursView },
    {
      path: '/tours/:tourId',
      name: 'tour-detail',
      component: TourDetailView,
    },
    { path: '/booking/new', component: BookingView },
    { path: '/booking/confirmation', component: BookingConfirmationView },
    {
      path: '/login',
      name: 'customer-login',
      component: CustomerLoginView,
    },
    {
      path: '/my/bookings',
      component: CustomerBookingsView,
      meta: { requiresCustomerAuth: true },
    },
    {
      path: '/my/bookings/:bookingId',
      component: CustomerBookingDetailView,
      meta: { requiresCustomerAuth: true },
    },
  ],
})

declare module 'vue-router' {
  interface RouteMeta {
    requiresCustomerAuth?: boolean
  }
}

router.beforeEach((to) => {
  if (to.meta.requiresCustomerAuth && !hasStoredSession()) {
    return {
      name: 'customer-login',
      query: { redirect: to.fullPath },
    }
  }
})

export default router
