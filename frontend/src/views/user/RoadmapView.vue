<template>
  <div class="flex h-screen bg-gray-50">
    <SideNavBar />
    <div class="flex-1 overflow-hidden">
      <div class="h-full flex">
        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto p-6">
          <!-- Loading State -->
          <div v-if="loading" class="flex items-center justify-center h-full">
            <div class="text-center">
              <div class="w-16 h-16 border-4 border-maroon-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p class="mt-4 text-gray-600">Loading roadmap...</p>
            </div>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="flex items-center justify-center h-full">
            <div class="text-center">
              <div class="w-16 h-16 mx-auto text-red-500">
                <span class="material-icons text-6xl">error_outline</span>
              </div>
              <p class="mt-4 text-gray-800 font-medium">{{ error }}</p>
              <button 
                @click="$router.push('/user/courses')"
                class="mt-4 px-4 py-2 bg-maroon-600 text-white rounded-lg hover:bg-maroon-700 transition-colors">
                Back to Courses
              </button>
            </div>
          </div>

          <!-- Roadmap Content -->
          <template v-else-if="roadmap">
            <!-- Header -->
            <div class="max-w-5xl mx-auto mb-8">
              <div class="flex items-center justify-between">
                <div>
                  <h1 class="text-3xl font-bold text-gray-900">{{ roadmap.title }}</h1>
                  <p class="text-gray-600 mt-1">{{ roadmap.description }}</p>
                </div>
                <div class="flex items-center space-x-4">
                  <div class="text-right">
                    <div class="text-sm text-gray-600">Overall Progress</div>
                    <div class="text-2xl font-bold text-gray-900">
                      {{ Math.round((roadmap.completedSteps / roadmap.totalSteps) * 100) }}%
                    </div>
                  </div>
                  <div class="h-16 w-16 rounded-full bg-maroon-100 flex items-center justify-center">
                    <span class="material-icons text-maroon-600 text-2xl">timeline</span>
                  </div>
                </div>
              </div>

              <!-- Progress Bar -->
              <div class="mt-6 bg-white rounded-xl shadow-sm border border-gray-100 p-4">
                <div class="flex items-center justify-between text-sm mb-2">
                  <span class="font-medium text-gray-900">Learning Progress</span>
                  <span class="text-gray-600">{{ roadmap.completedSteps }} of {{ roadmap.totalSteps }} Steps Completed</span>
                </div>
                <div class="w-full bg-gray-100 rounded-full h-2.5">
                  <div 
                    class="bg-maroon-600 h-2.5 rounded-full transition-all duration-500"
                    :style="{ width: `${(roadmap.completedSteps / roadmap.totalSteps) * 100}%` }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- Roadmap Timeline -->
            <div class="max-w-5xl mx-auto">
              <div class="space-y-8">
                <div 
                  v-for="(milestone, index) in roadmap.milestones" 
                  :key="milestone.id"
                  class="relative"
                >
                  <!-- Timeline Line -->
                  <div 
                    v-if="index < roadmap.milestones.length - 1"
                    class="absolute left-8 top-14 bottom-0 w-0.5 bg-gray-200"
                  ></div>

                  <!-- Milestone Card -->
                  <div 
                    class="bg-white rounded-xl shadow-sm border border-gray-100 relative"
                    :class="{ 'opacity-60': milestone.locked }"
                  >
                    <!-- Milestone Header -->
                    <div class="p-6 flex items-start space-x-4">
                      <div 
                        class="w-16 h-16 rounded-full flex items-center justify-center flex-shrink-0"
                        :class="getMilestoneStatusClasses(milestone.status).bgClass"
                      >
                        <span 
                          class="material-icons text-2xl"
                          :class="getMilestoneStatusClasses(milestone.status).textClass"
                        >
                          {{ getMilestoneStatusIcon(milestone.status) }}
                        </span>
                      </div>
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center justify-between">
                          <div>
                            <h3 class="text-xl font-semibold text-gray-900">{{ milestone.title }}</h3>
                            <p class="text-gray-600 mt-1">{{ milestone.description }}</p>
                          </div>
                          <div class="text-right">
                            <span 
                              class="px-3 py-1 rounded-full text-sm font-medium"
                              :class="getMilestoneStatusClasses(milestone.status).badgeClass"
                            >
                              {{ milestone.status }}
                            </span>
                            <div class="text-sm text-gray-500 mt-1">
                              {{ milestone.estimatedTime }}
                            </div>
                          </div>
                        </div>
                        
                        <!-- Status Controls -->
                        <div class="mt-4 flex justify-end space-x-2" v-if="!milestone.locked">
                          <button 
                            @click="updateMilestoneStatus(milestone, 'in_progress')"
                            class="px-3 py-1 rounded-md text-sm bg-blue-100 text-blue-800 hover:bg-blue-200 transition-colors"
                            :class="{ 'bg-blue-200': milestone.status === 'in_progress' }"
                          >
                            In Progress
                          </button>
                          <button 
                            @click="updateMilestoneStatus(milestone, 'completed')"
                            class="px-3 py-1 rounded-md text-sm bg-green-100 text-green-800 hover:bg-green-200 transition-colors"
                            :class="{ 'bg-green-200': milestone.status === 'completed' }"
                          >
                            Complete
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- Learning Materials -->
                    <div v-if="milestone.materials && milestone.materials.length > 0" class="px-6 pb-6">
                      <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div
                          v-for="material in milestone.materials"
                          :key="material.id"
                          class="bg-gray-50 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                        >
                          <div class="flex items-start space-x-3">
                            <div 
                              class="p-2 rounded-lg"
                              :class="getMaterialTypeClasses(material.type).bgClass"
                            >
                              <span 
                                class="material-icons"
                                :class="getMaterialTypeClasses(material.type).textClass"
                              >
                                {{ getMaterialTypeIcon(material.type) }}
                              </span>
                            </div>
                            <div class="flex-1 min-w-0">
                              <h4 class="font-medium text-gray-900">{{ material.title }}</h4>
                              <p class="text-sm text-gray-600 mt-1">{{ material.description }}</p>
                              <div class="flex items-center space-x-4 mt-2">
                                <button 
                                  @click="startLearning(material)"
                                  class="text-sm text-maroon-600 hover:text-maroon-700 font-medium inline-flex items-center"
                                  :disabled="milestone.locked"
                                >
                                  Start Learning
                                  <span class="material-icons text-sm ml-1">arrow_forward</span>
                                </button>
                                <span class="text-sm text-gray-500">{{ material.duration }}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Chat Panel -->
        <div 
          class="w-96 border-l border-gray-200 bg-white flex flex-col"
          :class="{ 'hidden': !showChat }"
        >
          <div class="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900">Learning Assistant</h2>
            <button 
              @click="showChat = false"
              class="p-1 hover:bg-gray-100 rounded-full transition-colors"
            >
              <span class="material-icons text-gray-500">close</span>
            </button>
          </div>
          <ChatBotBox class="flex-1" :context="currentLearningContext" />
        </div>

        <!-- Toggle Chat Button -->
        <button
          v-if="!showChat"
          @click="showChat = true"
          class="fixed bottom-6 right-6 bg-maroon-600 text-white rounded-full p-4 shadow-lg hover:bg-maroon-700 transition-all z-10"
        >
          <span class="material-icons">chat</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import SideNavBar from '@/layouts/SideNavBar.vue'
