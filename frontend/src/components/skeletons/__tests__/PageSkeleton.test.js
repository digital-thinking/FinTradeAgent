import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PageSkeleton from '../PageSkeleton.vue'

describe('PageSkeleton', () => {
  it('renders basic page skeleton structure', () => {
    const wrapper = mount(PageSkeleton)
    
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
    expect(wrapper.find('.space-y-6').exists()).toBe(true)
  })

  it('renders header skeleton by default', () => {
    const wrapper = mount(PageSkeleton)
    
    expect(wrapper.find('.h-8').exists()).toBe(true) // Title skeleton
    expect(wrapper.find('.h-4').exists()).toBe(true) // Subtitle skeleton
  })

  it('renders table type skeleton correctly', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'table' }
    })
    
    // Should have table structure
    expect(wrapper.findAll('.grid').length).toBeGreaterThan(0)
    expect(wrapper.findAll('.border-b').length).toBeGreaterThan(0)
  })

  it('renders cards type skeleton correctly', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'cards' }
    })
    
    // Should have card grid layout
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.findAll('.rounded-lg').length).toBeGreaterThan(3)
  })

  it('renders form type skeleton correctly', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'form' }
    })
    
    // Should have form field skeletons
    expect(wrapper.findAll('.space-y-4').length).toBeGreaterThan(0)
    expect(wrapper.findAll('.h-10').length).toBeGreaterThan(3) // Input field heights
  })

  it('renders dashboard type skeleton correctly', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'dashboard' }
    })
    
    // Should have dashboard-specific layout
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.findAll('.rounded-lg').length).toBeGreaterThan(4)
  })

  it('respects showHeader prop', () => {
    const wrapper = mount(PageSkeleton, {
      props: { showHeader: false }
    })
    
    // Header skeleton should not be present
    const headerElements = wrapper.findAll('.h-8')
    const hasHeaderSkeleton = headerElements.some(el => 
      el.classes().includes('w-64') || el.classes().includes('w-48')
    )
    expect(hasHeaderSkeleton).toBe(false)
  })

  it('applies custom item count for table type', () => {
    const wrapper = mount(PageSkeleton, {
      props: { 
        type: 'table',
        itemCount: 3
      }
    })
    
    // Should have 3 table rows + header
    const rows = wrapper.findAll('.grid.grid-cols-4, .grid.grid-cols-5, .grid.grid-cols-6')
    expect(rows.length).toBeGreaterThanOrEqual(3)
  })

  it('applies custom item count for cards type', () => {
    const wrapper = mount(PageSkeleton, {
      props: { 
        type: 'cards',
        itemCount: 6
      }
    })
    
    // Should have 6 card skeletons
    const cards = wrapper.findAll('.rounded-lg.bg-gray-200')
    expect(cards.length).toBeGreaterThanOrEqual(6)
  })

  it('applies custom item count for form type', () => {
    const wrapper = mount(PageSkeleton, {
      props: { 
        type: 'form',
        itemCount: 4
      }
    })
    
    // Should have 4 form field skeletons
    const formFields = wrapper.findAll('.h-10')
    expect(formFields.length).toBeGreaterThanOrEqual(4)
  })

  it('uses default item count when not specified', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'table' }
    })
    
    // Should use default count (typically 5)
    const skeletonElements = wrapper.findAll('.bg-gray-300, .bg-gray-200')
    expect(skeletonElements.length).toBeGreaterThan(10)
  })

  it('applies proper spacing and layout classes', () => {
    const wrapper = mount(PageSkeleton)
    
    expect(wrapper.find('.space-y-6').exists()).toBe(true)
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
  })

  it('renders action buttons skeleton when applicable', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'table' }
    })
    
    // Should have button-like skeletons in header area
    expect(wrapper.findAll('.rounded').length).toBeGreaterThan(5)
  })

  it('handles responsive grid layouts', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'cards' }
    })
    
    const grid = wrapper.find('.grid')
    expect(grid.classes()).toContain('grid-cols-1')
    expect(grid.classes().some(c => c.includes('md:') || c.includes('lg:'))).toBe(true)
  })

  it('applies dark mode styling', () => {
    const wrapper = mount(PageSkeleton)
    
    expect(wrapper.html()).toContain('dark:bg-gray-700')
    expect(wrapper.html()).toContain('dark:bg-gray-600')
  })

  it('renders search/filter skeleton when appropriate', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'table' }
    })
    
    // Should have search bar skeleton
    expect(wrapper.findAll('.h-10.rounded').length).toBeGreaterThan(0)
  })

  it('maintains consistent skeleton element styling', () => {
    const wrapper = mount(PageSkeleton)
    
    const skeletonElements = wrapper.findAll('.bg-gray-200, .bg-gray-300')
    skeletonElements.forEach(element => {
      expect(element.classes()).toContain('animate-pulse')
    })
  })

  it('renders without errors for all skeleton types', () => {
    const types = ['table', 'cards', 'form', 'dashboard']
    
    types.forEach(type => {
      expect(() => {
        mount(PageSkeleton, { props: { type } })
      }).not.toThrow()
    })
  })

  it('handles mixed content layouts', () => {
    const wrapper = mount(PageSkeleton, {
      props: { type: 'dashboard' }
    })
    
    // Should have both cards and table-like structures
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.findAll('.rounded-lg').length).toBeGreaterThan(2)
    expect(wrapper.findAll('.h-4, .h-6, .h-8').length).toBeGreaterThan(10)
  })
})