import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '../StatCard.vue'

describe('StatCard', () => {
  const defaultProps = {
    title: 'Total Value',
    value: '$50,000',
    change: '+5.2%',
    changeType: 'positive'
  }

  it('renders basic stat card structure', () => {
    const wrapper = mount(StatCard, {
      props: defaultProps
    })
    
    expect(wrapper.text()).toContain('Total Value')
    expect(wrapper.text()).toContain('$50,000')
    expect(wrapper.text()).toContain('+5.2%')
  })

  it('displays title and value correctly', () => {
    const wrapper = mount(StatCard, {
      props: {
        title: 'Portfolio Count',
        value: '12'
      }
    })
    
    expect(wrapper.text()).toContain('Portfolio Count')
    expect(wrapper.text()).toContain('12')
  })

  it('shows change with positive styling', () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        change: '+10.5%',
        changeType: 'positive'
      }
    })
    
    expect(wrapper.text()).toContain('+10.5%')
    expect(wrapper.find('.text-green-600').exists()).toBe(true)
  })

  it('shows change with negative styling', () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        change: '-3.2%',
        changeType: 'negative'
      }
    })
    
    expect(wrapper.text()).toContain('-3.2%')
    expect(wrapper.find('.text-red-600').exists()).toBe(true)
  })

  it('shows change with neutral styling', () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        change: '0.0%',
        changeType: 'neutral'
      }
    })
    
    expect(wrapper.text()).toContain('0.0%')
    expect(wrapper.find('.text-gray-600').exists()).toBe(true)
  })

  it('works without change prop', () => {
    const wrapper = mount(StatCard, {
      props: {
        title: 'Static Value',
        value: '100'
      }
    })
    
    expect(wrapper.text()).toContain('Static Value')
    expect(wrapper.text()).toContain('100')
    // Should not contain change indicator
    expect(wrapper.text()).not.toContain('%')
  })

  it('renders with icon when provided', () => {
    const wrapper = mount(StatCard, {
      props: defaultProps,
      slots: {
        icon: '<svg data-testid="stat-icon">icon</svg>'
      }
    })
    
    expect(wrapper.find('[data-testid="stat-icon"]').exists()).toBe(true)
  })

  it('applies loading state correctly', () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        loading: true
      }
    })
    
    // Should show skeleton/loading state
    expect(wrapper.classes()).toContain('animate-pulse')
    expect(wrapper.find('.bg-gray-300').exists()).toBe(true)
  })

  it('handles clickable state', async () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        clickable: true
      }
    })
    
    expect(wrapper.classes()).toContain('cursor-pointer')
    expect(wrapper.classes()).toContain('hover:bg-gray-50')
    
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('shows tooltip when provided', () => {
    const wrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        tooltip: 'This is additional information'
      }
    })
    
    expect(wrapper.attributes('title')).toBe('This is additional information')
  })

  it('handles different size variants', () => {
    const smallWrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        size: 'sm'
      }
    })
    expect(smallWrapper.classes()).toContain('p-4')

    const largeWrapper = mount(StatCard, {
      props: {
        ...defaultProps,
        size: 'lg'
      }
    })
    expect(largeWrapper.classes()).toContain('p-8')
  })

  it('applies dark mode styling correctly', () => {
    const wrapper = mount(StatCard, {
      props: defaultProps
    })
    
    expect(wrapper.classes()).toContain('bg-white')
    expect(wrapper.classes()).toContain('dark:bg-gray-800')
    expect(wrapper.classes()).toContain('dark:text-white')
  })
})