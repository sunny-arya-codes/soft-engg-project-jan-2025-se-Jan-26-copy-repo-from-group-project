import { defineStore } from 'pinia';
import { ref, onMounted, watch } from 'vue';
import FetchFunction from '../utils/FetchFunction';
import router from '../router/index';
import { User } from '@/models/User';
import { APP_BASE_URL, ROLE } from '@/AppConstants/globalConstants';
import rolePaths from '@/AppConstants/rolePaths';
import { authService } from '@/api/authService';

// For development only - remove in production
const DEV_MODE = import.meta.env.VITE_NODE_ENV === 'development';

export default defineStore('auth', () => {
    // Parse token from localStorage, handling both string and JSON string formats
    const storedToken = localStorage.getItem('token');
    let parsedToken = null;

    try {
        // First check if it begins with quotes (JSON string)
        if (storedToken && (storedToken.startsWith('"') && storedToken.endsWith('"'))) {
            // It's stored as a JSON string - parse and clean it
            parsedToken = JSON.parse(storedToken);
            // Fix the token in localStorage
            localStorage.setItem('token', parsedToken);
            console.warn('Fixed token format in localStorage (removed JSON quotes)');
        } else {
            // Use as is - plain string token
            parsedToken = storedToken;
        }
    } catch (e) {
        // If not valid JSON or any error, use as is
        console.warn('Error parsing token, using as-is:', e.message);
        parsedToken = storedToken;
    }

    const token = ref(parsedToken);
    const returnUrl = ref(null);
    const user = ref(new User(null, "", "", ""));
    const userRole = ref(localStorage.getItem('userRole') || ROLE.STUDENT);
    const isAdmin = ref(false);
    const isDevelopment = ref(DEV_MODE);
    const hasPassword = ref(false);
    const isInitialized = ref(false);

    // Initialize auth state when store is created
    async function initialize() {
        console.log("Initializing auth store");
        
        if (isInitialized.value) {
            console.log("Auth store already initialized");
            return;
        }
        
        // Check if we have a token
        if (!token.value) {
            console.log("No token found, skipping initialization");
            isInitialized.value = true;
            return;
        }
        
        try {
            // Get user data
            const userData = await authService.getCurrentUser();
            if (userData) {
                setUser(userData);
                console.log(`Auth store initialized for user: ${userData.email}, role: ${userData.role}`);
            } else {
                console.warn("Failed to get user data during initialization");
                // Keep the token in case it's valid but the API call failed
            }
        } catch (error) {
            console.error("Error initializing auth store:", error);
            // Clear auth data on critical errors
            if (error.response && error.response.status === 401) {
                logout();
            }
        } finally {
            isInitialized.value = true;
        }
    }

    // Development only - helper to switch roles
    function switchRole(role) {
        if (!isDevelopment.value) return;
        if (Object.values(ROLE).includes(role)) {
            setUserRole(role);
            // Don't redirect, let the router handle navigation
        }
    }

    async function login(email, pswd) {
        if (isDevelopment.value) {
            // For development, just set a dummy token as plain string
            const dummyToken = "dummy-token";
            token.value = dummyToken;
            localStorage.setItem('token', dummyToken); // Store as plain string
            
            console.log('Development mode: Using dummy token');
            
            // Navigate based on current role
            navigateToRoleDashboard();
            return;
        }
        
        try {
            // Use the authService directly instead of FetchFunction
            const response = await authService.loginWithEmail(email, pswd);
            
            if (response && response.success) {
                // Get clean token
                const accessToken = response.access_token;
                
                // Store as plain string, not JSON
                token.value = accessToken;
                localStorage.setItem('token', accessToken);
                
                console.log('Login successful, token stored in state and localStorage');
                
                // Set user role if available
                if (response.user && response.user.role) {
                    console.log(`AUTH STORE: Setting role from login response user object: "${response.user.role}"`);
                    console.log(`AUTH STORE: Current roles - FACULTY="${ROLE.FACULTY}", SUPPORT="${ROLE.SUPPORT}", STUDENT="${ROLE.STUDENT}"`);
                    setUserRole(response.user.role);
                    console.log(`AUTH STORE: Role after setting: "${userRole.value}"`);
                } else {
                    console.warn('AUTH STORE: No role found in login response user object');
                }
                
                // Navigate to appropriate dashboard
                navigateToRoleDashboard();
            } else {
                throw new Error(response?.message || 'Login failed');
            }
        } catch (error) {
            console.error("Login error:", error);
            throw error; // Re-throw to let the component handle it
        }
    }

    // Helper method to navigate based on role
    function navigateToRoleDashboard() {
        // Debug log to see the actual role value
        console.log("Navigating with role:", userRole.value);
        
        switch (userRole.value) {
            case ROLE.STUDENT:  // "STUDENT"
                console.log("Redirecting to student dashboard");
                router.push(rolePaths.STUDENT.dashboard);
                break;
            case ROLE.FACULTY:  // "FACULTY"
                console.log("Redirecting to faculty dashboard");
                router.push(rolePaths.FACULTY.dashboard);
                break;
            case ROLE.SUPPORT:  // "SUPPORT"
                console.log("Redirecting to support dashboard");
                router.push(rolePaths.SUPPORT.dashboard);
                break;
            default:
                console.warn(`Unknown role: ${userRole.value}, defaulting to student dashboard`);
                router.push(rolePaths.STUDENT.dashboard);
        }
    }

    function logout() {
        // Reset user to a new User instance instead of null
        user.value = new User(null, "", "", "");
        token.value = null;
        userRole.value = ROLE.STUDENT;
        hasPassword.value = false;
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        router.push('/login');
    }

    function setUser(userData) {
        console.log('useAuthStore: Setting user with data:', userData);
        
        // Check if user.value is null, and reinitialize if needed
        if (!user.value) {
            console.warn('user.value is null, reinitializing with new User object');
            user.value = new User(null, "", "", "");
        }
        
        // Now we can safely set properties
        user.value.id = userData.id;
        user.value.name = userData.name;
        user.value.email = userData.email;
        
        // Store the role directly from userData
        if (userData.role) {
            // Log the role before setting it
            console.log(`useAuthStore: Setting user.value.role from ${user.value.role} to ${userData.role}`);
            user.value.role = userData.role;
        }
        
        hasPassword.value = userData.has_password || false;
        
        // Use the separate method to set userRole (which handles normalization)
        if (userData.role) {
            setUserRole(userData.role);
        } else {
            console.warn('useAuthStore: userData does not contain role');
        }
    }

    function setUserRole(role) {
        if (role && typeof role === 'string') {
            // Normalize role to uppercase
            const normalizedRole = role.toUpperCase();
            
            // Log original and normalized role for debugging
            console.log(`Setting user role - Original: "${role}", Normalized: "${normalizedRole}"`);
            console.log(`ROLE constants: STUDENT="${ROLE.STUDENT}", FACULTY="${ROLE.FACULTY}", SUPPORT="${ROLE.SUPPORT}"`);
            
            // Validate against known roles
            if (Object.values(ROLE).includes(normalizedRole)) {
                userRole.value = normalizedRole;
                localStorage.setItem('userRole', normalizedRole);
                console.log(`User role set to: "${normalizedRole}"`);
            } else {
                // Try a case-insensitive match as fallback
                const matchingRole = Object.values(ROLE).find(r => 
                    r.toLowerCase() === role.toLowerCase());
                
                if (matchingRole) {
                    console.log(`Found matching role "${matchingRole}" through case-insensitive match`);
                    userRole.value = matchingRole;
                    localStorage.setItem('userRole', matchingRole);
                } else {
                    console.warn(`Invalid role: "${role}", defaulting to STUDENT`);
                    userRole.value = ROLE.STUDENT;
                    localStorage.setItem('userRole', ROLE.STUDENT);
                }
            }
        } else {
            console.warn(`Invalid role value: ${role}, defaulting to STUDENT`);
            userRole.value = ROLE.STUDENT;
            localStorage.setItem('userRole', ROLE.STUDENT);
        }
    }

    function clearUser() {
        user.value = new User(null, "", "", "");
        userRole.value = ROLE.STUDENT;
        hasPassword.value = false;
        localStorage.removeItem('userRole');
    }

    // Check if the current user needs to set a password
    async function checkPasswordStatus() {
        try {
            const userData = await authService.getCurrentUser();
            if (userData) {
                hasPassword.value = userData.has_password || false;
                return hasPassword.value;
            }
            return false;
        } catch (error) {
            console.error('Error checking password status:', error);
            return false;
        }
    }

    // Set password for the current user
    async function setPassword(password) {
        try {
            const result = await authService.setPassword(password);
            if (result.success) {
                hasPassword.value = true;
            }
            return result;
        } catch (error) {
            console.error('Error setting password:', error);
            return { success: false, message: 'Failed to set password' };
        }
    }

    // Initialize the store on creation
    // Note: This is called when the store is first accessed
    setTimeout(initialize, 0);

    return {
        token,
        returnUrl,
        user,
        userRole,
        isAdmin,
        isDevelopment,
        hasPassword,
        isInitialized,
        initialize,
        switchRole,
        login,
        logout,
        setUser,
        setUserRole,
        clearUser,
        navigateToRoleDashboard,
        checkPasswordStatus,
        setPassword
    };
});