import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseCard from '../BaseCard.vue'

describe('BaseCard', () => {
  it('renders basic card structure', () => {
    const wrapper = mount(BaseCard)
    
    expect(wrapper.classes()).toContain('bg-white')
    expect(wrapper.classes()).toContain('dark:bg-gray-800')
    expect(wrapper.classes()).toContain('rounded-lg')
    expect(wrapper.classes()).toContain('shadow-sm')
  })

  it('renders with padding when not noPadding', () => {
    const wrapper = mount(BaseCard)
    expect(wrapper.classes()).toContain('p-6')
  })

  it('renders without padding when noPadding is true', () => {
    const wrapper = mount(BaseCard, {
      props: { noPadding: true }
    })
    expect(wrapper.classes()).not.toContain('p-6')
  })

  it('renders header slot content', () => {
    const wrapper = mount(BaseCard, {
      slots: {
        header: '<h2>Card Header</h2>'
      }
    })
    
    expect(wrapper.html()).toContain('<h2>Card Header</h2>')
    const headerDiv = wrapper.find('[class*="border-b"]')
    expect(headerDiv.exists()).toBe(true)
  })

  it('renders default slot content', () => {
    const wrapper = mount(BaseCard, {
      slots: {
        default: '<p>Card content</p>'
      }
    })
    
    expect(wrapper.html()).toContain('<p>Card content</p>')
  })

  it('renders footer slot content', () => {
    const wrapper = mount(BaseCard, {
      slots: {
        footer: '<div>Card Footer</div>'
      }
    })
    
    expect(wrapper.html()).toContain('<div>Card Footer</div>')
    const footerDiv = wrapper.find('[class*="border-t"]')
    expect(footerDiv.exists()).toBe(true)
  })

  it('renders all slots together correctly', () => {
    const wrapper = mount(BaseCard, {
      slots: {
        header: '<h2>Header</h2>',
        default: '<p>Body</p>',
        footer: '<div>Footer</div>'
      }
    })
    
    expect(wrapper.html()).toContain('<h2>Header</h2>')
    expect(wrapper.html()).toContain('<p>Body</p>')
    expect(wrapper.html()).toContain('<div>Footer</div>')
  })

  it('applies hover styles when hoverable', () => {
    const wrapper = mount(BaseCard, {
      props: { hoverable: true }
    })
    
    expect(wrapper.classes()).toContain('hover:shadow-md')
    expect(wrapper.classes()).toContain('transition-shadow')
  })

  it('can be rendered as clickable element', () => {
    const wrapper = mount(BaseCard, {
      props: { clickable: true }
    })
    
    expect(wrapper.classes()).toContain('cursor-pointer')
  })

  it('emits click event when clickable and clicked', async () => {
    const wrapper = mount(BaseCard, {
      props: { clickable: true }
    })
    
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('does not emit click when not clickable', async () => {
    const wrapper = mount(BaseCard)
    
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeFalsy()
  })
})