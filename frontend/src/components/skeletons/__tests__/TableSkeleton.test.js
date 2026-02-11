import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TableSkeleton from '../TableSkeleton.vue'

describe('TableSkeleton', () => {
  it('renders basic table skeleton structure', () => {
    const wrapper = mount(TableSkeleton)
    
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.find('thead').exists()).toBe(true)
    expect(wrapper.find('tbody').exists()).toBe(true)
    expect(wrapper.find('.animate-pulse').exists()).toBe(true)
  })

  it('uses default column count when not specified', () => {
    const wrapper = mount(TableSkeleton)
    
    const headerCells = wrapper.findAll('th')
    expect(headerCells.length).toBeGreaterThan(3) // Default should be around 4-5 columns
  })

  it('applies custom column count', () => {
    const wrapper = mount(TableSkeleton, {
      props: { columns: 6 }
    })
    
    const headerCells = wrapper.findAll('th')
    expect(headerCells.length).toBe(6)
  })

  it('uses default row count when not specified', () => {
    const wrapper = mount(TableSkeleton)
    
    const dataRows = wrapper.findAll('tbody tr')
    expect(dataRows.length).toBeGreaterThan(3) // Default should be around 5 rows
  })

  it('applies custom row count', () => {
    const wrapper = mount(TableSkeleton, {
      props: { rows: 8 }
    })
    
    const dataRows = wrapper.findAll('tbody tr')
    expect(dataRows.length).toBe(8)
  })

  it('generates correct number of cells per row', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        columns: 4,
        rows: 3
      }
    })
    
    const dataRows = wrapper.findAll('tbody tr')
    dataRows.forEach(row => {
      const cells = row.findAll('td')
      expect(cells.length).toBe(4)
    })
  })

  it('renders header skeleton elements', () => {
    const wrapper = mount(TableSkeleton, {
      props: { columns: 3 }
    })
    
    const headerCells = wrapper.findAll('th')
    headerCells.forEach(cell => {
      expect(cell.find('.bg-gray-300').exists()).toBe(true)
      expect(cell.find('.h-4').exists()).toBe(true)
    })
  })

  it('renders data cell skeleton elements', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        columns: 3,
        rows: 2
      }
    })
    
    const dataCells = wrapper.findAll('tbody td')
    dataCells.forEach(cell => {
      expect(cell.find('.bg-gray-200').exists()).toBe(true)
      expect(cell.find('.h-4').exists()).toBe(true)
    })
  })

  it('applies proper table styling classes', () => {
    const wrapper = mount(TableSkeleton)
    
    expect(wrapper.find('table').classes()).toContain('w-full')
    expect(wrapper.find('table').classes()).toContain('table-auto')
  })

  it('shows table borders when bordered prop is true', () => {
    const wrapper = mount(TableSkeleton, {
      props: { bordered: true }
    })
    
    expect(wrapper.find('table').classes()).toContain('border')
    expect(wrapper.findAll('.border-b').length).toBeGreaterThan(0)
  })

  it('hides table borders by default', () => {
    const wrapper = mount(TableSkeleton)
    
    expect(wrapper.find('table').classes()).not.toContain('border')
  })

  it('applies striped rows when striped prop is true', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        striped: true,
        rows: 4
      }
    })
    
    const evenRows = wrapper.findAll('tbody tr:nth-child(even)')
    evenRows.forEach(row => {
      expect(row.classes()).toContain('bg-gray-50')
    })
  })

  it('applies hover effects when hoverable prop is true', () => {
    const wrapper = mount(TableSkeleton, {
      props: { hoverable: true }
    })
    
    const dataRows = wrapper.findAll('tbody tr')
    dataRows.forEach(row => {
      expect(row.classes()).toContain('hover:bg-gray-100')
    })
  })

  it('uses compact sizing when compact prop is true', () => {
    const wrapper = mount(TableSkeleton, {
      props: { compact: true }
    })
    
    const cells = wrapper.findAll('th, td')
    cells.forEach(cell => {
      expect(cell.classes()).toContain('px-2')
      expect(cell.classes()).toContain('py-1')
    })
  })

  it('uses default sizing when compact is false', () => {
    const wrapper = mount(TableSkeleton, {
      props: { compact: false }
    })
    
    const cells = wrapper.findAll('th, td')
    cells.forEach(cell => {
      expect(cell.classes()).toContain('px-4')
      expect(cell.classes()).toContain('py-3')
    })
  })

  it('renders with varying skeleton widths for natural look', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        columns: 4,
        rows: 3
      }
    })
    
    const skeletonElements = wrapper.findAll('.bg-gray-200, .bg-gray-300')
    const widthClasses = skeletonElements.map(el => 
      el.classes().find(c => c.startsWith('w-'))
    )
    
    // Should have different width classes for variety
    const uniqueWidths = new Set(widthClasses.filter(Boolean))
    expect(uniqueWidths.size).toBeGreaterThan(1)
  })

  it('applies dark mode styling correctly', () => {
    const wrapper = mount(TableSkeleton)
    
    expect(wrapper.html()).toContain('dark:bg-gray-700')
    expect(wrapper.html()).toContain('dark:bg-gray-600')
  })

  it('shows action column skeleton when showActions prop is true', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        showActions: true,
        columns: 3
      }
    })
    
    // Should have 3 data columns + 1 action column
    const headerCells = wrapper.findAll('th')
    expect(headerCells.length).toBe(4)
    
    // Action column should have different skeleton (typically shorter)
    const actionCells = wrapper.findAll('tbody tr td:last-child')
    actionCells.forEach(cell => {
      expect(cell.find('.rounded').exists()).toBe(true) // Action buttons are typically rounded
    })
  })

  it('renders loading indicator in header when specified', () => {
    const wrapper = mount(TableSkeleton, {
      props: { showLoadingHeader: true }
    })
    
    expect(wrapper.find('thead').find('.animate-spin').exists()).toBe(true)
  })

  it('handles empty state gracefully', () => {
    const wrapper = mount(TableSkeleton, {
      props: { 
        columns: 0,
        rows: 0
      }
    })
    
    expect(wrapper.find('table').exists()).toBe(true)
    expect(wrapper.findAll('th').length).toBe(0)
    expect(wrapper.findAll('tbody tr').length).toBe(0)
  })

  it('maintains consistent animation timing', () => {
    const wrapper = mount(TableSkeleton)
    
    const animatedElements = wrapper.findAll('.animate-pulse')
    expect(animatedElements.length).toBeGreaterThan(10) // Table should have many pulsing elements
  })

  it('applies responsive table classes', () => {
    const wrapper = mount(TableSkeleton)
    
    const tableWrapper = wrapper.find('.overflow-x-auto')
    expect(tableWrapper.exists()).toBe(true)
  })

  it('renders without errors with all props', () => {
    expect(() => {
      mount(TableSkeleton, {
        props: {
          columns: 5,
          rows: 10,
          bordered: true,
          striped: true,
          hoverable: true,
          compact: true,
          showActions: true,
          showLoadingHeader: true
        }
      })
    }).not.toThrow()
  })
})