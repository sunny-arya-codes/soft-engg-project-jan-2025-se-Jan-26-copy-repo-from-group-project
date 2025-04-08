<template>
  <div class="chat-container">
    <!-- Messages Area -->
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="currentMessages.length === 0" class="empty-state">
        <span class="empty-state-icon material-icons text-4xl mb-2">chat</span>
        <p class="empty-state-title">Hello, how can I help you today?</p>
        <p class="empty-state-text">Ask me any question about your courses, assignments, or academic materials.</p>
      </div>
      
      <div v-for="(message, index) in currentMessages" 
           :key="index"
           class="message"
           :class="{'user': message.type === 'user', 'ai': message.type === 'ai'}"
      >
        <!-- Message Content -->
        <div class="message-content" :class="{'user': message.type === 'user', 'ai': message.type === 'ai'}">
          <div class="prose prose-sm" v-html="formatMessage(message.content)"></div>
          <div v-if="message.type === 'ai'" class="message-actions">
            <button class="message-action-btn hover:text-gray-700" @click="copyToClipboard(message.content)">
              <span class="material-icons text-sm">content_copy</span>
            </button>
            <button class="message-action-btn hover:text-gray-700" @click="thumbsUp(index)">
              <span class="material-icons text-sm">thumb_up</span>
            </button>
            <button class="message-action-btn hover:text-gray-700" @click="thumbsDown(index)">
              <span class="material-icons text-sm">thumb_down</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Typing Indicator -->
      <div v-if="isTyping" class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
      
      <!-- Function Calling Indicator -->
      <div v-if="isFunctionCalling" class="function-calling-indicator">
        <div class="function-icon">
          <span class="material-icons">functions</span>
        </div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="function-text">Executing functions</div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="chat-input-container">
      <div class="swagger-tools">
        <button class="swagger-button" @click="toggleSwaggerInfo">
          <span class="material-icons">api</span>
          API Docs
        </button>
        
        <button v-if="currentMessages.length > 0" class="swagger-button clear-button" @click="clearChat">
          <span class="material-icons">delete</span>
          Clear Chat
        </button>
      </div>
      
      <form @submit.prevent="sendMessage" class="chat-input-wrapper">
        <textarea
          v-model="newMessage"
          rows="1"
          placeholder="Type your message..."
          class="chat-input"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown="handleKeyDown"
          ref="messageInput"
        ></textarea>
        <button
          type="submit"
          class="send-button"
          :disabled="!newMessage.trim() || isTyping || isFunctionCalling"
        >
          <span class="material-icons">send</span>
        </button>
      </form>
      
      <!-- Swagger Modal -->
      <Transition name="fade">
        <div v-if="showSwaggerInfo" class="swagger-modal" @click.self="showSwaggerInfo = false">
          <div class="swagger-modal-content">
            <div class="swagger-modal-header">
              <h3>Available API Endpoints</h3>
              <button @click="showSwaggerInfo = false" class="modal-close-button">
                <span class="material-icons">close</span>
              </button>
            </div>
            
            <div class="swagger-endpoints">
              <div v-if="loadingSwagger" class="swagger-loading">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
              </div>
              
              <div v-else-if="swaggerError" class="swagger-error">
                <span class="material-icons">error</span>
                <p>{{ swaggerError }}</p>
              </div>
              
              <template v-else>
                <p class="swagger-help-text">
                  These endpoints are available to the AI assistant. You can ask it to retrieve or manipulate data through these APIs.
                </p>
                
                <ul v-if="swaggerEndpoints.length > 0" class="swagger-endpoint-list">
                  <li v-for="(endpoint, index) in swaggerEndpoints" :key="index" class="swagger-endpoint-item">
                    <div :class="['method', endpoint.method.toLowerCase()]">{{ endpoint.method }}</div>
                    <div class="path">{{ endpoint.path }}</div>
                    <div class="description">{{ endpoint.description || 'No description available' }}</div>
                  </li>
                </ul>
                
                <div v-else class="swagger-empty">
                  <span class="material-icons">info</span>
                  <p>No API endpoints found</p>
                </div>
              </template>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ChatService } from '@/services/chat.service'
