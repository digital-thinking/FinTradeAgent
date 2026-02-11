import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ command, mode }) => {
  // Load environment variables
  const env = loadEnv(mode, process.cwd(), '')
  
  // Production-specific configuration
  const isProduction = mode === 'production'
  
  return {
    plugins: [
      vue({
        // Production optimizations
        template: {
          compilerOptions: {
            // Remove comments in production
            comments: !isProduction
          }
        }
      })
    ],
    
    // Server configuration
    server: {
      port: 3000,
      host: true, // Allow external connections
      cors: true
    },
    
    // Production preview server configuration
    preview: {
      port: 4173,
      host: true,
      cors: true
    },
    build: {
      // Build optimization for production
      target: ['es2020', 'edge88', 'firefox78', 'chrome87', 'safari14'],
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: isProduction,
          drop_debugger: isProduction,
          pure_funcs: isProduction ? ['console.log', 'console.info', 'console.debug'] : [],
          // Additional production optimizations
          passes: 2,
          unsafe_arrows: true,
          unsafe_methods: true,
          unsafe_proto: true,
          unsafe_regexp: true,
          unsafe_undefined: true
        },
        mangle: {
          properties: {
            regex: /^_/
          }
        },
        format: {
          comments: false
        }
      },
      
      // CSS optimization
      cssCodeSplit: true,
      cssMinify: 'lightningcss',
      
      // Asset optimization
      assetsInlineLimit: 4096, // 4KB inline limit
    
      // Bundle optimization
      rollupOptions: {
        // Production build optimizations
        treeshake: {
          moduleSideEffects: false,
          propertyReadSideEffects: false,
          annotations: true
        },
        
        output: {
          // Manual chunk splitting for optimal caching
          manualChunks: (id) => {
            // Node modules vendor chunks
            if (id.includes('node_modules')) {
              // Core framework chunks
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
                return 'vendor-vue'
              }
              // Chart.js and visualization
              if (id.includes('chart.js') || id.includes('chartjs')) {
                return 'vendor-ui'
              }
              // HTTP and utility libraries
              if (id.includes('axios')) {
                return 'vendor-http'
              }
              // Other vendor libraries
              return 'vendor-misc'
            }
            
            // Page-based chunks for better code splitting
            if (id.includes('/pages/')) {
              if (id.includes('Portfolio')) return 'pages-portfolio'
              if (id.includes('Dashboard') || id.includes('Comparison')) return 'pages-analytics'
              if (id.includes('Trade')) return 'pages-trades'
              if (id.includes('System')) return 'pages-system'
              return 'pages-misc'
            }
            
            // Component chunks
            if (id.includes('/components/')) {
              if (id.includes('Chart') || id.includes('StatCard')) return 'components-charts'
              return 'components-common'
            }
          },
        
          // Asset naming with hashing for optimal caching
          chunkFileNames: (chunkInfo) => {
            return `assets/js/[name]-[hash].js`
          },
          assetFileNames: (assetInfo) => {
            let extType = assetInfo.name.split('.').at(1)
            if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType)) {
              extType = 'img'
            } else if (/woff2?|eot|ttf|otf/i.test(extType)) {
              extType = 'fonts'
            } else if (/css/i.test(extType)) {
              extType = 'css'
            }
            return `assets/${extType}/[name]-[hash][extname]`
          },
          
          // Output configuration for CDN deployment
          ...(env.VITE_CDN_BASE_URL && isProduction ? {
            publicPath: env.VITE_CDN_BASE_URL
          } : {})
        },
        
        // External dependencies for CDN loading (optional)
        external: isProduction ? [] : [], // Can add CDN externals here
      },
      
      // Production chunk size warnings
      chunkSizeWarningLimit: isProduction ? 1000 : 500,
      
      // Source maps configuration
      sourcemap: isProduction ? 'hidden' : true, // Hidden source maps for production debugging
      
      // Build output directory
      outDir: 'dist',
      emptyOutDir: true,
      
      // Production-specific build options
      ...(isProduction && {
        reportCompressedSize: true,
        // Enable build compression
        rollupOptions: {
          ...((env.VITE_ENABLE_ANALYTICS === 'true') && {
            plugins: []
          })
        }
      })
    },
  
  // Performance optimizations
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'chart.js'
    ],
    exclude: ['@vue/test-utils']
  },
  
  // Asset optimization
  assetsInclude: ['**/*.woff2'],
  
  // Resolve alias for cleaner imports
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@services': resolve(__dirname, 'src/services'),
      '@composables': resolve(__dirname, 'src/composables')
    }
  },
  
    // Testing configuration
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.js',
      coverage: {
        provider: 'c8',
        reporter: ['text', 'json', 'html'],
        exclude: [
          'node_modules/',
          'src/test/',
          '**/*.test.js',
          '**/*.spec.js',
          'src/main.js',
          'src/router/index.js'
        ],
        thresholds: {
          global: {
            branches: 80,
            functions: 80,
            lines: 80,
            statements: 80
          }
        }
      }
    },
    
    // Environment-specific configuration
    define: {
      __VUE_OPTIONS_API__: 'false',
      __VUE_PROD_DEVTOOLS__: 'false',
      // Global constants
      '__APP_VERSION__': JSON.stringify(process.env.npm_package_version || '1.0.0'),
      '__BUILD_TIME__': JSON.stringify(new Date().toISOString()),
      '__PRODUCTION__': JSON.stringify(isProduction)
    },
    
    // Production-specific optimizations
    ...(isProduction && {
      esbuild: {
        // Remove console.* calls in production
        pure: ['console.log', 'console.info', 'console.debug'],
        // Remove debugger statements
        drop: ['debugger'],
        // Keep function names for better stack traces
        keepNames: true
      }
    })
  }
})
