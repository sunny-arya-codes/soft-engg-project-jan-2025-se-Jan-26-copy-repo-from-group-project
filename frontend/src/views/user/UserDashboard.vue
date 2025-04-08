<script>
// Import components first, then other dependencies
import SideNavBar from '@/layouts/SideNavBar.vue'
import ChatBotWrapper from '@/components/ChatBotWrapper.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AlertMessage from '@/components/common/AlertMessage.vue'

// Then import Vue reactivity
import { ref } from 'vue'

// Then import utilities and services
import api from '@/utils/api'
import { useToast } from 'vue-toastification'
import formatDateFunc from '@/utils/formatDate'
// import { RoadmapService } from '@/services/roadmap.service' // Roadmap temporarily removed

// Finally import store-related items
import { useChatStore } from '@/stores/useChatStore'
import useAuthStore from '@/stores/useAuthStore'
import { useCourseStore } from '@/stores/courseStore'
import { FacultyNotificationService } from '@/services/facultyNotification.service'

export default {
  name: 'DashboardView',
  components: {
    SideNavBar,
    ChatBotWrapper,
    LoadingSpinner,
    AlertMessage,
  },
  data() {
    return {
      showAlertMessage: false,
      isDataLoading: false,
      queryEmpty: true,
      showSplitScreen: false,
      recommendedMaterials: [],
      personalizedRoadmaps: [],
      bookmarkedMaterials: [],
      isDevelopment: import.meta.env.VITE_NODE_ENV === 'development',
      notifications: [],
      userInfo: {
        name: 'User',
      },
      courses: [],
      learningInsights: {
        studyPatterns: {
          optimalTime: 'morning hours',
          preferredContent: 'video content',
          recommendedSchedule: '9-11am'
        },
        suggestions: {
          contentType: 'practice exercises',
          reason: 'interaction patterns'
        },
        opportunities: [
          {
            type: 'quiz',
            subject: 'Data Structures Quiz',
            reason: 'knowledge retention'
          },
          {
            type: 'review',
            subject: 'Web Security Fundamentals',
            reason: 'preparation'
          }
        ],
        personalizedMessage: "Based on your learning activity, you're showing consistent progress in your courses.",
        learningTraits: [
          { type: 'strength', description: 'Visual learning preference' },
          { type: 'improvement', description: 'Consistent study schedule' }
        ],
        studyStats: [
          { label: 'Study Sessions', value: '12', unit: 'this month', trend: 5 },
          { label: 'Average Duration', value: '45', unit: 'minutes', trend: -2 },
          { label: 'Active Days', value: '8', unit: 'of 30', trend: 10 }
        ],
        recommendedTopics: [
          { title: 'Advanced Data Structures', reason: 'Based on your quiz performance', icon: 'data_object' },
          { title: 'Web Security Fundamentals', reason: 'Complements your current progress', icon: 'security' }
        ],
        learningOpportunities: [
          { 
            type: 'quiz', 
            title: 'Algorithm Challenge', 
            description: 'Test your understanding of sorting algorithms',
            estimated_time: '20 min'
          },
          {
            type: 'review',
            title: 'Review Session',
            description: 'Consolidate your understanding of recent topics',
            estimated_time: '30 min'
          }
        ],
        stats: {
          completion_rate: 0.65,
          quiz_average: 0.78,
          consistency_score: 7.5,
          time_invested: 42
        },
        performanceAreas: {
          strengths: [
            { topic: 'Data Structures', score: 0.85 },
            { topic: 'Web Development', score: 0.78 }
          ],
          improvements: [
            { topic: 'Algorithms', score: 0.45 },
            { topic: 'Database Design', score: 0.55 }
          ]
        }
      },
      loadingInsights: false
    }
  },
  computed: {
    mainContentClass() {
      return {
        'md:grid-cols-2': !this.showSplitScreen,
        'md:grid-cols-3': this.showSplitScreen,
      }
    },
    chatStore() {
      return useChatStore()
    },
    authStore() {
      return useAuthStore()
    },
    courseStore() {
      return useCourseStore()
    },
    getStatusClass() {
      return (status) => {
        return {
          'bg-green-100 text-green-800': status === 'active',
          'bg-yellow-100 text-yellow-800': status === 'pending',
          'bg-gray-100 text-gray-800': status === 'completed',
          'bg-red-100 text-red-800': status === 'inactive',
        }
      }
    },
    getStatusText() {
      return (status) => {
        const statusMap = {
          active: 'Active',
          pending: 'Pending',
          completed: 'Completed',
          inactive: 'Inactive',
        }
        return statusMap[status] || 'Unknown'
      }
    }
  },
  methods: {
    showSuccessToast(msg) {
      const toast = useToast()
      toast.success(msg, { timeout: 3000 })
    },
    showErrorToast(error, defaultMessage) {
      const toast = useToast()
      const message = error.response?.data?.message || defaultMessage
      toast.error(message)
    },
    startMaterial(material) {
      if (material.tutorial_url === null) {
        this.showAlertMessage = true
        setTimeout(() => {
          this.showAlertMessage = false
        }, 3000)
      } else {
        window.open(material.tutorial_url, '_blank')
      }
      console.log('Starting material:', material.title)
    },
    viewRoadmap(roadmap) {
      if (roadmap.courseId) {
        this.$router.push(`/user/roadmap/${roadmap.courseId}`)
      } else {
      this.$router.push(`/user/roadmap/${roadmap.id}`)
      }
    },
    removeBookmark(bookmark_id) {
      this.deleteBookMarkedMaterial(bookmark_id)
    },
    toggleSplitScreen() {
      this.showSplitScreen = !this.showSplitScreen

      // If we're closing split screen, ensure chat is also closed
      if (!this.showSplitScreen && this.chatStore.isOpen) {
        this.chatStore.closeChat()
      }
    },
    activateChat() {
      const chatStore = useChatStore()
      // First make sure we have a valid selected chat
      if (chatStore.chatHistory.length > 0 && !chatStore.currentChatId) {
        chatStore.setCurrentChat(chatStore.chatHistory[0].id)
      } else if (chatStore.chatHistory.length === 0) {
        // Create a new chat if there are none
        chatStore.startNewChat('New Conversation')
      }

      // Open the chat
      chatStore.isOpen = true
      console.log('Chat activated from dashboard, open state:', chatStore.isOpen)
    },
    // API calls
    async getRecommendedCourses() {
      try {
        this.isDataLoading = true
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No authentication token found')

        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }

        const response = await api.get('/user/recommended-courses', headers)
        if (response.status !== 200) throw new Error('Failed to fetch user data')
        console.log(response.data)
        this.recommendedMaterials = response.data
        this.showSuccessToast('Recommended Courses fetched successfully')
      } catch (error) {
        this.showErrorToast(error, 'Failed to Load Recommended Courses')
        throw error
      } finally {
        this.isDataLoading = false
      }
    },
    async getBookMarkedMaterials() {
      try {
        this.isDataLoading = true
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No authentication token found')

        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }

        const response = await api.get('/user/bookmarked-materials', headers)
        if (response.status !== 200) throw new Error('Failed to fetch user data')
        console.log(response.data)
        this.bookmarkedMaterials = response.data
        this.showSuccessToast('Bookmarked Materials fetched successfully')
      } catch (error) {
        this.showErrorToast(error, 'Failed to Load Bookmarked Materials')
        throw error
      } finally {
        this.isDataLoading = false
      }
    },
    async deleteBookMarkedMaterial(bookmarkId) {
      try {
        this.isDataLoading = true
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No authentication token found')

        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }

        const response = await api.delete(`/user/bookmarked-materials/${bookmarkId}`, headers)
        if (response.status !== 200) throw new Error('Failed to delete bookmarked material')
        this.showSuccessToast('Bookmarked Material deleted successfully')
        // remove the bookmark from the list
        this.bookmarkedMaterials = this.bookmarkedMaterials.filter(
          (bookmark) => bookmark.id !== bookmarkId
        )
      } catch (error) {
        this.showErrorToast(error, 'Failed to delete bookmarked material')
        throw error
      } finally {
        this.isDataLoading = false
      }
    },
    async getNotifications() {
      try {
        const response = await FacultyNotificationService.getRecentNotifications()
            if (response && response.data) {
          this.notifications = response.data
            }
      } catch (error) {
        console.error('Failed to load notifications:', error)
      }
    },
    getNotificationTypeClass(type) {
      return {
        'bg-blue-100 text-blue-800': type === 'course',
        'bg-purple-100 text-purple-800': type === 'system',
      }
    },
    getNotificationPriorityClass(priority) {
      return {
        'bg-green-100 text-green-800': priority === 'low',
        'bg-yellow-100 text-yellow-800': priority === 'medium',
        'bg-orange-100 text-orange-800': priority === 'high',
        'bg-red-100 text-red-800': priority === 'urgent',
      }
    },
    async loadCourses() {
      try {
        const response = await this.courseStore.fetchCourses()
        if (response && response.data) {
          this.courses = response.data
        }
      } catch (error) {
        console.error('Failed to load courses:', error)
        const toast = useToast()
        toast.error('Failed to load your courses')
      }
    },
    async getUserInfo() {
      try {
        const user = this.authStore.user
        if (user) {
          this.userInfo = {
            name: user.name || 'Student',
            email: user.email || '',
          }
        }
      } catch (error) {
        console.error('Error getting user info:', error)
      }
    },
    formatTime(timestamp) {
      return formatDateFunc(timestamp)
    },
    async getLearningInsights() {
      try {
        // Set loading state
        this.isDataLoading = true;
        this.loadingInsights = true;
        
        const token = localStorage.getItem('token');
        if (!token) throw new Error('No authentication token found');

        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        };

        // Get insights from API without fallback to mock data
        const response = await api.get('/user/learning-insights', headers);
        
        if (response.status === 200 && response.data) {
          this.learningInsights = response.data;
          console.log('Fetched learning insights from API successfully');
          this.showSuccessToast('Your learning insights have been updated');
        } else {
          // Clear existing data if response is not good
          this.learningInsights = {};
          console.error('Invalid response from learning insights API');
        }
      } catch (error) {
        // Clear any existing data on error
        this.learningInsights = {};
        console.error('Error in getLearningInsights:', error);
        // Removed error toast - no user notification on failure
      } finally {
        this.isDataLoading = false;
        this.loadingInsights = false;
      }
    },
    // Temporarily commented out roadmap functionality
    /*
    async getPersonalizedRoadmaps() {
      try {
        this.isDataLoading = true
        const token = localStorage.getItem('token')
        if (!token) throw new Error('No authentication token found')

        // Always set fallback data first so we have something to show immediately
        this.personalizedRoadmaps = [
          {
            id: 1,
            title: 'Full Stack Development',
            progress: 45,
            totalSteps: 12,
            completedSteps: 5,
          },
          {
            id: 2,
            title: 'Data Structures & Algorithms',
            progress: 30,
            totalSteps: 10,
            completedSteps: 3,
          },
          {
            id: 3,
            title: 'Machine Learning Basics',
            progress: 20,
            totalSteps: 8,
            completedSteps: 2,
          },
          {
            id: 4,
            title: 'Software Engineering Practices',
            progress: 60,
            totalSteps: 15,
            completedSteps: 9,
          },
        ]

        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }

        // Try to get the enrolled courses first
        const courses = await this.courseStore.fetchCourses()
        
        if (!courses || !courses.data || !courses.data.length) {
          console.log('No courses found for roadmaps')
          return // Keep fallback data that we already set
        }
        
        // For each course, try to get a roadmap
        const roadmaps = []
        
        for (const course of courses.data.slice(0, 4)) { // Limit to first 4 courses for performance
          try {
            const roadmapData = await RoadmapService.getRoadmap(course.id)
            if (roadmapData && roadmapData.roadmap) {
              const roadmap = roadmapData.roadmap
              
              // Format the roadmap for display
              roadmaps.push({
                id: roadmap.id,
                title: roadmap.title || `Learning Path for ${course.title}`,
                progress: Math.round((roadmap.completedSteps / roadmap.totalSteps) * 100) || 0,
                totalSteps: roadmap.totalSteps || 0,
                completedSteps: roadmap.completedSteps || 0,
                courseId: course.id
              })
            }
          } catch (error) {
            console.error(`Error fetching roadmap for course ${course.id}:`, error)
            // If we can't get a roadmap, try the next course
          }
        }
        
        // Only replace fallback data if we actually got at least one real roadmap
        if (roadmaps.length > 0) {
          this.personalizedRoadmaps = roadmaps
          this.showSuccessToast('Learning paths loaded successfully')
        }
      } catch (error) {
        console.error('Failed to fetch personalized roadmaps:', error)
        this.showErrorToast(error, 'Failed to load learning paths')
        // No need to set fallback data here as we already set it at the beginning
      } finally {
        this.isDataLoading = false
      }
    },
    */
  },
  mounted() {
    this.getRecommendedCourses()
    this.getBookMarkedMaterials()
    this.getNotifications()
    this.getUserInfo()
    this.loadCourses()
    this.getLearningInsights() // Fetch AI learning insights
    // this.getPersonalizedRoadmaps() // Roadmap temporarily removed

    // Make sure the GlobalChat component from App.vue is initialized
    const chatStore = useChatStore()
    if (!chatStore.initialized) {
      chatStore.initialize()
    }
    
    // Check for roadmap unavailable message from route redirect
    if (this.$route.query.message === 'roadmap-unavailable') {
      const toast = useToast()
      toast.info('Learning paths feature is temporarily unavailable as we work on improvements. Check back soon!', { 
        timeout: 5000,
        closeButton: true
      })
    }
  },
  setup() {
    // Authentication and course store
    const authStore = useAuthStore();
    const courseStore = useCourseStore();
    const toast = useToast();

    // User state
    const userInfo = ref({});
    const courses = ref([]);
    const loadingInsights = ref(false);
    
    // Helper methods for the learning insights section
    const opportunityIcon = (type) => {
      switch(type) {
        case 'quiz': return 'quiz';
        case 'review': return 'summarize';
        case 'practice': return 'code';
        default: return 'school';
      }
    };
    
    const getCompletionClass = (rate) => {
      if (rate >= 0.75) return 'bg-green-100 text-green-800';
      if (rate >= 0.5) return 'bg-blue-100 text-blue-800';
      if (rate >= 0.25) return 'bg-yellow-100 text-yellow-800';
      return 'bg-red-100 text-red-800';
    };
    
    const getScoreClass = (score) => {
      if (score >= 0.85) return 'bg-green-100 text-green-800';
      if (score >= 0.7) return 'bg-blue-100 text-blue-800';
      if (score >= 0.6) return 'bg-yellow-100 text-yellow-800';
      return 'bg-red-100 text-red-800';
    };

    // Loading data methods
    // ... existing code ...

    // Return functions for template use
    return {
      authStore,
      courseStore,
      userInfo,
      courses,
      loadingInsights,
      opportunityIcon,
      getCompletionClass,
      getScoreClass
    };
  }
}
</script>