import ChatBotBox from '@/components/ChatBotBox.vue'
import { useChatStore } from '@/stores/useChatStore'
import { useToast } from 'vue-toastification'
import { RoadmapService } from '@/services/roadmap.service'

export default {
  name: 'RoadmapView',
  components: {
    SideNavBar,
    ChatBotBox
  },
  props: {
    id: {
      type: [String, Number],
      required: true
    }
  },
  setup() {
    const chatStore = useChatStore()
    const toast = useToast()
    return {
      chatStore,
      toast
    }
  },
  data() {
    return {
      showChat: false,
      currentLearningContext: null,
      roadmap: null,
      loading: true,
      error: null
    }
  },
  async created() {
    try {
      console.log('Loading roadmap for course:', this.id);
      
      // Show loading state
      this.loading = true;
      
      // Initialize with mock data immediately so something is always shown
      this.loadMockRoadmap();
      
      // Try to fetch real data
      try {
        const data = await RoadmapService.getRoadmap(this.id);
        
        if (data && data.roadmap) {
          // Check if the roadmap has valid milestones
          if (data.roadmap.milestones && 
              Array.isArray(data.roadmap.milestones) && 
              data.roadmap.milestones.length > 0) {
            
            console.log('Found valid roadmap data, replacing mock data');
            this.roadmap = data.roadmap;
            
            // Update chat context
            this.currentLearningContext = {
              type: 'roadmap',
              title: this.roadmap.title,
              description: this.roadmap.description,
              courseId: this.id
            };
            
            // Remove error if any
            this.error = null;
          } else {
            console.warn('API returned roadmap with no milestones, keeping mock data');
            this.toast.warning('Roadmap from server has no content. Using sample data instead.');
          }
        } else {
          console.warn('API returned invalid roadmap structure, keeping mock data');
        }
      } catch (err) {
        console.error('Error loading roadmap from API:', err);
        
        if (err.response && err.response.status === 404) {
          this.toast.warning('Roadmap not found for this course. Using sample data instead.');
        } else if (err.response && err.response.status === 401) {
          this.toast.error('Authentication required to access this roadmap.');
        } else {
          this.toast.error('Failed to load roadmap: ' + (err.message || 'Unknown error'));
        }
        
        // We already loaded mock data, so no need to call loadMockRoadmap again
        // Just keep what we have
      }
    } finally {
      this.loading = false;
    }
  },
  methods: {
    loadMockRoadmap() {
      // Generate different mock data based on the course ID
      const courseId = parseInt(this.id);
      
      // Default mock data template that will be customized
      const mockTemplate = {
        id: courseId.toString(),
        title: "Learning Path",
        description: "Personalized roadmap for your learning journey",
        completedSteps: 0,
        totalSteps: 6,
        milestones: []
      };
      
      // Customize based on course ID
      switch (courseId) {
        case 1:
          mockTemplate.title = "Python Programming Path";
          mockTemplate.description = "Master Python programming with hands-on projects and exercises";
          mockTemplate.completedSteps = 3;
          mockTemplate.totalSteps = 8;
          mockTemplate.milestones = [
            {
              id: 1,
              title: "Python Basics",
              description: "Learn Python syntax and basic concepts",
              status: "completed",
              estimatedTime: "2 weeks",
              locked: false,
              materials: [
                {
                  id: 1,
                  type: "video",
                  title: "Introduction to Python",
                  description: "Get started with Python programming",
                  duration: "2 hours",
                  url: `/course/${courseId}/lecture/1`
                },
                {
                  id: 2,
                  type: "exercise",
                  title: "Python Syntax Practice",
                  description: "Practice basic Python syntax",
                  duration: "1 hour",
                  url: `/course/${courseId}/lecture/2`
                }
              ]
            },
            {
              id: 2,
              title: "Data Structures",
              description: "Master Python data structures",
              status: "in_progress",
              estimatedTime: "3 weeks",
              locked: false,
              materials: [
                {
                  id: 3,
                  type: "video",
                  title: "Lists and Dictionaries",
                  description: "Practice with Python collections",
                  duration: "3 hours",
                  url: `/course/${courseId}/lecture/3`
                },
                {
                  id: 4,
                  type: "project",
                  title: "Data Structure Implementation",
                  description: "Build common data structures from scratch",
                  duration: "5 hours",
                  url: `/course/${courseId}/lecture/4`
                }
              ]
            },
            {
              id: 3,
              title: "Functions and Modules",
              description: "Learn how to organize code with functions and modules",
              status: "locked",
              estimatedTime: "2 weeks",
              locked: true,
              materials: [
                {
                  id: 5,
                  type: "video",
                  title: "Python Functions",
                  description: "Learn to write reusable code with functions",
                  duration: "2 hours",
                  url: `/course/${courseId}/lecture/5`
                }
              ]
            }
          ];
          break;
          
        case 2:
          mockTemplate.title = "Web Development Path";
          mockTemplate.description = "Master web development fundamentals and modern frameworks";
          mockTemplate.completedSteps = 2;
          mockTemplate.totalSteps = 6;
          mockTemplate.milestones = [
            {
              id: 1,
              title: "HTML & CSS",
              description: "Learn the basics of web development",
              status: "completed",
              estimatedTime: "2 weeks",
              locked: false,
              materials: [
                {
                  id: 1,
                  type: "video",
                  title: "HTML Fundamentals",
                  description: "Get started with HTML5",
                  duration: "2 hours",
                  url: `/course/${courseId}/lecture/1`
                },
                {
                  id: 2,
                  type: "exercise",
                  title: "CSS Styling",
                  description: "Master the fundamentals of CSS",
                  duration: "2 hours",
                  url: `/course/${courseId}/lecture/2`
                }
              ]
            },
            {
              id: 2,
              title: "JavaScript Basics",
              description: "Learn the fundamentals of JavaScript",
              status: "in_progress",
              estimatedTime: "3 weeks",
              locked: false,
              materials: [
                {
                  id: 3,
                  type: "tutorial",
                  title: "JavaScript Syntax",
                  description: "Core JavaScript concepts",
                  duration: "3 hours",
                  url: `/course/${courseId}/lecture/3`
                }
              ]
            }
          ];
          break;
          
        case 3:
          mockTemplate.title = "Machine Learning Path";
          mockTemplate.description = "Learn machine learning concepts and practical applications";
          mockTemplate.completedSteps = 1;
          mockTemplate.totalSteps = 10;
          mockTemplate.milestones = [
            {
              id: 1,
              title: "ML Foundations",
              description: "Understanding machine learning basics",
              status: "in_progress",
              estimatedTime: "4 weeks",
              locked: false,
              materials: [
                {
                  id: 1,
                  type: "course",
                  title: "Introduction to ML",
                  description: "Basic concepts and terminology",
                  duration: "4 hours",
                  url: `/course/${courseId}/lecture/1`
                },
                {
                  id: 2,
                  type: "project",
                  title: "Simple Regression Model",
                  description: "Build your first ML model",
                  duration: "3 hours",
                  url: `/course/${courseId}/lecture/2`
                }
              ]
            }
          ];
          break;
          
        default:
          // Generic roadmap for any other course
          mockTemplate.title = `Learning Path for Course ${courseId}`;
          mockTemplate.description = "Custom learning journey for this course";
          mockTemplate.completedSteps = 1;
          mockTemplate.totalSteps = 5;
          mockTemplate.milestones = [
            {
              id: 1,
              title: "Getting Started",
              description: "Introduction to the course fundamentals",
              status: "completed",
              estimatedTime: "1 week",
              locked: false,
              materials: [
                {
                  id: 1,
                  type: "video",
                  title: "Course Introduction",
                  description: "Overview of what you'll learn",
                  duration: "1 hour",
                  url: `/course/${courseId}/lecture/1`
                }
              ]
            },
            {
              id: 2,
              title: "Core Concepts",
              description: "Master the fundamental principles",
              status: "in_progress",
              estimatedTime: "2 weeks",
              locked: false,
              materials: [
                {
                  id: 2,
                  type: "tutorial",
                  title: "Key Principles",
                  description: "Learn the essential concepts",
                  duration: "2 hours",
                  url: `/course/${courseId}/lecture/2`
                }
              ]
            },
            {
              id: 3,
              title: "Advanced Topics",
              description: "Deepen your understanding with advanced material",
              status: "locked",
              estimatedTime: "3 weeks",
              locked: true,
              materials: [
                {
                  id: 3,
                  type: "project",
                  title: "Practical Application",
                  description: "Apply what you've learned",
                  duration: "5 hours",
                  url: `/course/${courseId}/lecture/3`
                }
              ]
            }
          ];
      }
      
      this.roadmap = mockTemplate;
      
      // Set context for chat based on mock data
      this.currentLearningContext = {
        type: 'roadmap',
        title: this.roadmap.title,
        description: this.roadmap.description,
        courseId: this.id
      };
      
      if (this.error) {
        this.toast.error('Could not load roadmap from server. Using mock data instead.');
      } else {
        this.toast.info('Using sample roadmap data');
      }
    },
    getMilestoneStatusClasses(status) {
      const classes = {
        completed: {
          bgClass: 'bg-green-100',
          textClass: 'text-green-600',
          badgeClass: 'bg-green-100 text-green-800'
        },
        in_progress: {
          bgClass: 'bg-blue-100',
          textClass: 'text-blue-600',
          badgeClass: 'bg-blue-100 text-blue-800'
        },
        locked: {
          bgClass: 'bg-gray-100',
          textClass: 'text-gray-600',
          badgeClass: 'bg-gray-100 text-gray-800'
        }
      }
      return classes[status] || classes.locked
    },
    getMilestoneStatusIcon(status) {
      const icons = {
        completed: 'check_circle',
        in_progress: 'trending_up',
        locked: 'lock'
      }
      return icons[status] || 'help'
    },
    getMaterialTypeClasses(type) {
      const classes = {
        video: {
          bgClass: 'bg-purple-100',
          textClass: 'text-purple-600'
        },
        exercise: {
          bgClass: 'bg-orange-100',
          textClass: 'text-orange-600'
        },
        course: {
          bgClass: 'bg-blue-100',
          textClass: 'text-blue-600'
        },
        project: {
          bgClass: 'bg-green-100',
          textClass: 'text-green-600'
        },
        tutorial: {
          bgClass: 'bg-yellow-100',
          textClass: 'text-yellow-600'
        }
      }
      return classes[type] || classes.course
    },
    getMaterialTypeIcon(type) {
      const icons = {
        video: 'play_circle',
        exercise: 'assignment',
        course: 'school',
        project: 'engineering',
        tutorial: 'menu_book'
      }
      return icons[type] || 'article'
    },
    startLearning(material) {
      // Set the learning context for the chat
      this.currentLearningContext = {
        type: material.type,
        title: material.title,
        description: material.description,
        url: material.url
      };
      
      // Show the chat panel when starting a new material
      this.showChat = true;
      
      // Extract the lecture ID from the URL if it's in the format "/course/{courseId}/lecture/{lectureId}"
      let lectureId = 1; // Default lecture ID
      
      if (material.url) {
        const match = material.url.match(/\/lecture\/(\d+)/);
        if (match && match[1]) {
          lectureId = parseInt(match[1]);
        }
      }
      
      // Navigate to the course lecture view
      this.$router.push({
        name: 'CourseLectureView',
        params: { 
          courseId: this.id,
          lectureId: lectureId
        }
      });
    },
    async updateMilestoneStatus(milestone, newStatus) {
      try {
        // Don't allow changing locked milestones
        if (milestone.locked) {
          this.toast.warning('This milestone is locked. Complete previous milestones first.');
          return;
        }
        
        this.toast.info('Updating milestone status...');
        
        // Call the service to update progress
        const response = await RoadmapService.updateProgress(
          this.roadmap.id, 
          milestone.id, 
          newStatus
        );
        
        if (response && response.success) {
          // Update the local state
          milestone.status = newStatus;
          
          // Update completion counters
          if (newStatus === 'completed') {
            this.roadmap.completedSteps += 1;
          } else if (milestone.status === 'completed' && newStatus !== 'completed') {
            this.roadmap.completedSteps -= 1;
          }
          
          // Unlock next milestone if this one is completed
          if (newStatus === 'completed') {
            const nextIndex = this.roadmap.milestones.findIndex(m => m.id === milestone.id) + 1;
            if (nextIndex < this.roadmap.milestones.length) {
              this.roadmap.milestones[nextIndex].locked = false;
              this.roadmap.milestones[nextIndex].status = 'in_progress';
            }
          }
          
          this.toast.success('Progress updated successfully');
        } else {
          this.toast.error('Failed to update progress');
        }
      } catch (error) {
        console.error('Error updating milestone status:', error);
        this.toast.error('Failed to update milestone status: ' + error.message);
      }
    }
  }
}
</script>

<style scoped>
/* Custom scrollbar */
.overflow-y-auto::-webkit-scrollbar {
  width: 4px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}
</style> 