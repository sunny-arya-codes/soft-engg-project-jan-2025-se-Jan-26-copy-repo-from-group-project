import axios from 'axios'
import useAuthStore from '@/stores/useAuthStore'

// Determine the base URL for API requests
let baseURL = ''

// Check environment
if (process.env.NODE_ENV === 'production') {
  // Use the production API URL
  baseURL = '/api/v1'
} else {
  // Use local development server
  baseURL = 'http://localhost:8000/api/v1'
}

// Create an axios instance with the base URL
const api = axios.create({
  baseURL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
})

// Add logging for all requests
const logRequest = (config) => {
  console.log(`🚀 API REQUEST: ${config.method.toUpperCase()} ${config.url}`, config.params || {})
  return config
}

// Add logging for all responses
const logResponse = (response) => {
  console.log(`✅ API RESPONSE: ${response.config.method.toUpperCase()} ${response.config.url}`, response.status)
  return response
}

// Add a request interceptor to add the auth token to requests
api.interceptors.request.use(
  config => {
    // Apply request logging
    logRequest(config)
    
    // Get the auth token from the store or localStorage
    const authStore = useAuthStore()
    let token = authStore.token
    
    // If token not in store, try localStorage directly
    if (!token) {
      token = localStorage.getItem('token')
    }

    // If token exists, process it and add to headers
    if (token) {
      // Clean up token - remove quotes if JSON stringified
      let cleanToken = token
      
      if (typeof cleanToken === 'string') {
        // Remove JSON quotes if present
        cleanToken = cleanToken.replace(/^"|"$/g, '')
        
        // Remove Bearer prefix if already included
        if (cleanToken.startsWith('Bearer ')) {
          cleanToken = cleanToken.substring(7)
        }
      }
      
      config.headers['Authorization'] = `Bearer ${cleanToken}`
      console.log(`Adding token to ${config.url}: Bearer ${cleanToken.substring(0, 10)}...`)
    } else {
      console.warn(`No auth token found for request to: ${config.url}`)
    }

    // Add a timestamp to prevent caching issues for GET requests
    if (config.method === 'get') {
      // Initialize params object if it doesn't exist
      config.params = config.params || {}

      // Only add timestamp if it hasn't been added manually
      if (!config.params['_t']) {
        config.params['_t'] = Date.now()
      }

      // Ensure Cache-Control header is set to prevent browser caching
      config.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
      config.headers['Pragma'] = 'no-cache'
      config.headers['Expires'] = '0'
    }

    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// Add a response interceptor for error handling
api.interceptors.response.use(
  response => {
    // Apply response logging
    return logResponse(response)
  },
  error => {
    console.error('API Error:', error)
    
    if (error.response) {
      console.error(`API Response Error: ${error.response.status} ${error.response.statusText}`, error.config.url)
    } else if (error.request) {
      console.error('API Request Error: No response received', error.config.url)
    }
    
    // Handle authentication errors
    if (error.response && error.response.status === 401) {
      // Get auth store and logout the user
      const authStore = useAuthStore()
      authStore.logout()
      
      // Redirect to login page if not already there
      const currentPath = window.location.pathname
      if (currentPath !== '/login') {
        window.location.href = '/login?redirect=' + encodeURIComponent(currentPath)
      }
    }

    return Promise.reject(error)
  }
)

// Helper function to check if the API is reachable
export const checkApiHealth = async () => {
  try {
    // Try to reach the API health endpoint
    const response = await api.get('/health', { timeout: 5000 })
    return response.status === 200
  } catch (error) {
    console.error('API health check failed:', error)
    return false
  }
}

export default api
