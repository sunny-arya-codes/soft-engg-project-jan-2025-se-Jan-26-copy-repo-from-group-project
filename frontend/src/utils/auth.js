/**
 * Authentication utility functions
 */

/**
 * Get the authentication token from local storage
 * @returns {string|null} The authentication token or null if not found
 */
export const getAuthToken = () => {
  // First check for 'token' which is used by authService.js
  let token = localStorage.getItem('token');
  
  // Fallback to legacy 'auth_token' if not found
  if (!token) {
    token = localStorage.getItem('auth_token');
  }
  
  // Clean up token if needed
  if (token) {
    // Remove quotes if token is stored as JSON string
    token = token.replace(/^"|"$/g, '');
    
    // Ensure proper Bearer format
    if (!token.startsWith('Bearer ')) {
      token = `Bearer ${token}`;
    }
  }
  
  return token;
};

/**
 * Set the authentication token in local storage
 * @param {string} token - The token to store
 */
export const setAuthToken = (token) => {
  // Store using the current key format used by authService.js
  localStorage.setItem('token', token);
};

/**
 * Clear the authentication token from local storage
 */
export const clearAuthToken = () => {
  // Clear both possible keys
  localStorage.removeItem('token');
  localStorage.removeItem('auth_token');
};

/**
 * Check if the user is authenticated
 * @returns {boolean} True if the user is authenticated
 */
export const isAuthenticated = () => {
  return !!getAuthToken();
};

// Default export for backward compatibility
export default getAuthToken; 