import ApiExecutorService from '@/services/api-executor.service'
import { useChatStore } from '@/stores/useChatStore'
import { computed, ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'ChatBotBox',
  props: {
    chatId: {
      type: String,
      default: null
    },
    context: {
      type: Object,
      default: null
    }
  },
  emits: ['clear-context', 'update:title'],
  setup(props, { emit }) {
    const route = useRoute()
    const chatStore = useChatStore()
    const newMessage = ref('')
    const isTyping = ref(false)
    const isFunctionCalling = ref(false)
    const messagesContainer = ref(null)
    const messageInput = ref(null)
    const swaggerEndpoints = ref([])
    const showSwaggerInfo = ref(false)
    const loadingSwagger = ref(false)
    const swaggerError = ref(null)
    
    // Get the current chat's messages from the chat store
    const currentMessages = computed(() => {
      const chatId = props.chatId
      if (!chatId) return []
      
      const chat = chatStore.chatHistory.find(chat => chat.id === chatId)
      return chat ? chat.messages : []
    })
    
    // Get or generate a thread ID for this chat
    const threadId = computed(() => {
      const chat = chatStore.chatHistory.find(chat => chat.id === props.chatId)
      return chat?.threadId || crypto.randomUUID()
    })
    
    // Watch for changes in chatId and scroll to bottom
    watch(() => props.chatId, () => {
      scrollToBottom()
    })
    
    onMounted(() => {
      scrollToBottom()
    })
    
    // Scroll to the bottom of the chat
    const scrollToBottom = () => {
      setTimeout(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      }, 100)
    }
    
    // Format message content with markdown - with type checking
    const formatMessage = (content) => {
      try {
        // Ensure content is a string
        if (typeof content !== 'string') {
          // If it's an object, try to stringify it
          if (content && typeof content === 'object') {
            content = JSON.stringify(content)
          } else {
            // If it's another type or null/undefined, provide a fallback
            content = String(content || 'Message unavailable')
          }
        }
        
        const html = marked(content)
        return DOMPurify.sanitize(html)
      } catch (error) {
        console.error('Error formatting message:', error)
        return 'Error displaying message'
      }
    }
    
    // Handle key events
    const handleKeyDown = (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        sendMessage()
      }
    }
    
    // Improve error display for specific backend errors
    const formatErrorMessage = (error) => {
      if (!error) return "An unknown error occurred.";
      
      // Handle specific error patterns
      if (typeof error === 'string') {
        // Database error pattern
        if (error.includes("Database error:")) {
          const errorParts = error.split(':');
          if (errorParts.length > 1) {
            const errorDetails = errorParts.slice(1).join(':').trim();
            
            // Handle specific database errors
            if (errorDetails.includes("has no attribute")) {
              return "There appears to be a database schema mismatch. This has been reported to the development team.";
            }
            
            if (errorDetails.includes("No module named")) {
              return "A required module is missing. The system administrator has been notified.";
            }

            if (errorDetails.includes("schema mismatch")) {
              return "The database schema doesn't match the expected structure. The development team has been notified.";
            }
            
            return `Database Error: ${errorDetails}`;
          }
        }
        
        // Module import error pattern
        if (error.includes("cannot import name")) {
          return "System configuration error. Please contact support.";
        }
        
        // System message errors
        if (error.includes("schema mismatch")) {
          return "The system encountered a schema mismatch. This has been reported to the development team.";
        }
        
        // General error message
        return error;
      }
      
      // If error has a message property (like message: "Course schema mismatch detected")
      if (error.message) {
        if (error.message.includes("schema mismatch")) {
          return "A schema mismatch was detected. The development team has been notified.";
        }
        return error.message;
      }
      
      // Fallback for unknown error structures
      return JSON.stringify(error);
    };
    
    // Send a message
    const sendMessage = async () => {
      const message = newMessage.value.trim()
      if (!message || isTyping.value || isFunctionCalling.value) return
      
      // Create a chat if none exists
      if (!props.chatId) {
        const newChatId = chatStore.startNewChat('New Conversation')
        emit('update:chatId', newChatId)
      }
      
      // Clear input and scroll
      newMessage.value = ''
      
      try {
        // Add user message to the store ONLY
        const userMessage = {
          id: Date.now() + '-user',
          role: 'user',
          type: 'user',
          content: message,
          timestamp: new Date()
        }
        
        // Add user message to chat history
        await chatStore.addMessage(props.chatId, userMessage)
        
        // Update chat title if it's the first message
        if (currentMessages.value.length === 1) { // Just added the first message
          const title = generateChatTitle(message)
          chatStore.updateChatTitle(props.chatId, title)
        }
        
        scrollToBottom()
        
        // Get AI response
        isTyping.value = true
        await simulateTyping()
        
        const response = await getAIResponse(message)
        
        // Add AI response to chat history
        await chatStore.addMessage(props.chatId, {
          id: Date.now() + '-ai',
          role: 'assistant',
          type: 'ai',
          content: response,
          timestamp: new Date()
        })
        
      } catch (error) {
        console.error("Error getting AI response:", error)
        
        // Add error message
        await chatStore.addMessage(props.chatId, {
          id: Date.now() + '-ai',
          role: 'assistant',
          type: 'ai',
          content: "I'm sorry, I encountered an error while processing your request. Please try again later.",
          timestamp: new Date()
        })
      } finally {
        isTyping.value = false
        scrollToBottom()
      }
    }
    
    // Simulate AI typing
    const simulateTyping = async () => {
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1500))
    }
    
    // Helper function to handle course-related queries
    const handleCourseQuery = async (message) => {
      try {
        console.log("Handling course query explicitly:", message);
        
        // Create a direct function call to getCourses
        const result = await ChatService.executeFunctionCall("getCourses", {});
        
        // Format the result for display
        if (result && result.courses && result.courses.length > 0) {
          let formattedResponse = "Here are your courses:\n\n";
          result.courses.forEach((course, index) => {
            formattedResponse += `**${index+1}. ${course.title}**\n`;
            if (course.instructor) formattedResponse += `Instructor: ${course.instructor}\n`;
            if (course.progress !== undefined) formattedResponse += `Progress: ${course.progress}%\n`;
            formattedResponse += `\n`;
          });
          return formattedResponse;
        } else {
          return "You don't have any courses currently. You can explore available courses in the course catalog.";
        }
      } catch (error) {
        console.error("Error in direct course handling:", error);
        return "I tried to retrieve your courses but encountered an issue. Please try again later or contact support if the problem persists.";
      }
    }
    
    // Get AI response from backend
    const getAIResponse = async (message) => {
      try {
        // Include context if available
        const payload = {
          id: threadId.value,
          query: message
        }
        
        if (props.context) {
          payload.context = props.context
        }
        
        const data = await ChatService.sendMessage(payload)
        
        // Check if we have a proper response
        if (!data) {
          return "I'm sorry, I couldn't generate a response. Please try again."
        }
        
        // Handle completely empty responses
        if ((!data.content || data.content.trim() === '') 
            && (!data.function_calls || data.function_calls.length === 0)
            && (!data.function_results || data.function_results.length === 0)) {
          console.warn("Received empty response from backend:", data);
          
          // If the query is about courses, provide a fallback response
          const courseTerms = ['course', 'class', 'enrolled', 'classes', 'subject', 'semester'];
          const isCourseQuery = courseTerms.some(term => message.toLowerCase().includes(term));
          
          if (isCourseQuery) {
            // Try to handle course query directly with a function call
            return await handleCourseQuery(message);
          }
          
          return "I apologize, but I couldn't generate a proper response to your question. Could you please try rephrasing or providing more details?";
        }
        
        // Handle error responses
        if (data.error) {
          return `I encountered an issue while processing your request: ${formatErrorMessage(data.error)}`;
        }
        
        // Handle function calls if present
        if (data.function_calls && data.function_calls.length > 0) {
          // Show function calling indicator
          isFunctionCalling.value = true
          
          try {
            // Format the response to include function calls and results
            let response = data.content?.trim() || ""
            
            // For direct function calls, make the response more user-friendly
            const isDirectCall = message.toLowerCase().includes("show") || 
                               message.toLowerCase().includes("get") || 
                               message.toLowerCase().includes("list");
                               
            if (isDirectCall) {
              // Add a simplified response format for direct calls
              let formattedResults = "";
              
              // Format the function results for display
              if (data.function_results && data.function_results.length > 0) {
                const result = data.function_results[0].result;
                
                // Special handling for courses
                if (data.function_calls[0].name === "getCourses" && result.courses) {
                  formattedResults = "Here are your courses:\n\n";
                  result.courses.forEach((course, index) => {
                    formattedResults += `**${index+1}. ${course.title}**\n`;
                    formattedResults += `Instructor: ${course.instructor}\n`;
                    if (course.progress !== undefined) {
                      formattedResults += `Progress: ${course.progress}%\n`;
                    }
                    formattedResults += `\n`;
                  });
                  return formattedResults;
                }
                
                // Special handling for assignments
                if (data.function_calls[0].name === "getAssignments" && result.assignments) {
                  formattedResults = "Here are your assignments:\n\n";
                  result.assignments.forEach((assignment, index) => {
                    formattedResults += `**${index+1}. ${assignment.title}**\n`;
                    formattedResults += `Course: ${assignment.course?.title || 'Unknown'}\n`;
                    formattedResults += `Due Date: ${new Date(assignment.due_date).toLocaleDateString()}\n`;
                    formattedResults += `Status: ${assignment.submission_status}\n`;
                    formattedResults += `\n`;
                  });
                  return formattedResults;
                }
                
                // Special handling for user profile
                if (data.function_calls[0].name === "getUserProfile") {
                  formattedResults = "Here's your profile information:\n\n";
                  const profile = result;
                  formattedResults += `**Name:** ${profile.full_name || profile.username}\n`;
                  formattedResults += `**Email:** ${profile.email}\n`;
                  formattedResults += `**Role:** ${profile.role}\n`;
                  
                  if (profile.enrolled_courses_count !== undefined) {
                    formattedResults += `**Enrolled Courses:** ${profile.enrolled_courses_count}\n`;
                  }
                  
                  return formattedResults;
                }
              }
            }
            
            // Add function calls section if there are any
            if (data.function_calls.length > 0) {
              response += "\n\n**Function Calls:**\n```json\n"
              for (const call of data.function_calls) {
                try {
                  // Extract function name and arguments based on structure
                  let functionName, args;
                  
                  if (call.type === 'function' && call.function) {
                    // Handle format: { type: 'function', function: { name, arguments } }
                    functionName = call.function.name;
                    args = call.function.arguments;
                  } else {
                    // Handle standard format: { name, arguments }
                    functionName = call.name || call.function?.name;
                    args = call.arguments || call.function?.arguments || call.args || {};
                  }
                  
                  // Ensure we have a valid function name
                  if (!functionName || typeof functionName !== 'string') {
                    console.error("Invalid function name:", functionName);
                    continue;
                  }
                  
                  // Ensure arguments is an object
                  if (!args || typeof args !== 'object') {
                    // Parse arguments if they're a string
                    if (typeof args === 'string') {
                      try {
                        if (args.includes('=')) {
                          // Handle Python-style kwargs format (param1='value', param2=42)
                          const argsObject = {};
                          // Split by commas but not those within quotes or brackets
                          const argPairs = args.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)(?=(?:[^{]*{[^}]*})*[^}]*$)/);
                          
                          for (const pair of argPairs) {
                            const [key, val] = pair.split('=').map(s => s.trim());
                            if (key && val) {
                              // Try to parse value if it's JSON-like
                              try {
                                argsObject[key] = JSON.parse(val.replace(/'/g, '"'));
                              } catch (e) {
                                argsObject[key] = val.replace(/^["']|["']$/g, ''); // Remove quotes
                              }
                            }
                          }
                          args = argsObject;
                        } else {
                          // Try standard JSON parsing
                          args = JSON.parse(args);
                        }
                      } catch (e) {
                        console.error(`Error parsing arguments for function ${functionName}:`, e);
                        args = {};
                      }
                    } else {
                      console.error(`Invalid arguments format for function ${functionName}:`, args);
                      args = {};
                    }
                  }
                  
                  response += `${functionName}(${JSON.stringify(args, null, 2)})\n`;
                } catch (e) {
                  console.error("Error formatting function call:", e);
                  const fallbackName = call.type === 'function' && call.function 
                    ? call.function.name || 'unknown'
                    : call.name || 'unknown';
                  response += `${fallbackName}(arguments error)\n`;
                }
              }
              response += "```\n"
            }
            
            // Execute each function call and collect results
            const functionResults = []
            
            for (const call of data.function_calls) {
              try {
                // Extract function name and arguments based on structure
                let functionName, args;
                
                if (call.type === 'function' && call.function) {
                  // Handle format: { type: 'function', function: { name, arguments } }
                  functionName = call.function.name;
                  args = call.function.arguments;
                } else {
                  // Handle standard format: { name, arguments }
                  functionName = call.name || call.function?.name;
                  args = call.arguments || call.function?.arguments || call.args || {};
                }
                
                // Ensure we have a valid function name
                if (!functionName || typeof functionName !== 'string') {
                  console.error("Invalid function name:", functionName);
                  continue;
                }
                
                // Ensure arguments is an object
                if (!args || typeof args !== 'object') {
                  // Parse arguments if they're a string
                  if (typeof args === 'string') {
                    try {
                      if (args.includes('=')) {
                        // Handle Python-style kwargs format (param1='value', param2=42)
                        const argsObject = {};
                        // Split by commas but not those within quotes or brackets
                        const argPairs = args.split(/,(?=(?:[^"]*"[^"]*")*[^"]*$)(?=(?:[^{]*{[^}]*})*[^}]*$)/);
                        
                        for (const pair of argPairs) {
                          const [key, val] = pair.split('=').map(s => s.trim());
                          if (key && val) {
                            // Try to parse value if it's JSON-like
                            try {
                              argsObject[key] = JSON.parse(val.replace(/'/g, '"'));
                            } catch (e) {
                              argsObject[key] = val.replace(/^["']|["']$/g, ''); // Remove quotes
                            }
                          }
                        }
                        args = argsObject;
                      } else {
                        // Try standard JSON parsing
                        args = JSON.parse(args);
                      }
                    } catch (e) {
                      console.error(`Error parsing arguments for function ${functionName}:`, e);
                      args = {};
                    }
                  } else {
                    console.error(`Invalid arguments format for function ${functionName}:`, args);
                    args = {};
                  }
                }
                
                console.log(`Executing function ${functionName} with args:`, args);
                
                // Execute the function
                const result = await ChatService.executeFunctionCall(functionName, args);
                
                // Add to results
                functionResults.push({
                  name: functionName,
                  result: result
                });
              } catch (funcErr) {
                console.error("Error executing function:", funcErr);
                const functionName = 
                  (call.type === 'function' && call.function?.name) 
                    ? call.function.name 
                    : (call.name || call.function?.name || 'unknown');
                    
                functionResults.push({
                  name: functionName,
                  result: { error: funcErr.message || 'Unknown error' }
                });
              }
            }
            
            // Now that we have all results, send a follow-up message to the AI with the results
            if (functionResults.length > 0) {
              // Add the results to the response first
              response += "\n**Function Results:**\n```json\n"
              for (const result of functionResults) {
                try {
                  response += `${result.name}: ${JSON.stringify(result.result, null, 2)}\n\n`
                } catch (e) {
                  console.error("Error formatting function result:", e)
                  response += `${result.name}: (formatting error)\n\n`
                }
              }
              response += "```\n"
              
              // Get a follow-up response from the AI with the function results
              const followUpPayload = {
                id: threadId.value,
                query: message,
                function_results: functionResults
              }
              
              // Only add context if it was in the original request
              if (props.context) {
                followUpPayload.context = props.context
              }
              
              try {
                const followUpResponse = await ChatService.sendMessage(followUpPayload)
                
                if (followUpResponse && followUpResponse.content) {
                  // Append the AI's interpretation of the function results
                  response += "\n**AI Response to Function Results:**\n"
                  response += followUpResponse.content
                }
              } catch (followUpError) {
                console.error("Error getting follow-up response:", followUpError)
                response += "\n\nI wasn't able to provide an interpretation of these results due to an error."
              }
            }
            
            return response
          } catch (funcError) {
            console.error("Error processing function results:", funcError)
            return data.content + "\n\nI tried to process function results, but encountered an error: " + funcError.message
          } finally {
            // Hide function calling indicator
            isFunctionCalling.value = false
          }
        }
        
        // Regular response (no function calls)
        return data.content || "I apologize, but I couldn't generate a proper response."
      } catch (error) {
        console.error("Error getting AI response:", error)
        isFunctionCalling.value = false
        
        // Return a more user-friendly error message based on the error type
        if (error.response) {
          const status = error.response.status
          
          if (status === 401 || status === 403) {
            return "You need to be logged in to use this feature. Please sign in and try again."
          } else if (status === 404) {
            return "The AI service is currently unavailable. Please try again later."
          } else if (status >= 500) {
            return "The server encountered an issue. Our team has been notified and is working to fix it."
          }
        }
        
        return "I'm having trouble connecting to the AI service. Please check your internet connection and try again."
      }
    }
    
    // Generate a title based on the first message
    const generateChatTitle = (message) => {
      return message.length > 30 ? message.substring(0, 30) + '...' : message
    }
    
    // Copy message to clipboard
    const copyToClipboard = async (text) => {
      try {
        await navigator.clipboard.writeText(text)
        // TODO: Show success toast
      } catch (err) {
        console.error("Failed to copy:", err)
        // TODO: Show error toast
      }
    }
    
    // Handle thumbs up feedback
    const thumbsUp = (index) => {
      // TODO: Implement feedback
      console.log('Thumbs up for message:', index)
    }
    
    // Handle thumbs down feedback
    const thumbsDown = (index) => {
      // TODO: Implement feedback
      console.log('Thumbs down for message:', index)
    }
    
    // Clear chat history
    const clearChat = async () => {
      try {
        // First attempt to clear via the service (which will try API first, then local)
        const result = await ChatService.clearChatHistory(props.chatId)
        
        // Update the store (this should work even if the API call failed)
        await chatStore.clearChatHistory(props.chatId)
        
        // Check if there was an error in the API response
        if (result && result.error) {
          console.warn("API error when clearing chat, but local cache was cleared:", result.error)
        }
      } catch (err) {
        console.error("Failed to clear chat:", err)
        
        // Fallback: Try to at least clear the local store
        try {
          await chatStore.clearChatHistory(props.chatId)
          console.log("Cleared chat locally despite API error")
        } catch (storeErr) {
          console.error("Failed to clear chat even locally:", storeErr)
        }
      }
    }
    
    // Toggle Swagger documentation modal
    const toggleSwaggerInfo = async () => {
      try {
        // Toggle the visibility
        showSwaggerInfo.value = !showSwaggerInfo.value
        
        // If showing and we don't have endpoints loaded yet, fetch them
        if (showSwaggerInfo.value && swaggerEndpoints.value.length === 0) {
          loadingSwagger.value = true
          swaggerError.value = null
          
          try {
            // Use the ChatService to get the Swagger endpoints
            const endpoints = await ChatService.getSwaggerEndpoints()
            swaggerEndpoints.value = endpoints
          } catch (error) {
            console.error("Error loading API documentation:", error)
            swaggerError.value = "Failed to load API documentation"
          } finally {
            loadingSwagger.value = false
          }
        }
      } catch (err) {
        console.error("Error toggling Swagger info:", err)
        swaggerError.value = "An error occurred"
      }
    }
    
    return {
      currentMessages,
      newMessage,
      isTyping,
      isFunctionCalling,
      messagesContainer,
      messageInput,
      chatStore,
      sendMessage,
      formatMessage,
      scrollToBottom,
      handleKeyDown,
      copyToClipboard,
      thumbsUp,
      thumbsDown,
      swaggerEndpoints,
      showSwaggerInfo,
      loadingSwagger,
      swaggerError,
      clearChat,
      toggleSwaggerInfo
    }
  }
}
</script>

<style scoped>
/* Hide scrollbar for Chrome, Safari and Opera */
.overflow-y-auto::-webkit-scrollbar {
  display: none;
}

/* Hide scrollbar for IE, Edge and Firefox */
.overflow-y-auto {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}

/* Markdown styles */
:deep(.prose) {
  max-width: none;
}

:deep(.prose pre) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0.5rem;
  border-radius: 0.25rem;
  margin: 0.5rem 0;
}

:deep(.prose code) {
  color: inherit;
  background-color: rgba(0, 0, 0, 0.05);
  padding: 0.1rem 0.25rem;
  border-radius: 0.25rem;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #f9f9f9;
  border-radius: 8px;
  overflow: hidden;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  height: 100%;
  opacity: 0.7;
  padding: 2rem;
}

.empty-state-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.empty-state-text {
  font-size: 0.875rem;
  max-width: 300px;
}

.message {
  display: flex;
  margin-bottom: 1rem;
  max-width: 80%;
}

.message.user {
  margin-left: auto;
}

.message.ai {
  margin-right: auto;
}

.message-content {
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  font-size: 0.875rem;
  position: relative;
}

.message-content.user {
  background-color: #e7f2ff;
  color: #0d47a1;
  border-top-right-radius: 0;
}

.message-content.ai {
  background-color: #f0f0f0;
  color: #333;
  border-top-left-radius: 0;
}

.message-actions {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  justify-content: flex-end;
}

.message-action-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.chat-input-container {
  border-top: 1px solid #e0e0e0;
  padding: 1rem;
  background-color: white;
}

.chat-input-wrapper {
  display: flex;
  border: 1px solid #e0e0e0;
  border-radius: 1.5rem;
  padding: 0.5rem 0.75rem;
  background-color: white;
}

.chat-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 0.875rem;
  resize: none;
  background: transparent;
  max-height: 120px;
}

.send-button {
  background: none;
  border: none;
  color: #4299e1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-button:disabled {
  color: #a0aec0;
  cursor: not-allowed;
}

.typing-indicator {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: #f0f0f0;
  border-radius: 1rem;
  max-width: 60px;
  margin-right: auto;
}

.typing-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #888;
  margin: 0 2px;
  animation: typing 1.5s infinite ease-in-out;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.5s;
}

.typing-dot:nth-child(3) {
  animation-delay: 1s;
}

.function-calling-indicator {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: #f0f2ff;
  border: 1px solid #e0e6ff;
  border-radius: 1rem;
  max-width: 200px;
  margin-right: auto;
}

.function-icon {
  margin-right: 8px;
  color: #4f46e5;
}

.function-text {
  font-size: 0.75rem;
  color: #4f46e5;
  margin-left: 8px;
}

.swagger-tools {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
  gap: 8px;
}

.swagger-button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  background-color: #f5f5f5;
  font-size: 12px;
  cursor: pointer;
}

.swagger-button:hover {
  background-color: #e9e9e9;
}

.clear-button {
  background-color: #fff1f1;
  border-color: #ffcfcf;
  color: #e53e3e;
}

.clear-button:hover {
  background-color: #ffeded;
}

.swagger-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
}

.swagger-modal-content {
  background-color: white;
  border-radius: 8px;
  width: 90%;
  max-width: 700px;
  max-height: 70vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.swagger-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.modal-close-button {
  background: none;
  border: none;
  cursor: pointer;
}

.swagger-endpoints {
  padding: 1rem;
  max-height: 60vh;
  overflow-y: auto;
}

.swagger-help-text {
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: #666;
}

.swagger-endpoint-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.swagger-endpoint-item {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid #e0e0e0;
}

.swagger-endpoint-item:last-child {
  border-bottom: none;
}

.method {
  font-weight: bold;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
}

.method.get {
  background-color: #e3f2fd;
  color: #0d47a1;
}

.method.post {
  background-color: #e8f5e9;
  color: #1b5e20;
}

.method.put {
  background-color: #fff3e0;
  color: #e65100;
}

.method.delete {
  background-color: #ffebee;
  color: #b71c1c;
}

.path {
  font-family: monospace;
}

.description {
  font-size: 0.875rem;
  color: #666;
  flex-basis: 100%;
}

.swagger-loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.swagger-error {
  color: #e53e3e;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
}

.swagger-empty {
  color: #666;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

