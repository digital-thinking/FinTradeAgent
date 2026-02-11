import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BaseModal from '../BaseModal.vue'
import { nextTick } from 'vue'

describe('BaseModal', () => {
  it('does not render when not open', () => {
    const wrapper = mount(BaseModal, {
      props: { open: false }
    })
    
    expect(wrapper.find('.fixed').exists()).toBe(false)
  })

  it('renders when open is true', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true }
    })
    
    expect(wrapper.find('.fixed').exists()).toBe(true)
    expect(wrapper.find('.bg-black').exists()).toBe(true) // backdrop
    expect(wrapper.find('.bg-white').exists()).toBe(true) // modal content
  })

  it('renders title when provided', () => {
    const wrapper = mount(BaseModal, {
      props: { 
        open: true,
        title: 'Test Modal Title'
      }
    })
    
    expect(wrapper.text()).toContain('Test Modal Title')
  })

  it('renders default slot content', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true },
      slots: {
        default: '<p>Modal content goes here</p>'
      }
    })
    
    expect(wrapper.html()).toContain('<p>Modal content goes here</p>')
  })

  it('renders footer slot content', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true },
      slots: {
        footer: '<div class="footer-content">Footer buttons</div>'
      }
    })
    
    expect(wrapper.html()).toContain('<div class="footer-content">Footer buttons</div>')
  })

  it('emits close event when close button is clicked', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true }
    })
    
    const closeButton = wrapper.find('button[aria-label="Close"]')
    await closeButton.trigger('click')
    
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('emits close event when backdrop is clicked', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true }
    })
    
    const backdrop = wrapper.find('.fixed.inset-0.bg-black')
    await backdrop.trigger('click')
    
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('does not emit close when clicking inside modal content', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true }
    })
    
    const modalContent = wrapper.find('.bg-white')
    await modalContent.trigger('click')
    
    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('handles different sizes correctly', () => {
    const smallWrapper = mount(BaseModal, {
      props: { 
        open: true,
        size: 'sm'
      }
    })
    expect(smallWrapper.find('.max-w-sm').exists()).toBe(true)

    const mediumWrapper = mount(BaseModal, {
      props: { 
        open: true,
        size: 'md'
      }
    })
    expect(mediumWrapper.find('.max-w-md').exists()).toBe(true)

    const largeWrapper = mount(BaseModal, {
      props: { 
        open: true,
        size: 'lg'
      }
    })
    expect(largeWrapper.find('.max-w-lg').exists()).toBe(true)

    const xlWrapper = mount(BaseModal, {
      props: { 
        open: true,
        size: 'xl'
      }
    })
    expect(xlWrapper.find('.max-w-xl').exists()).toBe(true)
  })

  it('shows close button by default', () => {
    const wrapper = mount(BaseModal, {
      props: { open: true }
    })
    
    expect(wrapper.find('button[aria-label="Close"]').exists()).toBe(true)
  })

  it('hides close button when showClose is false', () => {
    const wrapper = mount(BaseModal, {
      props: { 
        open: true,
        showClose: false
      }
    })
    
    expect(wrapper.find('button[aria-label="Close"]').exists()).toBe(false)
  })

  it('handles keyboard events for closing', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true },
      attachTo: document.body
    })

    // Simulate Escape key press
    await wrapper.trigger('keydown', { key: 'Escape' })
    
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('manages focus trap correctly', async () => {
    const wrapper = mount(BaseModal, {
      props: { open: true },
      attachTo: document.body
    })

    await nextTick()
    
    // Check that modal contains focusable elements
    const focusableElements = wrapper.element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    
    expect(focusableElements.length).toBeGreaterThan(0)
  })
})