<template>
  <div>
    <div class="flex h-screen">
      <div>
        <SideNavBar />
      </div>
      <div class="flex-1 p-6 overflow-y-auto bg-gray-50">
        <div class="max-w-7xl mx-auto">
          <!-- Alert Message -->
          <AlertMessage
            v-if="showAlertMessage"
            message="This material doesn't have a learning path or tutorial yet."
          />

          <!-- Loading Spinner -->
          <LoadingSpinner v-if="isDataLoading" />

          <!-- Recommended Section -->
          <div class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Recommended for You</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <div
                v-for="material in recommendedMaterials"
                :key="material.id"
                class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow"
              >
                <div class="flex items-start space-x-4">
                  <img
                    :src="material.thumbnail_path"
                    :alt="material.title"
                    class="w-16 h-16 rounded-lg object-cover"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="flex items-start justify-between">
                      <div class="min-w-0">
                        <h3 class="font-semibold text-gray-800 truncate">{{ material.title }}</h3>
                        <span class="text-sm text-gray-500">{{ material.type }}</span>
                      </div>
                    </div>
                    <p class="text-sm text-gray-600 mt-2 line-clamp-2">{{ material.reason }}</p>
                    <button
                      @click="startMaterial(material)"
                      class="mt-3 text-sm text-maroon-600 hover:text-maroon-700 font-medium inline-flex items-center"
                    >
                      Start Learning
                      <span class="material-icons text-sm ml-1">arrow_forward</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Bookmarked Materials - Moved above Learning Insights -->
          <div class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Bookmarked Materials</h2>
            <div class="space-y-4">
              <div
                v-for="material in bookmarkedMaterials"
                :key="material.id"
                class="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow group"
              >
                <div class="flex items-start justify-between">
                  <div class="min-w-0 flex-1">
                    <h3 class="font-semibold text-gray-800 truncate">{{ material.title }}</h3>
                    <div class="flex items-center space-x-2 mt-1">
                      <span class="text-sm text-gray-500">{{ material.type }}</span>
                      <span class="text-gray-300">•</span>
                      <span class="text-sm text-gray-500 truncate">{{ material.author }}</span>
                    </div>
                    <div class="text-sm text-gray-500 mt-1">
                      Bookmarked on {{ new Date(material.date_bookmarked).toLocaleDateString() }}
                    </div>
                  </div>
                  <button
                    @click="removeBookmark(material.id)"
                    class="text-gray-400 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <span class="material-icons">bookmark_remove</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Learning Insights - Only show if data successfully loaded -->
          <div v-if="learningInsights && Object.keys(learningInsights).length > 0 && !loadingInsights" class="mb-8">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold text-gray-800">Your Learning Insights</h2>
              <button @click="getLearningInsights" class="text-maroon-600 hover:text-maroon-800 transition-colors flex items-center">
                <span class="material-symbols-outlined mr-1">refresh</span>
                Refresh Insights
              </button>
            </div>
            
            <div v-if="loadingInsights" class="flex justify-center py-6">
              <LoadingSpinner size="lg" />
            </div>
            
            <div class="space-y-6">
              <!-- Learning Profile -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div class="flex items-center mb-4">
                  <span class="material-symbols-outlined text-2xl text-maroon-600 mr-3">analytics</span>
                  <h3 class="text-lg font-medium text-gray-800">Your Learning Profile</h3>
                </div>
                
                <p class="text-gray-700 mb-4">{{ learningInsights.personalizedMessage }}</p>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
                  <div v-for="(trait, index) in learningInsights.learningTraits" :key="index" 
                       class="bg-gray-50 rounded-lg p-3 flex items-center">
                    <span class="material-symbols-outlined text-maroon-600 mr-2">{{ 
                      trait.type === 'strength' ? 'trending_up' : 
                      trait.type === 'improvement' ? 'trending_flat' : 'trending_down'
                    }}</span>
                    <span class="text-sm text-gray-700">{{ trait.description }}</span>
                  </div>
                </div>
              </div>
              
              <!-- Study Patterns -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div class="flex items-center mb-4">
                  <span class="material-symbols-outlined text-2xl text-maroon-600 mr-3">schedule</span>
                  <h3 class="text-lg font-medium text-gray-800">Study Pattern Analysis</h3>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div v-for="(stat, index) in learningInsights.studyStats" :key="index" 
                       class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">{{ stat.label }}</span>
                    <div class="flex items-baseline">
                      <span class="text-2xl font-medium text-gray-800 mr-2">{{ stat.value }}</span>
                      <span class="text-xs text-gray-500">{{ stat.unit }}</span>
                    </div>
                    <div class="text-xs mt-1" :class="stat.trend > 0 ? 'text-green-600' : 'text-red-600'">
                      <span class="material-symbols-outlined text-xs align-middle">
                        {{ stat.trend > 0 ? 'trending_up' : 'trending_down' }}
                      </span>
                      {{ Math.abs(stat.trend) }}% {{ stat.trend > 0 ? 'increase' : 'decrease' }} from last month
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Content Recommendations -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div class="flex items-center mb-4">
                  <span class="material-symbols-outlined text-2xl text-maroon-600 mr-3">menu_book</span>
                  <h3 class="text-lg font-medium text-gray-800">Recommended Topics</h3>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div v-for="(topic, index) in learningInsights.recommendedTopics" :key="index" 
                       class="flex items-start p-3 rounded-lg border border-gray-100 hover:bg-gray-50 transition-colors cursor-pointer">
                    <span class="material-symbols-outlined text-maroon-600 mr-3 mt-1">{{ topic.icon || 'auto_stories' }}</span>
                    <div>
                      <h4 class="font-medium text-gray-800">{{ topic.title }}</h4>
                      <p class="text-sm text-gray-600 mt-1">{{ topic.reason }}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Learning Opportunities -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div class="flex items-center mb-4">
                  <span class="material-symbols-outlined text-2xl text-maroon-600 mr-3">tips_and_updates</span>
                  <h3 class="text-lg font-medium text-gray-800">Learning Opportunities</h3>
                </div>
                
              <div class="space-y-4">
                  <div v-for="(opportunity, index) in learningInsights.learningOpportunities" :key="index" 
                       class="flex items-start border-b border-gray-100 pb-3 last:border-0">
                    <div class="bg-maroon-50 p-2 rounded-lg mr-3">
                      <span class="material-symbols-outlined text-maroon-600">{{ opportunityIcon(opportunity.type) }}</span>
                    </div>
                    <div class="flex-1">
                      <h4 class="font-medium text-gray-800">{{ opportunity.title }}</h4>
                      <p class="text-sm text-gray-600 mt-1">{{ opportunity.description }}</p>
                      <div class="mt-2">
                        <button class="text-maroon-600 hover:text-maroon-800 text-sm font-medium transition-colors">
                          Take action
                        </button>
                      </div>
                    </div>
                    <div class="text-xs text-gray-500 whitespace-nowrap">
                      {{ opportunity.estimated_time || '15 min' }}
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Performance Stats -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
                <div class="flex items-center mb-4">
                  <span class="material-symbols-outlined text-2xl text-maroon-600 mr-3">leaderboard</span>
                  <h3 class="text-lg font-medium text-gray-800">Performance Statistics</h3>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                  <div class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">Course Completion Rate</span>
                    <div class="flex items-center">
                      <span class="text-2xl font-medium text-gray-800 mr-2">
                        {{ Math.floor(learningInsights.stats.completion_rate * 100) }}%
                      </span>
                      <span class="px-2 py-0.5 rounded text-xs" :class="getCompletionClass(learningInsights.stats.completion_rate)">
                        {{ 
                          learningInsights.stats.completion_rate >= 0.75 ? 'Excellent' : 
                          learningInsights.stats.completion_rate >= 0.5 ? 'Good' : 
                          learningInsights.stats.completion_rate >= 0.25 ? 'Fair' : 'Needs Work'
                        }}
                      </span>
                    </div>
                  </div>
                  
                  <div class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">Quiz Average</span>
                    <div class="flex items-center">
                      <span class="text-2xl font-medium text-gray-800 mr-2">
                        {{ Math.floor(learningInsights.stats.quiz_average * 100) }}%
                      </span>
                      <span class="px-2 py-0.5 rounded text-xs" :class="getScoreClass(learningInsights.stats.quiz_average)">
                        {{ 
                          learningInsights.stats.quiz_average >= 0.85 ? 'Excellent' : 
                          learningInsights.stats.quiz_average >= 0.7 ? 'Good' : 
                          learningInsights.stats.quiz_average >= 0.6 ? 'Fair' : 'Needs Work'
                        }}
                      </span>
                    </div>
                  </div>
                  
                  <div class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">Consistency Score</span>
                    <div class="flex items-center">
                      <span class="text-2xl font-medium text-gray-800 mr-2">
                        {{ learningInsights.stats.consistency_score.toFixed(1) }}
                      </span>
                      <span class="text-xs text-gray-500">/ 10</span>
                    </div>
                  </div>
                  
                  <div class="flex flex-col">
                    <span class="text-sm text-gray-500 mb-1">Time Invested</span>
                    <div class="flex items-baseline">
                      <span class="text-2xl font-medium text-gray-800 mr-2">
                        {{ learningInsights.stats.time_invested }}
                    </span>
                      <span class="text-xs text-gray-500">hours</span>
                    </div>
                  </div>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div class="border border-gray-100 rounded-lg p-4">
                    <h4 class="text-sm font-medium text-gray-700 mb-3">Areas of Strength</h4>
                    <div class="space-y-2">
                      <div v-for="(area, index) in learningInsights.performanceAreas.strengths" :key="index" 
                          class="flex items-center justify-between">
                        <span class="text-sm text-gray-600">{{ area.topic }}</span>
                        <div class="w-32 bg-gray-100 rounded-full h-2.5">
                          <div class="bg-green-500 h-2.5 rounded-full" :style="`width: ${area.score * 100}%`"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div class="border border-gray-100 rounded-lg p-4">
                    <h4 class="text-sm font-medium text-gray-700 mb-3">Areas for Improvement</h4>
                    <div class="space-y-2">
                      <div v-for="(area, index) in learningInsights.performanceAreas.improvements" :key="index" 
                          class="flex items-center justify-between">
                        <span class="text-sm text-gray-600">{{ area.topic }}</span>
                        <div class="w-32 bg-gray-100 rounded-full h-2.5">
                          <div class="bg-maroon-500 h-2.5 rounded-full" :style="`width: ${area.score * 100}%`"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                </div>
              </div>
            </div>

            <!-- AI Chatbot (Split Screen Mode) -->
            <div v-if="showSplitScreen" class="h-[calc(100vh-12rem)]">
              <ChatBotWrapper />
          </div>
        </div>
      </div>
    </div>

    <!-- Floating Chat Toggle Button -->
    <button
      v-if="!chatStore.isOpen && !showSplitScreen"
      @click="activateChat"
      class="fixed bottom-6 right-6 bg-maroon-600 text-white rounded-full p-4 shadow-lg hover:bg-maroon-700 transition-all z-[100] group"
    >
      <span class="material-icons">chat</span>
      <span
        class="absolute right-full mr-3 top-1/2 -translate-y-1/2 px-3 py-1 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap"
      >
        Ask Learning Assistant
      </span>
    </button>
  </div>
</template>

<style scoped>
.material-icons {
  font-size: inherit;
  line-height: inherit;
  vertical-align: middle;
}

/* Smooth transitions */
.grid {
  transition: grid-template-columns 0.3s ease-in-out;
}

/* Improved scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
.loading-overlay {
  @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50;
}

/* Make sure the chat components are properly positioned */
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
}

.h-screen {
  height: calc(100vh - 4rem); /* Adjust for header height */
  position: relative;
  z-index: 0; /* Ensure proper stacking with global chat */
}
</style>
