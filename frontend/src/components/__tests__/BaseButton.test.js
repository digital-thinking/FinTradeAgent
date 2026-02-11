import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseButton from '../BaseButton.vue'

describe('BaseButton', () => {
  it('renders with default props', () => {
    const wrapper = mount(BaseButton, {
      slots: { default: 'Click me' }
    })
    
    expect(wrapper.text()).toBe('Click me')
    expect(wrapper.classes()).toContain('px-4')
    expect(wrapper.classes()).toContain('py-2')
    expect(wrapper.attributes('type')).toBe('button')
  })

  it('renders different variants correctly', () => {
    const primaryWrapper = mount(BaseButton, {
      props: { variant: 'primary' },
      slots: { default: 'Primary' }
    })
    expect(primaryWrapper.classes()).toContain('bg-blue-600')

    const secondaryWrapper = mount(BaseButton, {
      props: { variant: 'secondary' },
      slots: { default: 'Secondary' }
    })
    expect(secondaryWrapper.classes()).toContain('bg-gray-200')

    const dangerWrapper = mount(BaseButton, {
      props: { variant: 'danger' },
      slots: { default: 'Danger' }
    })
    expect(dangerWrapper.classes()).toContain('bg-red-600')
  })

  it('renders different sizes correctly', () => {
    const smallWrapper = mount(BaseButton, {
      props: { size: 'sm' },
      slots: { default: 'Small' }
    })
    expect(smallWrapper.classes()).toContain('px-3')
    expect(smallWrapper.classes()).toContain('py-1.5')
    expect(smallWrapper.classes()).toContain('text-sm')

    const largeWrapper = mount(BaseButton, {
      props: { size: 'lg' },
      slots: { default: 'Large' }
    })
    expect(largeWrapper.classes()).toContain('px-6')
    expect(largeWrapper.classes()).toContain('py-3')
    expect(largeWrapper.classes()).toContain('text-lg')
  })

  it('handles disabled state correctly', () => {
    const wrapper = mount(BaseButton, {
      props: { disabled: true },
      slots: { default: 'Disabled' }
    })
    
    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.classes()).toContain('opacity-50')
    expect(wrapper.classes()).toContain('cursor-not-allowed')
  })

  it('handles loading state correctly', () => {
    const wrapper = mount(BaseButton, {
      props: { loading: true },
      slots: { default: 'Loading' }
    })
    
    expect(wrapper.attributes('disabled')).toBeDefined()
    expect(wrapper.classes()).toContain('opacity-50')
    expect(wrapper.text()).toBe('Loading...')
  })

  it('renders as different element types', () => {
    const linkWrapper = mount(BaseButton, {
      props: { as: 'a', href: 'https://example.com' },
      slots: { default: 'Link' }
    })
    
    expect(linkWrapper.element.tagName).toBe('A')
    expect(linkWrapper.attributes('href')).toBe('https://example.com')
  })

  it('emits click event when clicked', async () => {
    const wrapper = mount(BaseButton, {
      slots: { default: 'Click me' }
    })
    
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('does not emit click when disabled or loading', async () => {
    const disabledWrapper = mount(BaseButton, {
      props: { disabled: true },
      slots: { default: 'Disabled' }
    })
    
    await disabledWrapper.trigger('click')
    expect(disabledWrapper.emitted('click')).toBeFalsy()

    const loadingWrapper = mount(BaseButton, {
      props: { loading: true },
      slots: { default: 'Loading' }
    })
    
    await loadingWrapper.trigger('click')
    expect(loadingWrapper.emitted('click')).toBeFalsy()
  })

  it('applies full width class when block prop is true', () => {
    const wrapper = mount(BaseButton, {
      props: { block: true },
      slots: { default: 'Block button' }
    })
    
    expect(wrapper.classes()).toContain('w-full')
  })
})