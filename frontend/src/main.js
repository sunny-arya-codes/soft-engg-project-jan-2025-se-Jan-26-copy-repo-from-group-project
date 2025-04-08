import './assets/main.css'
import './assets/tailwind.css'
import './assets/css/icons.css'

// Make sure TailwindCSS is initialized properly
document.addEventListener('DOMContentLoaded', () => {
  console.log('TailwindCSS initialized');
});

// Import material-symbols.js explicitly
import './plugins/material-symbols.js'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Toast from 'vue-toastification'
import '@fortawesome/fontawesome-free/css/all.css'
import 'vue-toastification/dist/index.css'
// Configure Material Symbols (ensure icons render correctly)

import App from './App.vue'
import router from './router'
import { ChatService } from './services/chat.service'

const app = createApp(App)

// Debug authentication token on startup 
console.log('============ AUTH DEBUGGING ============')
const token = localStorage.getItem('token')
if (token) {
  console.log('Token exists in localStorage:', token.substring(0, 10) + '...')
  
  // Check token format
  if (token.startsWith('"') || token.endsWith('"')) {
    console.warn('⚠️ Token has quote characters - might be incorrectly stored as JSON string')
  }
  
  if (token.includes('Bearer ')) {
    console.warn('⚠️ Token already includes Bearer prefix - might cause double prefix issues')
  }
  
  // Test request header format
  const testHeader = `Bearer ${token.replace(/^"|"$/g, '')}`
  console.log('Auth header would be: ' + testHeader.substring(0, 25) + '...')
} else {
  console.warn('⚠️ No authentication token found in localStorage')
}
console.log('=======================================')

// Toast configuration
const toastOptions = {
  position: 'top-right',
  timeout: 3000,
  closeOnClick: true,
  pauseOnFocusLoss: true,
  pauseOnHover: true,
  draggable: true,
  draggablePercent: 0.6,
  showCloseButtonOnHover: false,
  hideProgressBar: false,
  closeButton: 'button',
  icon: true,
  rtl: false
}

app.use(createPinia())
app.use(router)
app.use(Toast, toastOptions)

// Test function calling on startup (only in development)
if (process.env.NODE_ENV === 'development') {
  // Test function calling after app is mounted but only if authenticated
  setTimeout(async () => {
    try {
      // First check if user is authenticated before trying API call
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('Skipping function calling test - user not authenticated');
        return;
      }
      
      console.log('Testing function calling capabilities...');
      // Test the simplest function to avoid authentication issues
      const testPayload = {
        id: crypto.randomUUID(),
        query: 'What courses are available?',
        function_call: {
          name: 'web_search',
          arguments: { query: 'test function calling' }
        }
      }
      
      try {
        const result = await ChatService.sendMessage(testPayload);
        console.log('Function calling test result:', result);
        
        if (result.function_calls && result.function_calls.length > 0) {
          console.log('✅ Function calling is working properly!');
        } else {
          console.warn('⚠️ Function calling test did not return function calls.');
        }
      } catch (error) {
        // Only log the error if it's not an auth error (401)
        if (error.response && error.response.status === 401) {
          console.log('Authentication required for function calling test.');
        } else {
          console.error('❌ Function calling test failed:', error);
        }
      }
    } catch (error) {
      console.log('Skipping function calling test due to error:', error.message);
    }
  }, 3000); // Wait 3 seconds after app is mounted
}

app.mount('#app')
