import { ref, reactive, computed } from 'vue'

export function useFormValidation(initialValues = {}, rules = {}) {
  const values = reactive({ ...initialValues })
  const errors = ref({})
  const touched = ref({})
  const isSubmitting = ref(false)
  const submitCount = ref(0)

  const isValid = computed(() => {
    return Object.keys(errors.value).length === 0
  })

  const isDirty = computed(() => {
    return Object.keys(touched.value).length > 0
  })

  const validateField = (field, value = values[field]) => {
    const fieldRules = rules[field]
    if (!fieldRules) {
      delete errors.value[field]
      return true
    }

    const fieldErrors = []

    // Handle array of rules or single rule
    const rulesArray = Array.isArray(fieldRules) ? fieldRules : [fieldRules]

    for (const rule of rulesArray) {
      if (typeof rule === 'function') {
        const result = rule(value, values)
        if (result !== true && result) {
          fieldErrors.push(result)
        }
      } else if (typeof rule === 'object') {
        const { validator, message } = rule
        const result = validator(value, values)
        if (result !== true && result) {
          fieldErrors.push(message || result)
        }
      }
    }

    if (fieldErrors.length > 0) {
      errors.value[field] = fieldErrors[0] // Show first error
      return false
    } else {
      delete errors.value[field]
      return true
    }
  }

  const validateAllFields = () => {
    let isFormValid = true

    for (const field in rules) {
      const isFieldValid = validateField(field)
      if (!isFieldValid) {
        isFormValid = false
      }
    }

    return isFormValid
  }

  const handleInput = (field, value) => {
    values[field] = value
    touched.value[field] = true

    // Validate on input if field was already touched and has errors
    if (errors.value[field]) {
      validateField(field, value)
    }
  }

  const handleBlur = (field) => {
    touched.value[field] = true
    validateField(field)
  }

  const handleSubmit = async (submitFn) => {
    isSubmitting.value = true
    submitCount.value++

    // Mark all fields as touched
    for (const field in rules) {
      touched.value[field] = true
    }

    // Validate all fields
    const isFormValid = validateAllFields()

    try {
      if (isFormValid) {
        await submitFn(values)
        // Reset form on successful submission if desired
        // reset()
      }
    } catch (error) {
      // Handle submit errors
      if (error.response?.data?.errors) {
        // Server-side validation errors
        errors.value = { ...errors.value, ...error.response.data.errors }
      }
      throw error
    } finally {
      isSubmitting.value = false
    }

    return isFormValid
  }

  const reset = () => {
    Object.assign(values, initialValues)
    errors.value = {}
    touched.value = {}
    isSubmitting.value = false
    submitCount.value = 0
  }

  const setFieldError = (field, error) => {
    errors.value[field] = error
  }

  const clearFieldError = (field) => {
    delete errors.value[field]
  }

  const setFieldValue = (field, value) => {
    values[field] = value
  }

  const getFieldProps = (field) => {
    return {
      value: values[field],
      error: errors.value[field],
      touched: touched.value[field],
      onInput: (value) => handleInput(field, value),
      onBlur: () => handleBlur(field)
    }
  }

  return {
    // State
    values,
    errors,
    touched,
    isSubmitting,
    submitCount,

    // Computed
    isValid,
    isDirty,

    // Methods
    validateField,
    validateAllFields,
    handleInput,
    handleBlur,
    handleSubmit,
    reset,
    setFieldError,
    clearFieldError,
    setFieldValue,
    getFieldProps
  }
}

// Common validation rules
export const validators = {
  required: (message = 'This field is required') => (value) => {
    if (value === null || value === undefined || value === '') {
      return message
    }
    return true
  },

  minLength: (min, message) => (value) => {
    if (!value) return true // Let required handle empty values
    if (value.length < min) {
      return message || `Must be at least ${min} characters long`
    }
    return true
  },

  maxLength: (max, message) => (value) => {
    if (!value) return true
    if (value.length > max) {
      return message || `Must be no more than ${max} characters long`
    }
    return true
  },

  email: (message = 'Please enter a valid email address') => (value) => {
    if (!value) return true
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(value)) {
      return message
    }
    return true
  },

  pattern: (regex, message) => (value) => {
    if (!value) return true
    if (!regex.test(value)) {
      return message || 'Invalid format'
    }
    return true
  },

  numeric: (message = 'Please enter a valid number') => (value) => {
    if (!value) return true
    if (isNaN(value) || isNaN(parseFloat(value))) {
      return message
    }
    return true
  },

  min: (min, message) => (value) => {
    if (!value) return true
    const num = parseFloat(value)
    if (num < min) {
      return message || `Must be at least ${min}`
    }
    return true
  },

  max: (max, message) => (value) => {
    if (!value) return true
    const num = parseFloat(value)
    if (num > max) {
      return message || `Must be no more than ${max}`
    }
    return true
  },

  custom: (validator, message) => (value, allValues) => {
    const result = validator(value, allValues)
    if (result !== true) {
      return message || result || 'Invalid value'
    }
    return true
  }
}