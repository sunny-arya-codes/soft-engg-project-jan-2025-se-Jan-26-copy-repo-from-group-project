import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL;
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '';
const isDev = import.meta.env.MODE === 'development';

// Enable more verbose logging in development mode
const logLevel = isDev ? 'debug' : 'error';

// Custom logger with different log levels
const logger = {
    debug: (...args) => isDev && console.debug('[Auth Service]', ...args),
    log: (...args) => console.log('[Auth Service]', ...args),
    warn: (...args) => console.warn('[Auth Service]', ...args),
    error: (...args) => console.error('[Auth Service]', ...args),
};

const axiosInstance = axios.create({
    baseURL: `${API_URL}${API_PREFIX}`,
    withCredentials: true,
});

// Add request interceptor to include the token in every request
axiosInstance.interceptors.request.use(
    (config) => {
        // Skip adding token for login requests
        if (config.url && config.url.includes('/login')) {
            return config;
        }
        
        const token = localStorage.getItem('token');
        if (token) {
            // Clean up token - remove quotes and any 'Bearer ' prefix
            let cleanToken = token;
            
            // Remove quotes if token is stored as JSON string
            cleanToken = cleanToken.replace(/^"|"$/g, '');
            
            // Remove Bearer prefix if it was accidentally stored with the token
            if (cleanToken.startsWith('Bearer ')) {
                cleanToken = cleanToken.substring(7);
            }
            
            // Add the proper Authorization header
            config.headers.Authorization = `Bearer ${cleanToken}`;
            logger.debug(`Request to ${config.url} - Adding Authorization header: Bearer ${cleanToken.substring(0, 15)}...`);
        } else {
            logger.warn(`Request to ${config.url} - No token found`);
            // Refresh token or redirect to login if this is an authenticated endpoint
            // This helps prevent 403 errors by redirecting to login when no token is present
            if (!config.url.includes('/public/') && !config.url.includes('/login')) {
                const currentPath = window.location.pathname;
                // Only redirect if not already on login page to prevent loops
                if (!currentPath.includes('/login')) {
                    logger.warn('No token for authenticated endpoint - redirecting to login');
                    // Use a slight delay to allow the current request to complete
                    setTimeout(() => {
                        window.location.href = '/login?redirect=' + encodeURIComponent(currentPath);
                    }, 100);
                }
            }
        }

        // Log request details in development
        if (isDev) {
            logger.debug(`Request: ${config.method.toUpperCase()} ${config.url}`, config.data || {});
        }

        return config;
    },
    (error) => {
        logger.error('Request interceptor error:', error);
        return Promise.reject(error);
    }
);

// Add response interceptor for debugging
axiosInstance.interceptors.response.use(
    (response) => {
        logger.debug(`Response from ${response.config.url}: ${response.status}`,
            isDev ? response.data : '');
        return response;
    },
    (error) => {
        if (error.response) {
            logger.error(`Response error from ${error.config?.url || 'unknown'}: ${error.response.status}`,
                error.response.data);

            // Handle 401 errors (unauthorized)
            if (error.response.status === 401) {
                logger.warn('Unauthorized access detected - token may be invalid or expired');
                // We could trigger a token refresh here if needed
            }
        } else if (error.request) {
            logger.error('No response received:', error.request);
        } else {
            logger.error('Request error:', error.message);
        }
        return Promise.reject(error);
    }
);

