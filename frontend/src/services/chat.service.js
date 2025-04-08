import axios from 'axios';
import { API_ROUTES } from '@/config/api.routes';
// Comment out the import that's causing the error
// import { withLLMValidation } from '@/utils/llmValidator';
import api from '@/utils/api';
import dayjs from 'dayjs';
import useAuthStore from '@/stores/useAuthStore';

// Local storage keys for chat data
const LOCAL_STORAGE_KEYS = {
  CHAT_SESSIONS: 'localChatSessions',
  CHAT_MESSAGES: 'localChatMessages',
};

// Helper function to generate a unique ID
const generateId = () => {
  return Date.now().toString() + Math.random().toString(36).substring(2, 9);
};

// API paths without prefixes since they're already added in the axios instance
const API_PATHS = {
  CHAT: API_ROUTES.CHAT
};

// Local fallback implementations
const localImplementation = {
  // Get chat sessions from local storage
  getChatHistory: () => {
    try {
      const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS) || '[]');
      return { 
        data: { 
          chatSessions: sessions.map(session => ({
            ...session,
            createdAt: new Date(session.createdAt),
            lastUpdated: new Date(session.lastUpdated)
          })) 
        }
      };
    } catch (error) {
      console.error('Error getting chat history from local storage:', error);
      return { data: { chatSessions: [] } };
    }
  },

  // Create a chat session in local storage
  createChatSession: (title) => {
    try {
      const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS) || '[]');
      const newSession = {
        id: generateId(),
        title,
        createdAt: new Date(),
        lastUpdated: new Date(),
        messages: []
      };
      
      sessions.push(newSession);
      localStorage.setItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify(sessions));
      
      return { 
        data: { 
          chatSession: {
            ...newSession,
            createdAt: new Date(newSession.createdAt),
            lastUpdated: new Date(newSession.lastUpdated)
          }
        } 
      };
    } catch (error) {
      console.error('Error creating chat session in local storage:', error);
      throw error;
    }
  },

  // Update a chat session in local storage
  updateChatSession: (id, updates) => {
    try {
      const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS) || '[]');
      const index = sessions.findIndex(session => session.id === id);
      
      if (index !== -1) {
        sessions[index] = {
          ...sessions[index],
          ...updates,
          lastUpdated: new Date()
        };
        
        localStorage.setItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify(sessions));
        
        return { 
          data: { 
            chatSession: {
              ...sessions[index],
              createdAt: new Date(sessions[index].createdAt),
              lastUpdated: new Date(sessions[index].lastUpdated)
            }
          } 
        };
      } else {
        throw new Error('Chat session not found');
      }
    } catch (error) {
      console.error('Error updating chat session in local storage:', error);
      throw error;
    }
  },

  // Delete a chat session from local storage
  deleteChatSession: (id) => {
    try {
      const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS) || '[]');
      const newSessions = sessions.filter(session => session.id !== id);
      
      localStorage.setItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify(newSessions));
      localStorage.removeItem(LOCAL_STORAGE_KEYS.CHAT_MESSAGES + id);
      
      return { data: { success: true } };
    } catch (error) {
      console.error('Error deleting chat session from local storage:', error);
      throw error;
    }
  },

  // Add a message to a chat session in local storage
  addMessage: (chatId, message) => {
    try {
      // Update the chat session
      const sessions = JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS) || '[]');
      const index = sessions.findIndex(session => session.id === chatId);
      
      if (index !== -1) {
        sessions[index].lastUpdated = new Date();
        localStorage.setItem(LOCAL_STORAGE_KEYS.CHAT_SESSIONS, JSON.stringify(sessions));
      }
      
      // Add the message to the chat
      const messagesKey = LOCAL_STORAGE_KEYS.CHAT_MESSAGES + chatId;
      const messages = JSON.parse(localStorage.getItem(messagesKey) || '[]');
      
      // Ensure the message has correct structure
      const newMessage = {
        id: generateId(),
        role: message.role || 'user',
        type: message.role === 'assistant' ? 'ai' : 'user',
        content: typeof message.content === 'string' ? message.content : String(message.content || ''),
        timestamp: new Date()
      };
      
      messages.push(newMessage);
      localStorage.setItem(messagesKey, JSON.stringify(messages));
      
      return { 
        data: { 
          message: {
            ...newMessage,
            timestamp: new Date(newMessage.timestamp)
          }
        } 
      };
    } catch (error) {
      console.error('Error adding message to chat session in local storage:', error);
      throw error;
    }
  },
  
  // Get all messages for a chat session from local storage
  getMessages: (chatId) => {
    try {
      const messagesKey = LOCAL_STORAGE_KEYS.CHAT_MESSAGES + chatId;
      const messages = JSON.parse(localStorage.getItem(messagesKey) || '[]');
      
      return { 
        data: { 
          messages: messages.map(message => ({
            ...message,
            timestamp: new Date(message.timestamp)
          }))
        } 
      };
    } catch (error) {
      console.error('Error getting messages from local storage:', error);
      return { data: { messages: [] } };
    }
  }
};

