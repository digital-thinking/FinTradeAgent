import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardSkeleton from '../DashboardSkeleton.vue'

describe('DashboardSkeleton', () => {
  it('renders skeleton structure correctly', () => {
    const wrapper = mount(DashboardSkeleton)
    
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
    expect(wrapper.findAll('.bg-gray-300').length).toBeGreaterThan(0)
  })

  it('renders stat cards skeleton', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have multiple stat card skeletons in grid
    expect(wrapper.find('.grid').exists()).toBe(true)
    expect(wrapper.findAll('.rounded-lg.bg-gray-200').length).toBeGreaterThan(3)
  })

  it('renders chart skeleton section', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have chart skeleton area
    const chartSkeleton = wrapper.find('[style*="height: 300px"]')
    expect(chartSkeleton.exists()).toBe(true)
  })

  it('renders recent activity skeleton', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have list items for recent activity
    expect(wrapper.findAll('.space-y-3').length).toBeGreaterThan(0)
    expect(wrapper.findAll('.h-4').length).toBeGreaterThan(5) // Multiple skeleton lines
  })

  it('applies responsive grid layout', () => {
    const wrapper = mount(DashboardSkeleton)
    
    const grid = wrapper.find('.grid')
    expect(grid.classes()).toContain('grid-cols-1')
    expect(grid.classes()).toContain('md:grid-cols-2')
    expect(grid.classes()).toContain('lg:grid-cols-4')
  })

  it('renders with proper animation classes', () => {
    const wrapper = mount(DashboardSkeleton)
    
    expect(wrapper.classes()).toContain('animate-pulse')
    // All skeleton elements should have gray background
    const skeletonElements = wrapper.findAll('.bg-gray-300, .bg-gray-200')
    expect(skeletonElements.length).toBeGreaterThan(10)
  })

  it('renders header skeleton', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have title area skeleton
    expect(wrapper.find('.h-8').exists()).toBe(true)
    expect(wrapper.find('.w-64').exists()).toBe(true)
  })

  it('renders portfolio overview skeleton', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have cards for portfolio overview
    const cards = wrapper.findAll('.rounded-lg.p-4')
    expect(cards.length).toBeGreaterThan(0)
  })

  it('handles different screen sizes appropriately', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Check responsive classes are present
    expect(wrapper.html()).toContain('sm:')
    expect(wrapper.html()).toContain('md:')
    expect(wrapper.html()).toContain('lg:')
  })

  it('renders execution status skeleton', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have skeleton for execution status indicators
    expect(wrapper.findAll('.rounded-full').length).toBeGreaterThan(0)
  })

  it('applies dark mode classes correctly', () => {
    const wrapper = mount(DashboardSkeleton)
    
    expect(wrapper.html()).toContain('dark:bg-gray-700')
    expect(wrapper.html()).toContain('dark:bg-gray-600')
  })

  it('renders without errors when no props provided', () => {
    expect(() => {
      mount(DashboardSkeleton)
    }).not.toThrow()
  })

  it('maintains consistent spacing and layout', () => {
    const wrapper = mount(DashboardSkeleton)
    
    expect(wrapper.find('.space-y-6').exists()).toBe(true)
    expect(wrapper.find('.gap-6').exists()).toBe(true)
  })

  it('includes various skeleton element sizes', () => {
    const wrapper = mount(DashboardSkeleton)
    
    // Should have different heights for variety
    expect(wrapper.find('.h-4').exists()).toBe(true)
    expect(wrapper.find('.h-6').exists()).toBe(true)
    expect(wrapper.find('.h-8').exists()).toBe(true)
    expect(wrapper.find('.h-12').exists()).toBe(true)
  })

  it('uses proper rounded corners for skeleton elements', () => {
    const wrapper = mount(DashboardSkeleton)
    
    expect(wrapper.find('.rounded').exists()).toBe(true)
    expect(wrapper.find('.rounded-lg').exists()).toBe(true)
    expect(wrapper.find('.rounded-full').exists()).toBe(true)
  })
})