export const authService = {
    // Initialize axios instance with credentials
    axiosInstance,

    // Login with Email & Password  
    async loginWithEmail(email, password) {
        try {
            logger.log('Logging in with email and password...');

            // Convert to form-urlencoded format
            const formData = new URLSearchParams();
            formData.append('username', email);
            formData.append('password', password);
            console.log('Login Request Data:', { username: email, password: '*****' });

            // Fix: Use proper relative URL and formData directly
            const response = await this.axiosInstance.post('/login', formData, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });
            
            logger.log('Login successful');
            logger.debug('User data:', response.data);
            
            if (!response.data || !response.data.access_token) {
                logger.error('Login response missing access_token:', response.data);
                return { 
                    success: false, 
                    message: 'Invalid response from server' 
                };
            }
            
            // Get the token and clean it up
            const token = response.data.access_token;
            
            // Save auth data to localStorage as plain string (not JSON)
            localStorage.setItem('token', token);
            console.log('Token saved to localStorage:', token.substring(0, 15) + '...');
            
            // Also update Pinia store if available
            try {
                const authStore = window.Pinia?.state?.value?.auth;
                if (authStore) {
                    authStore.token = token;
                    console.log('Token also updated in auth store');
                }
            } catch (storeError) {
                console.warn('Could not update auth store:', storeError);
            }
            
            // Debug full response to see actual structure
            console.log('Full login response structure:', JSON.stringify(response.data, null, 2));
            
            // Save user role if available from user object - ALWAYS NORMALIZE TO UPPERCASE
            if (response.data.user && response.data.user.role) {
                const originalRole = response.data.user.role;
                const normalizedRole = originalRole.toUpperCase();
                console.log(`AUTH SERVICE: Original role from backend: "${originalRole}", type: ${typeof originalRole}`);
                console.log(`AUTH SERVICE: Normalized role: "${normalizedRole}"`);
                localStorage.setItem('userRole', normalizedRole);
                console.log(`AUTH SERVICE: Saved userRole to localStorage: "${localStorage.getItem('userRole')}"`);
            } else {
                console.warn('No role found in login response user object');
            }
            
            return {
                success: true,
                access_token: response.data.access_token,
                user: response.data.user
            };
        } catch (error) {
            logger.error('Error logging in with email and password:', error.message);
            if (error.response) {
                logger.error(`Status: ${error.response.status}, Data:`, error.response.data);
                return {
                    success: false,
                    message: error.response.data?.detail || 'Login failed. Please check your credentials.',
                    status: error.response.status
                };
            }
            return { 
                success: false, 
                message: 'Network error while logging in' 
            };
        }
    },


    // Login with Google
    async loginWithGoogle() {
        // Use the correct path from OpenAPI: /api/v1/login/google
        const redirectUrl = `${API_URL}/api/v1/login/google`;
        logger.log('Redirecting to Google login:', redirectUrl);
        window.location.href = redirectUrl;
    },

    // Get current user
    async getCurrentUser() {
        try {
            // Clear cache if userRole in localStorage doesn't match cached data
            const localStorageRole = localStorage.getItem('userRole');
            if (this._cachedUserData && localStorageRole && 
                this._cachedUserData.role !== localStorageRole) {
                console.log(`getCurrentUser: Clearing mismatched cached data. Cache role: "${this._cachedUserData.role}", localStorage role: "${localStorageRole}"`);
                this._cachedUserData = null;
            }
            
            // Check if we already have the user data in cache
            if (this._cachedUserData) {
                logger.debug('Returning cached user data');
                return this._cachedUserData;
            }
            
            // Get auth token
            const token = localStorage.getItem('token');
            if (!token) {
                logger.warn('No auth token found in localStorage');
                return null;
            }
            
            // Get role from localStorage
            const userRole = localStorage.getItem('userRole') || 'STUDENT';
            console.log(`getCurrentUser: Retrieved role from localStorage: "${userRole}"`);
            
            // Create a simple user object from localStorage data
            const userData = {
                id: 'local-user', // Placeholder ID
                name: localStorage.getItem('userName') || 'User',
                email: localStorage.getItem('userEmail') || '',
                role: userRole.toUpperCase(),
                is_google_user: false,
                has_password: true
            };

            logger.debug('Created user data from localStorage:', userData);
            console.log(`getCurrentUser: Returning user data with role: "${userData.role}"`);
            
            // Cache the user data for subsequent calls
            this._cachedUserData = userData;
            
            return userData;
        } catch (error) {
            logger.error('Error getting current user:', error.message);
            return null;
        }
    },

    // Check if the user is currently authenticated
    async isAuthenticated() {
        try {
            // Check if token exists in localStorage
            const token = localStorage.getItem('token');
            if (!token) {
                logger.warn('No auth token found in localStorage');
                return false;
            }
            
            // Just consider authenticated if token exists
            logger.debug('Token exists in localStorage, considering authenticated');
            return true;
            
        } catch (error) {
            logger.error('Error in isAuthenticated check:', error.message);
            return false;
        }
    },

    // Refresh token
    async refreshToken() {
        try {
            logger.log('Refreshing token...');
            const token = localStorage.getItem('token');
            
            if (!token) {
                logger.warn('No token to refresh');
                return false;
            }
            
            const response = await this.axiosInstance.post('/refresh', {}, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.data && response.data.access_token) {
                logger.log('Token refreshed successfully');
                localStorage.setItem('token', response.data.access_token);
                return true;
            } else {
                logger.warn('Token refresh response missing access_token');
                return false;
            }
        } catch (error) {
            logger.error('Error refreshing token:', error.message);
            if (error.response && error.response.status === 401) {
                logger.warn('Token refresh failed - clearing invalid token');
                localStorage.removeItem('token');
            }
            return false;
        }
    },

    // Logout user
    async logout() {
        try {
            logger.log('Logging out...');
            // Clear token from browser
            localStorage.removeItem('token');
            localStorage.removeItem('userRole');
            localStorage.removeItem('userName');
            localStorage.removeItem('userEmail');
            
            // Explicitly clear cache
            console.log('Clearing cached user data on logout');
            this._cachedUserData = null;
            
            // Call backend to invalidate token
            await this.axiosInstance.get('/logout');
            logger.log('Logout successful');
            
            return true;
        } catch (error) {
            logger.error('Error during logout:', error.message);
            // Force logout even if the API call fails
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            localStorage.removeItem('userRole');
            this._cachedUserData = null;
            window.location.href = '/';
            return false;
        }
    },

    // Set or update password
    async setPassword(password) {
        try {
            logger.log('Setting new password...');
            
            const response = await this.axiosInstance.post('/set-password', {
                password
            });
            
            logger.log('Password set successfully');
            return {
                success: true,
                message: 'Password updated successfully'
            };
        } catch (error) {
            logger.error('Error setting password:', error.message);
            if (error.response) {
                logger.error(`Status: ${error.response.status}, Data:`, error.response.data);
                return {
                    success: false,
                    message: error.response.data?.detail || 'Failed to set password',
                    status: error.response.status
                };
            }
            return { success: false, message: 'Network error while setting password' };
        }
    },

    // Debug token status - useful for troubleshooting
    debugTokenStatus() {
        const token = localStorage.getItem('token');
        logger.log('Token exists:', !!token);

        if (!token) {
            return false;
        }

        try {
            // Try to parse if it's stored as JSON
            let tokenValue = token;
            try {
                const parsedToken = JSON.parse(token);
                if (typeof parsedToken === 'string') {
                    tokenValue = parsedToken;
                    logger.debug('Token is stored as JSON string');
                } else {
                    logger.debug('Token is stored as JSON object');
                    return !!token;
                }
            } catch (e) {
                // Not JSON, just a string
                logger.debug('Token is stored as plain string');
            }

            // Show token details
            const tokenParts = tokenValue.split('.');
            if (tokenParts.length === 3) {
                try {
                    // Decode the payload (middle part)
                    const payloadBase64 = tokenParts[1].replace(/-/g, '+').replace(/_/g, '/');
                    const payloadJson = atob(payloadBase64);
                    const payload = JSON.parse(payloadJson);
                    
                    // Calculate expiration
                    if (payload.exp) {
                        const expMs = payload.exp * 1000; // Convert from seconds to milliseconds
                        const now = Date.now();
                        const expiresIn = expMs - now;
                        const expiresInMin = Math.floor(expiresIn / 60000);
                        
                        if (expiresIn <= 0) {
                            logger.warn('Token has expired!');
                        } else {
                            logger.log(`Token expires in: ${expiresInMin} minutes`);
                        }
                        
                        // Show expiration date in local time
                        const expirationDate = new Date(expMs);
                        logger.log('Token expires at:', expirationDate.toLocaleString());
                    } else {
                        logger.warn('Token has no expiration claim!');
                    }
                    
                    // Show subject and other common claims
                    if (payload.sub) {
                        logger.log('Token subject (user):', payload.sub);
                    }
                    
                    return true;
                } catch (e) {
                    logger.error('Error decoding token payload:', e);
                    return true; // We still have a token even if we can't decode it
                }
            } else {
                logger.warn('Token does not appear to be a valid JWT (not 3 parts)');
                return true; // We still have a token even if it's not a standard JWT
            }
        } catch (e) {
            logger.error('Error analyzing token:', e);
            return !!token; // Return whether we have a token
        }
    },

    // Clear all authentication data from local storage
    clearAuthData() {
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        localStorage.removeItem('user');
        this._cachedUserData = null;
    },

    // Check if user has required role
    hasRole(role) {
        try {
            // If we're checking for anonymous, always return true
            if (role === 'anonymous') {
                return true;
            }
            
            // Get user role from localStorage
            const userRole = localStorage.getItem('userRole');
            if (!userRole) {
                logger.debug('No user role found in localStorage');
                return false;
            }
            
            // Convert to lowercase for comparison
            const userRoleLower = userRole.toLowerCase();
            const requiredRoleLower = role.toLowerCase();
            
            // Direct match - return true
            if (userRoleLower === requiredRoleLower) {
                logger.debug(`Role check: direct match ${userRoleLower} === ${requiredRoleLower}`);
                return true;
            }
            
            // If user is admin or support, they have access to everything
            if (userRoleLower === 'admin' || userRoleLower === 'support') {
                logger.debug(`Role check: admin/support role has access to ${requiredRoleLower}`);
                return true;
            }
            
            // Role hierarchy for fallback
            const roleHierarchy = {
                admin: 5,
                support: 4,
                faculty: 3,
                teaching_assistant: 2,
                student: 1,
                anonymous: 0
            };
            
            // Convert role strings to numeric levels
            const userRoleLevel = roleHierarchy[userRoleLower] || 0;
            const requiredRoleLevel = roleHierarchy[requiredRoleLower] || 0;
            
            // Check if user's role level is sufficient
            const hasAccess = userRoleLevel >= requiredRoleLevel;
            logger.debug(`Role check: User role ${userRoleLower} (level ${userRoleLevel}) vs required ${requiredRoleLower} (level ${requiredRoleLevel}) = ${hasAccess}`);
            
            return hasAccess;
        } catch (error) {
            logger.error('Error checking role:', error);
            return false;
        }
    },

    // Check if user has a support role (admin or faculty)
    hasSupportRole() {
        try {
            const userRole = localStorage.getItem('userRole');
            if (!userRole) return false;
            
            const supportRoles = ['ADMIN', 'SUPPORT', 'FACULTY', 'TEACHING_ASSISTANT'];
            return supportRoles.includes(userRole.toUpperCase());
        } catch (error) {
            logger.error('Error checking support role:', error);
            return false;
        }
    }
};

export default authService;
