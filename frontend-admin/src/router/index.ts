import { createRouter, createWebHistory } from 'vue-router'

import AdminLayout from '../layouts/AdminLayout.vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import ToursView from '../views/ToursView.vue'
import DeparturesView from '../views/DeparturesView.vue'
import CustomersView from '../views/CustomersView.vue'
import BookingsView from '../views/BookingsView.vue'
import PaymentsView from '../views/PaymentsView.vue'
import ItinerariesView from '../views/ItinerariesView.vue'
import GuidesView from '../views/GuidesView.vue'
import AssignmentsView from '../views/AssignmentsView.vue'
import SuppliersView from '../views/SuppliersView.vue'
import ExpensesView from '../views/ExpensesView.vue'
import ArticlesView from '../views/ArticlesView.vue'
import ReportsView from '../views/ReportsView.vue'
import UsersView from '../views/UsersView.vue'
import ForbiddenView from '../views/ForbiddenView.vue'
import { useAuthStore } from '../stores/auth'
import { hasPermission, type Permission } from '../utils/permissions'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: AuthLayout,
      meta: { public: true },
      children: [{ path: '', component: LoginView }],
    },
    {
      path: '/forbidden',
      component: ForbiddenView,
      meta: { public: true },
    },
    {
      path: '/',
      component: AdminLayout,
      redirect: '/dashboard',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'dashboard',
          component: DashboardView,
          meta: { permission: 'dashboard:read' },
        },
        {
          path: 'tours',
          component: ToursView,
          meta: { permission: 'tours:read' },
        },
        {
          path: 'departures',
          component: DeparturesView,
          meta: { permission: 'departures:read' },
        },
        {
          path: 'bookings',
          component: BookingsView,
          meta: { permission: 'bookings:read' },
        },
        {
          path: 'payments',
          component: PaymentsView,
          meta: { permission: 'payments:read' },
        },
        {
          path: 'customers',
          component: CustomersView,
          meta: { permission: 'customers:read' },
        },
        {
          path: 'itineraries',
          component: ItinerariesView,
          meta: { permission: 'itineraries:read' },
        },
        {
          path: 'guides',
          component: GuidesView,
          meta: { permission: 'guides:read' },
        },
        {
          path: 'assignments',
          component: AssignmentsView,
          meta: { permission: 'assignments:read' },
        },
        {
          path: 'suppliers',
          component: SuppliersView,
          meta: { permission: 'suppliers:read' },
        },
        {
          path: 'expenses',
          component: ExpensesView,
          meta: { permission: 'expenses:read' },
        },
        {
          path: 'articles',
          component: ArticlesView,
          meta: { permission: 'articles:read' },
        },
        {
          path: 'reports',
          component: ReportsView,
          meta: { permission: 'reports:read' },
        },
        {
          path: 'users',
          component: UsersView,
          meta: { permission: 'users:read' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    if (to.path === '/login' && auth.isAuthenticated) return '/dashboard'
    return true
  }

  if (!auth.isAuthenticated) {
    await auth.restoreSession()
  }
  if (!auth.isAuthenticated) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
  const permission = to.meta.permission as Permission | undefined
  if (permission && !hasPermission(auth.user?.roles, permission)) {
    return '/forbidden'
  }
  return true
})

export default router
