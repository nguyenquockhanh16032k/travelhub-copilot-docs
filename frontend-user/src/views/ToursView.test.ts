// @vitest-environment happy-dom
import { defineComponent, nextTick, reactive } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'
import type { TourPage } from '../types/tour'

const mocks = vi.hoisted(() => ({
  listTours: vi.fn(),
  route: null as unknown,
  push: vi.fn(),
  replace: vi.fn(),
}))

vi.mock('../services/tours', () => ({
  listTours: mocks.listTours,
}))

vi.mock('vue-router', async () => {
  const actual = await vi.importActual<typeof import('vue-router')>('vue-router')
  return {
    ...actual,
    useRoute: () => mocks.route,
    useRouter: () => ({
      push: mocks.push,
      replace: mocks.replace,
    }),
  }
})

import ToursView from './ToursView.vue'

const SlotStub = defineComponent({
  template: '<div><slot /><slot name="append" /><slot name="prepend" /></div>',
})

const FieldStub = defineComponent({
  props: {
    modelValue: {
      type: [String, Number, Boolean],
      default: '',
    },
    label: {
      type: String,
      default: '',
    },
  },
  emits: ['update:modelValue'],
  setup(_props, { emit }) {
    function update(event: Event): void {
      emit('update:modelValue', (event.target as HTMLInputElement).value)
    }
    return { update }
  },
  template: `
    <label>
      <span>{{ label }}</span>
      <input :value="modelValue" @input="update">
    </label>
  `,
})

const ButtonStub = defineComponent({
  props: {
    type: {
      type: String,
      default: 'button',
    },
  },
  emits: ['click'],
  template: '<button :type="type" @click="$emit(\'click\', $event)"><slot /></button>',
})

const stubs = {
  VAlert: SlotStub,
  VAvatar: SlotStub,
  VBtn: ButtonStub,
  VCard: SlotStub,
  VCardActions: SlotStub,
  VCardItem: SlotStub,
  VCardSubtitle: SlotStub,
  VCardText: SlotStub,
  VCardTitle: SlotStub,
  VChip: SlotStub,
  VCol: SlotStub,
  VContainer: SlotStub,
  VIcon: SlotStub,
  VPagination: SlotStub,
  VProgressLinear: defineComponent({
    template: '<div aria-label="Loading tours"></div>',
  }),
  VRow: SlotStub,
  VSelect: FieldStub,
  VSwitch: FieldStub,
  VTextField: FieldStub,
}

function emptyPage(): TourPage {
  return {
    items: [],
    total: 0,
    page: 1,
    size: 12,
    pages: 0,
    currencies: [],
  }
}

function pageWithTour(title: string): TourPage {
  return {
    items: [
      {
        id: title,
        title,
        slug: title.toLowerCase().replaceAll(' ', '-'),
        description: null,
        duration_days: 2,
        destination: 'Coast',
        status: 'published',
        starting_prices: [],
        next_departure: null,
        has_available_departure: false,
      },
    ],
    total: 1,
    page: 1,
    size: 12,
    pages: 1,
    currencies: [],
  }
}

function mountToursView() {
  return mount(ToursView, {
    global: {
      stubs,
      renderStubDefaultSlot: true,
    },
  })
}

describe('ToursView', () => {
  let routeState: { path: string; query: LocationQuery }

  beforeEach(() => {
    vi.clearAllMocks()
    routeState = reactive({
      path: '/tours',
      query: {} as LocationQuery,
    })
    mocks.route = routeState
    mocks.push.mockImplementation(
      async (location: { query: LocationQueryRaw }) => {
        routeState.query = location.query as LocationQuery
      },
    )
    mocks.replace.mockImplementation(
      async (location: { query: LocationQueryRaw }) => {
        routeState.query = location.query as LocationQuery
      },
    )
    mocks.listTours.mockResolvedValue(emptyPage())
  })

  it('shows loading and empty states', async () => {
    let resolveRequest!: (page: TourPage) => void
    mocks.listTours.mockReturnValue(
      new Promise<TourPage>((resolve) => {
        resolveRequest = resolve
      }),
    )

    const wrapper = mountToursView()
    await nextTick()
    expect(wrapper.find('[aria-label="Loading tours"]').exists()).toBe(true)

    resolveRequest(emptyPage())
    await flushPromises()
    expect(wrapper.text()).toContain(
      'No tours match these search criteria.',
    )
  })

  it('restores URL filters and clears them from the URL', async () => {
    routeState.query = {
      keyword: 'beach',
      destination: 'Da Lat',
      page: '2',
    }
    const wrapper = mountToursView()
    await flushPromises()

    expect(mocks.listTours).toHaveBeenNthCalledWith(
      1,
      2,
      12,
      expect.objectContaining({ keyword: 'beach', destination: 'Da Lat' }),
      expect.any(AbortSignal),
    )

    const clearButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Clear all')
    expect(clearButton).toBeDefined()
    await clearButton!.trigger('click')
    await flushPromises()

    expect(mocks.push).toHaveBeenCalledWith({
      path: '/tours',
      query: {},
    })
    expect(routeState.query).toEqual({})
    expect(mocks.listTours).toHaveBeenLastCalledWith(
      1,
      12,
      expect.objectContaining({ keyword: '', destination: '' }),
      expect.any(AbortSignal),
    )
  })

  it('prevents an older response from replacing newer search results', async () => {
    let resolveFirst!: (page: TourPage) => void
    mocks.listTours
      .mockReturnValueOnce(
        new Promise<TourPage>((resolve) => {
          resolveFirst = resolve
        }),
      )
      .mockResolvedValueOnce(pageWithTour('New result'))

    routeState.query = { keyword: 'old' }
    const wrapper = mountToursView()
    await nextTick()
    routeState.query = { keyword: 'new' }
    await flushPromises()

    expect(wrapper.text()).toContain('New result')
    resolveFirst(pageWithTour('Old result'))
    await flushPromises()
    expect(wrapper.text()).toContain('New result')
    expect(wrapper.text()).not.toContain('Old result')
  })
})