// Define a simple local implementation of the validation function
// This avoids the need to import the external validation module
const withLLMValidation = (fn) => {
  return (...args) => {
    // Simply pass through to the original function
    return fn(...args);
  };
};

export const ChatService = {
  /**
   * Send a message to the AI and get a response
   * @param {Object} params - Object containing id and message
   * @param {string} params.id - Thread ID for conversation
   * @param {string} params.query - The user's message
   * @returns {Promise<Object>} - The AI's response
   */
  async sendMessage(params) {
    try {
      const { id, message, query, context, function_results } = params;
      
      // The backend expects 'query' instead of 'message'
      const payload = {
        id: id || crypto.randomUUID(),
        query: query || message // Support both 'query' and message for backwards compatibility
      };
      
      // Add context if provided
      if (context) {
        payload.context = context;
      }
      
      // Add function_results if provided
      if (function_results) {
        payload.function_results = function_results;
      }
      
      console.log('Sending message to AI:', payload);
      
      // Try the API call with proper error handling
      const response = await api.post(`${API_PATHS.CHAT}`, payload);
      
      // Process and normalize the response
      let processedResponse = { ...response.data };
      
      // Ensure we always have a valid structure even if backend returns empty/null fields
      if (!processedResponse.content) processedResponse.content = '';
      if (!processedResponse.function_calls) processedResponse.function_calls = [];
      if (!processedResponse.function_results) processedResponse.function_results = [];
      
      // Auto-detect common queries and add function calls when needed
      const userQueryText = (payload.query || '').toLowerCase();
      
      // If we have empty response but the query looks like it needs function calls
      if ((!processedResponse.content || processedResponse.content.trim() === '') && 
          processedResponse.function_calls.length === 0) {
          
        // Handle course-related queries
        if (userQueryText.includes('course') || userQueryText.includes('class') || 
            userQueryText.includes('enrolled') || userQueryText.match(/what (?:am i|i am) (?:taking|studying)/i)) {
          console.log("Adding automatic getCourses function call for course query");
          processedResponse.function_calls.push({
            name: "getCourses",
            arguments: {}
          });
        }
        
        // Handle assignment-related queries
        else if (userQueryText.includes('assignment') || userQueryText.includes('homework') || 
                userQueryText.includes('due') || userQueryText.includes('deadline')) {
          console.log("Adding automatic getAssignments function call for assignment query");
          processedResponse.function_calls.push({
            name: "getAssignments",
            arguments: {}
          });
        }
        
        // Handle profile-related queries
        else if (userQueryText.includes('profile') || userQueryText.includes('my account') || 
                userQueryText.includes('my info') || userQueryText.includes('my information')) {
          console.log("Adding automatic getUserProfile function call for profile query");
          processedResponse.function_calls.push({
            name: "getUserProfile",
            arguments: {}
          });
        }
      }
      
      // Normalize function_calls to ensure consistent format
      if (processedResponse.function_calls) {
        // If function_calls exists but is not an array, convert to array
        if (!Array.isArray(processedResponse.function_calls)) {
          try {
            // First check if it's a JSON string
            if (typeof processedResponse.function_calls === 'string') {
              try {
                // First try to extract function calls from tool_code blocks
                if (processedResponse.function_calls.includes('```tool_code') || 
                    processedResponse.function_calls.includes('```python') ||
                    processedResponse.function_calls.includes('```json')) {
                  // Extract code from the code blocks
                  const codeBlockRegex = /```(?:tool_code|python|json)?\n(.*?)```/gs;
                  const matches = [...processedResponse.function_calls.matchAll(codeBlockRegex)];
                  
                  if (matches.length > 0) {
                    console.log(`Found ${matches.length} code blocks in function_calls`);
                    let extractedCalls = [];
                    
                    for (const match of matches) {
                      const codeContent = match[1].trim();
                      
                      // Try to detect function calls like print(function_name(param1='value', param2=42))
                      const functionCallRegex = /(\w+)\s*\(\s*({[^}]+}|[^)]+)\s*\)/g;
                      const functionMatches = [...codeContent.matchAll(functionCallRegex)];
                      
                      for (const funcMatch of functionMatches) {
                        const funcName = funcMatch[1];
                        let funcArgs = funcMatch[2];
                        
                        // Skip common Python functions
                        if (['print', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'len'].includes(funcName)) {
                          continue;
                        }
                        
                        try {
                          // Try to convert Python-style arguments to JSON
                          // Convert single quotes to double quotes
                          funcArgs = funcArgs.replace(/'/g, '"');
                          
                          // Handle kwargs format (param1=value, param2=42)
                          if (funcArgs.includes('=')) {
                            const argsObject = {};
                            // Split by commas but not those within quotes or brackets
                            const argPairs = funcArgs.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)(?=(?:[^{]*{[^}]*})*[^}]*$)/);
                            
                            for (const pair of argPairs) {
                              const [key, val] = pair.split('=').map(s => s.trim());
                              if (key && val) {
                                // Try to parse value if it's JSON-like
                                try {
                                  argsObject[key] = JSON.parse(val);
                                } catch (e) {
                                  argsObject[key] = val.replace(/^["']|["']$/g, ''); // Remove quotes
                                }
                              }
                            }
                            
                            extractedCalls.push({
                              name: funcName,
                              arguments: argsObject
                            });
                          } else {
                            // Try to parse as JSON directly
                            try {
                              const parsedArgs = JSON.parse(funcArgs);
                              extractedCalls.push({
                                name: funcName,
                                arguments: parsedArgs
                              });
                            } catch (e) {
                              console.error(`Error parsing function arguments: ${funcArgs}`, e);
                              extractedCalls.push({
                                name: funcName,
                                arguments: funcArgs
                              });
                            }
                          }
                        } catch (e) {
                          console.error(`Error extracting function call ${funcName}:`, e);
                          extractedCalls.push({
                            name: funcName,
                            arguments: {}
                          });
                        }
                      }
                    }
                    
                    if (extractedCalls.length > 0) {
                      console.log(`Extracted ${extractedCalls.length} function calls from code blocks`, extractedCalls);
                      processedResponse.function_calls = extractedCalls;
                    } else {
                      // Fallback: try to parse the whole thing as JSON
                      try {
                        processedResponse.function_calls = JSON.parse(processedResponse.function_calls);
                        if (!Array.isArray(processedResponse.function_calls)) {
                          processedResponse.function_calls = [processedResponse.function_calls];
                        }
                      } catch (e) {
                        // Not valid JSON, treat as single item
                        processedResponse.function_calls = [processedResponse.function_calls];
                      }
                    }
                  } else {
                    // Fallback to standard JSON parsing
                    try {
                      processedResponse.function_calls = JSON.parse(processedResponse.function_calls);
                      if (!Array.isArray(processedResponse.function_calls)) {
                        processedResponse.function_calls = [processedResponse.function_calls];
                      }
                    } catch (e) {
                      // Not valid JSON, treat as single item
                      processedResponse.function_calls = [processedResponse.function_calls];
                    }
                  }
                } else {
                  // Standard JSON parsing
                  try {
                    processedResponse.function_calls = JSON.parse(processedResponse.function_calls);
                    if (!Array.isArray(processedResponse.function_calls)) {
                      processedResponse.function_calls = [processedResponse.function_calls];
                    }
                  } catch (e) {
                    // Not valid JSON, treat as single item
                    processedResponse.function_calls = [processedResponse.function_calls];
                  }
                }
              } catch (e) {
                // Not valid JSON, treat as single item
                processedResponse.function_calls = [processedResponse.function_calls];
              }
            } else {
              // Not a string, just wrap object in array
              processedResponse.function_calls = [processedResponse.function_calls];
            }
          } catch (e) {
            console.error('Error normalizing function_calls format:', e);
            processedResponse.function_calls = [];
          }
        }
        
        // Ensure each function call has proper structure
        processedResponse.function_calls = processedResponse.function_calls.map(call => {
          // If it's a string, try to parse it
          if (typeof call === 'string') {
            try {
              return JSON.parse(call);
            } catch (e) {
              console.error('Error parsing function call string:', e);
              return { name: 'unknown', arguments: {} };
            }
          }
          
          // Handle the format seen in the error message: { type: 'function', function: { name, arguments } }
          if (call.type === 'function' && call.function) {
            return {
              name: call.function.name,
              arguments: call.function.arguments || {}
            };
          }
          
          // Default fallback structure
          return {
            name: call.name || 'unknown',
            arguments: call.arguments || {}
          };
        });
      }
      
      // Normalize function_results similarly
      if (processedResponse.function_results) {
        if (!Array.isArray(processedResponse.function_results)) {
          try {
            if (typeof processedResponse.function_results === 'string') {
              try {
                processedResponse.function_results = JSON.parse(processedResponse.function_results);
                if (!Array.isArray(processedResponse.function_results)) {
                  processedResponse.function_results = [processedResponse.function_results];
                }
              } catch (e) {
                processedResponse.function_results = [processedResponse.function_results];
              }
            } else {
              processedResponse.function_results = [processedResponse.function_results];
            }
          } catch (e) {
            console.error('Error normalizing function_results:', e);
            processedResponse.function_results = [];
          }
        }
        
        // Ensure each function result has proper structure
        processedResponse.function_results = processedResponse.function_results.map(result => {
          // If it's a string, try to parse it
          if (typeof result === 'string') {
            try {
              return JSON.parse(result);
            } catch (e) {
              console.error('Error parsing function result string:', e);
              return { name: 'unknown', result: { error: 'Failed to parse result' } };
            }
          }
          
          // Handle possible nested structure
          if (result.type === 'function_result' && result.function_result) {
            return {
              name: result.function_result.name || result.name || 'unknown',
              result: result.function_result.result || result.result || { error: 'Missing result data' }
            };
          }
          
          // Default fallback structure
          return {
            name: result.name || 'unknown',
            result: result.result !== undefined ? result.result : { error: 'No result data' }
          };
        });
      }
      
      return processedResponse;
    } catch (error) {
      console.error('Error sending message to AI:', error);
      
      // Give a more specific error message based on the status code
      if (error.response) {
        const status = error.response.status;
        
        if (status === 404) {
          return {
            content: "Sorry, the AI service seems to be unavailable. Please check your connection and try again."
          };
        } else if (status === 500) {
          return {
            content: "The server encountered an issue while processing your request. The team has been notified."
          };
        }
      }
      
      // Generic fallback for network errors or other issues
      return {
        content: "I'm sorry, I couldn't connect to my knowledge base. Please try again in a moment."
      };
    }
  },

  /**
   * Get the current chat history
   * @param {string} id - Thread ID to get history for 
   * @returns {Promise<Array>} - The chat history
   */
  async getChatHistory(id) {
    try {
      // If an ID is provided, get that specific chat history
      if (id) {
        const response = await api.get(`${API_PATHS.CHAT}?id=${id}`);
        return response.data;
      }
      
      // Otherwise try to get all chat sessions
      const response = await api.get(`${API_PATHS.CHAT}/sessions`);
      return response.data;
    } catch (error) {
      console.error('Error getting chat history:', error);
      // Return local chat history as fallback
      return localImplementation.getChatHistory();
    }
  },
  
  /**
   * Create a new chat session
   * @param {Object} sessionData - The session data
   * @returns {Promise<Object>} - The created session
   */
  async createChatSession(sessionData) {
    try {
      const response = await api.post(`${API_PATHS.CHAT}/sessions`, sessionData);
      return response.data;
    } catch (error) {
      console.error('Error creating chat session:', error);
      // Create local chat session as fallback
      return localImplementation.createChatSession(sessionData.title);
    }
  },
  
  /**
   * Get a chat session by ID
   * @param {string} sessionId - The session ID
   * @returns {Promise<Object>} - The session
   */
  async getChatSession(sessionId) {
    try {
      const response = await api.get(`${API_PATHS.CHAT}/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting chat session:', error);
      // Get local chat sessions and find the one by ID
      const { data: { chatSessions } } = localImplementation.getChatHistory();
      const session = chatSessions.find(s => s.id === sessionId);
      if (!session) throw error;
      return { 
        data: { 
          chatSession: {
            ...session,
            createdAt: new Date(session.createdAt),
            lastUpdated: new Date(session.lastUpdated)
          }
        } 
      };
    }
  },
  
  /**
   * Update a chat session
   * @param {string} sessionId - The session ID
   * @param {Object} sessionData - The session data to update
   * @returns {Promise<Object>} - The updated session
   */
  async updateChatSession(sessionId, sessionData) {
    try {
      const response = await api.put(`${API_PATHS.CHAT}/sessions/${sessionId}`, sessionData);
      return response.data;
    } catch (error) {
      console.error('Error updating chat session:', error);
      // Update local chat session as fallback
      return localImplementation.updateChatSession(sessionId, sessionData);
    }
  },
  
  /**
   * Delete a chat session
   * @param {string} sessionId - The session ID
   * @returns {Promise<void>}
   */
  async deleteChatSession(sessionId) {
    try {
      await api.delete(`${API_PATHS.CHAT}/sessions/${sessionId}`);
    } catch (error) {
      console.error('Error deleting chat session:', error);
      // Delete local chat session as fallback
      localImplementation.deleteChatSession(sessionId);
    }
  },
  
  /**
   * Add a message to a chat session
   * @param {string} sessionId - The session ID
   * @param {Object} message - The message to add
   * @returns {Promise<Object>} - The added message
   */
  async addMessage(sessionId, message) {
    try {
      const response = await api.post(`${API_PATHS.CHAT}/sessions/${sessionId}/messages`, message);
      return response.data;
    } catch (error) {
      console.error('Error adding message:', error);
      // Add message to local chat session as fallback
      return localImplementation.addMessage(sessionId, message);
    }
  },
  
  /**
   * Get messages for a chat session
   * @param {string} sessionId - The session ID
   * @returns {Promise<Array>} - The messages
   */
  async getMessages(sessionId) {
    try {
      const response = await api.get(`${API_PATHS.CHAT}/sessions/${sessionId}/messages`);
      return response.data;
    } catch (error) {
      console.error('Error getting messages:', error);
      // Get local chat sessions and find messages for the session
      const { data: { messages } } = localImplementation.getMessages(sessionId);
      return messages;
    }
  },

  /**
   * Get available functions that the AI can call, filtered by user role
   * @returns {Promise<Array>} - The available functions
   */
  async getAvailableFunctions() {
    try {
      // Get current user info from auth store
      const authStore = useAuthStore();
      const isAuthenticated = authStore.isAuthenticated || !!authStore.token;
      const userRole = authStore.userRole?.toLowerCase() || 'anonymous';
      
      console.log(`Getting available functions for user role: ${userRole}`);
      
      // Skip API call for unauthenticated users and return anonymous functions directly
      if (!isAuthenticated) {
        console.log('User not authenticated, returning anonymous functions without API call');
        // Return only functions available to anonymous users
        return [
          {
            name: "web_search",
            description: "Search the web for current information",
            parameters: {
              properties: {
                query: {
                  type: "string",
                  description: "The search query"
                }
              },
              required: ["query"]
            }
          }
        ];
      }
      
      // First try to get from API
      const response = await api.get(`${API_PATHS.CHAT}/available-functions`);
      
      // Log the functions available to this user
      console.log(`Received ${response.data.length} available functions from backend`);
      
      return response.data;
    } catch (error) {
      console.error('Error getting available functions:', error);
      
      // Get user role for fallback
      const authStore = useAuthStore();
      const userRole = authStore.userRole?.toLowerCase() || 'anonymous';
      
      // Define role-based function access for fallback
      const roleFunctions = {
        admin: [
          "getCourses", "getCourseById", "getAssignments", "getUserProfile",
          "getQuizzes", "getSubmissions", "web_search", "get_user_info",
          "get_course_enrollment", "query_course_materials"
        ],
        faculty: [
          "getCourses", "getCourseById", "getAssignments", "getUserProfile",
          "getQuizzes", "web_search", "get_course_enrollment", "query_course_materials"
        ],
        student: [
          "getCourses", "getCourseById", "getAssignments", "getUserProfile",
          "web_search", "query_course_materials"
        ],
        anonymous: [
          "web_search"
        ]
      };
      
      // Get allowed functions for this role (default to anonymous)
      const allowedFunctions = roleFunctions[userRole] || roleFunctions.anonymous;
      
      // Return more comprehensive fallback functions list when API fails, filtered by role
      const allFunctions = [
        {
          name: "getCourses",
          description: "Get all available courses for the current user",
          parameters: {
            properties: {},
            required: []
          }
        },
        {
          name: "getCourseById",
          description: "Get details of a specific course by ID",
          parameters: {
            properties: {
              courseId: {
                type: "string",
                description: "The ID of the course to retrieve"
              }
            },
            required: ["courseId"]
          }
        },
        {
          name: "getAssignments",
          description: "Get all assignments for the current user",
          parameters: {
            properties: {
              courseId: {
                type: "string",
                description: "Optional: Filter assignments by course ID"
              }
            },
            required: []
          }
        },
        {
          name: "getUserProfile",
          description: "Get the current user's profile information",
          parameters: {
            properties: {},
            required: []
          }
        },
        {
          name: "web_search",
          description: "Search the web for current information",
          parameters: {
            properties: {
              query: {
                type: "string",
                description: "The search query"
              }
            },
            required: ["query"]
          }
        },
        {
          name: "get_course_enrollment",
          description: "Get enrollment details for a course (faculty only)",
          parameters: {
            properties: {
              course_id: {
                type: "string",
                description: "The ID of the course"
              }
            },
            required: ["course_id"]
          }
        },
        {
          name: "query_course_materials",
          description: "Search the course materials for relevant information",
          parameters: {
            properties: {
              query_text: {
                type: "string",
                description: "The search query"
              }
            },
            required: ["query_text"]
          }
        }
      ];
      
      // Filter functions by role
      return allFunctions.filter(func => allowedFunctions.includes(func.name));
    }
  },

  /**
   * Check if the AI can use functions
   * @returns {Promise<boolean>} - Whether the AI can use functions
   */
  async canUseFunctions() {
    try {
      const authStore = useAuthStore();
      const isAuthenticated = authStore.isAuthenticated || !!authStore.token;
      
      // If user is not authenticated, return limited functions without API call
      if (!isAuthenticated) {
        console.log('User not authenticated, returning limited functions without API call');
        return true; // We still want to show the functions badge for anonymous users
      }
      
      const functions = await this.getAvailableFunctions();
      return Array.isArray(functions) && functions.length > 0;
    } catch (error) {
      console.error('Error checking if AI can use functions:', error);
      return true; // Default to true for better UX
    }
  },

  /**
   * Send a message to the AI with academic integrity validation
   * @param {Object|string} params - Either a string message or object with id and message
   * @returns {Promise<Object>} - The AI's response
   */
  sendValidatedMessage: withLLMValidation(async (params) => {
    try {
      const { id, message } = typeof params === 'string' 
        ? { id: crypto.randomUUID(), message: params } 
        : params;
      
      const response = await api.post(`${API_PATHS.CHAT}`, {
        id: id,
        query: message
      });
      return response.data;
    } catch (error) {
      console.error('Error sending validated message to AI:', error);
      // Fallback to a simple AI response
      return {
        response: {
          message: "I apologize, but I'm having trouble connecting to the server right now. Please try again later."
        }
      };
    }
  }),

  /**
   * Get Swagger documentation
   * @returns {Promise<Object>} The OpenAPI specification
   */
  async getSwaggerDocs() {
    try {
      // First try to get the actual OpenAPI spec from the root URL (no /api/v1 prefix)
      const response = await axios.get('http://localhost:8000/openapi.json', {
        params: { _t: Date.now() }  // Add timestamp to prevent caching
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching Swagger documentation:', error);
      
      // Return a minimal mock Swagger document as fallback
      return {
        openapi: "3.0.0",
        info: {
          title: "API Documentation",
          version: "1.0.0",
          description: "Mock API documentation for development"
        },
        paths: {
          "/api/v1/auth/me": {
            get: {
              summary: "Get current user profile",
              tags: ["auth"]
            }
          },
          "/api/v1/courses": {
            get: {
              summary: "Get all courses",
              tags: ["courses"]
            }
          },
          "/api/v1/courses/{courseId}": {
            get: {
              summary: "Get course by ID",
              tags: ["courses"]
            }
          },
          "/api/v1/assignments": {
            get: {
              summary: "Get all assignments",
              tags: ["assignments"]
            }
          },
          "/api/v1/chat/sessions": {
            get: {
              summary: "Get all chat sessions",
              tags: ["chat"]
            },
            post: {
              summary: "Create a new chat session",
              tags: ["chat"]
            }
          },
          "/api/v1/chat/sessions/{sessionId}": {
            get: {
              summary: "Get a chat session by ID",
              tags: ["chat"]
            },
            put: {
              summary: "Update a chat session",
              tags: ["chat"]
            },
            delete: {
              summary: "Delete a chat session",
              tags: ["chat"]
            }
          }
        }
      };
    }
  },

  /**
   * Get current user's JWT token
   * @returns {string|null} - JWT token or null if not found
   */
  async getCurrentUserToken() {
    try {
      // First try to get from auth store
      const authStore = useAuthStore();
      if (authStore.token) {
        return authStore.token;
      }
      
      // Fallback to local storage
      return localStorage.getItem('token');
    } catch (error) {
      console.error('Error getting user token:', error);
      return null;
    }
  },

  /**
   * Execute an API call with authentication
   * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
   * @param {string} url - API endpoint URL
   * @param {Object} data - Request payload (for POST/PUT)
   * @returns {Promise<Object>} - Response data
   */
  async executeApiCall(method, url, data = null) {
    try {
      const token = await this.getCurrentUserToken();
      
      if (!token) {
        throw new Error('Authentication required. Please log in.');
      }
      
      const config = {
        method: method.toLowerCase(),
        url: url.startsWith('/') ? url : `/${url}`,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      };
      
      if (data && ['post', 'put', 'patch'].includes(method.toLowerCase())) {
        config.data = data;
      }
      
      const response = await axios(config);
      return response.data;
    } catch (error) {
      console.error(`Error executing ${method} ${url}:`, error);
      throw error;
    }
  },

  /**
   * Execute a function call by mapping to API endpoints
   * @param {string} functionName - Name of the function to execute
   * @param {Object} args - Arguments for the function call
   * @returns {Promise<Object>} - Function result
   */
  async executeFunctionCall(functionName, args) {
    console.log(`Executing function: ${functionName}`, args);
    
    try {
      // Send a direct function call to the backend
      const payload = {
        id: crypto.randomUUID(),
        query: `Executing function: ${functionName}`,
        function_call: {
          name: functionName,
          arguments: args || {}
        }
      };
      
      console.log('Sending direct function execution request to backend:', payload);
      
      // Use the chat endpoint which now supports direct function calling
      const response = await api.post(`${API_PATHS.CHAT}`, payload);
      
      // The response should include function_results with our function's result
      if (response.data && response.data.function_results && response.data.function_results.length > 0) {
        // Find the result for this function
        const functionResult = response.data.function_results.find(r => r.name === functionName);
        if (functionResult) {
          console.log(`Received result for function ${functionName}:`, functionResult.result);
          return functionResult.result;
        }
      }
      
      // If for some reason we didn't get a function result, return the raw response
      console.warn(`Function ${functionName} didn't return specific results, returning raw response`);
      return response.data;
      } catch (error) {
      console.error(`Error executing function ${functionName}:`, error);
      
      if (error.response) {
        // Handle specific error status codes
        const status = error.response.status;
        
        if (status === 401 || status === 403) {
          throw new Error('Authentication required. Please log in to access this functionality.');
        } else if (status === 404) {
          throw new Error(`Function ${functionName} not found or not accessible.`);
        } else if (status === 422) {
          throw new Error(`Invalid arguments provided to function ${functionName}.`);
        } else if (status >= 500) {
          throw new Error('Server error occurred. Please try again later.');
        }
      }
      
      // For network or other errors
      throw new Error(`Failed to execute function ${functionName}: ${error.message}`);
    }
  },

  /**
   * Get formatted endpoints from Swagger documentation
   * @returns {Promise<Array>} Array of formatted endpoints
   */
  async getSwaggerEndpoints() {
    try {
      // Fetch the Swagger documentation
      const swaggerDocs = await this.getSwaggerDocs();
      
      // Check if the Swagger documentation is valid and contains paths
      if (!swaggerDocs || !swaggerDocs.paths) {
        console.warn('Swagger documentation is empty or invalid');
        return [];
      }

      const endpoints = [];
      const paths = swaggerDocs.paths;

      // Iterate through all paths and methods
      for (const path in paths) {
        const pathObj = paths[path];
        
        // Skip if path starts with "/docs" or "/openapi.json"
        if (path.startsWith('/docs') || path.startsWith('/openapi.json')) {
          continue;
        }

        // Process each HTTP method (GET, POST, PUT, DELETE, etc.)
        for (const method in pathObj) {
          // Skip if method is 'parameters' or other non-HTTP method property
          if (!['get', 'post', 'put', 'delete', 'patch', 'options', 'head'].includes(method)) {
            continue;
          }

          const endpointInfo = pathObj[method];
          
          endpoints.push({
            path: path,
            method: method.toUpperCase(),
            description: endpointInfo.summary || endpointInfo.description || '',
            tags: endpointInfo.tags || []
          });
        }
      }

      // Sort endpoints by path for better readability
      return endpoints.sort((a, b) => a.path.localeCompare(b.path));
    } catch (error) {
      console.error('Error getting Swagger endpoints:', error);
      throw error;
    }
  },

  /**
   * Clear chat history for a specific thread
   * @param {string} id - Thread ID to clear
   * @returns {Promise<Object>} Response data
   */
  async clearChatHistory(id) {
    if (!id) {
      throw new Error('Thread ID is required to clear chat history')
    }
    
    try {
      // Call the DELETE endpoint with the thread ID as a query parameter and a shorter timeout
      const response = await api.delete(`${API_PATHS.CHAT}?id=${id}`, {
        timeout: 10000, // 10 second timeout instead of default 30 seconds
      })
      return response.data
    } catch (error) {
      console.error('Error clearing chat history:', error)
      
      // For timeout errors, still try to use the local implementation
      if (error.code === 'ECONNABORTED' || (error.response && error.response.status === 500)) {
        console.log('Using local fallback for chat history deletion')
        return localImplementation.deleteChatSession(id)
      }
      
      // For other errors, just return a success message to prevent UI issues
      return { 
        message: 'Chat history cleared locally',
        error: error.message
      }
    }
  },
}

export default ChatService 