<script>
import { ref, onMounted } from 'vue'
import SideNavBar from '@/layouts/SideNavBar.vue'
import AnalyticsViewer from '@/components/faculty/AnalyticsViewer.vue'
import AlertMessage from '@/components/common/AlertMessage.vue'

export default {
  name: 'FacultyDashboard',
  components: {
    SideNavBar,
    AnalyticsViewer,
    AlertMessage,
  },
  setup() {
    const showAlert = ref(false)
    const alertMessage = ref('')
    const alertType = ref('')
    const analyticsFilters = ref({
      course: '',
      year: '',
      term: ''
    })

    const courses = ['Math', 'CT', 'SE', 'ST']
    const years = ['2025', '2024', '2023']
    const terms = ['Term 1', 'Term 2', 'Term 3']

    const triggerAlert = (message, type) => {
      alertMessage.value = message
      alertType.value = type
      showAlert.value = true

      setTimeout(() => {
        showAlert.value = false
      }, 3000)
    }

    const updateFilters = () => {
      if (!analyticsFilters.value.course || !analyticsFilters.value.year || !analyticsFilters.value.term) {
        triggerAlert('Please select all filter values', 'warning')
        return
      }
      
      // Show success message when all filters are selected
      triggerAlert('Analytics data updated successfully', 'success')
    }

    // Set default values for demonstration
    onMounted(() => {
      analyticsFilters.value = {
        course: 'SE',
        year: '2024',
        term: 'Term 1'
      }
      updateFilters()
    })

    return {
      showAlert,
      alertMessage,
      alertType,
      analyticsFilters,
      courses,
      years,
      terms,
      triggerAlert,
      updateFilters
    }
  }
}
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <div>
      <SideNavBar />
    </div>
    
    <div class="flex-1 overflow-y-auto">
      <div class="p-6 space-y-6">
        <!-- Alert Message -->
        <AlertMessage
          v-if="showAlert"
          :message="alertMessage"
          :type="alertType"
          class="fixed top-4 right-4 z-50"
        />

        <!-- Main Content -->
        <div class="grid gap-6">
          <!-- Course Filters -->
          <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
            <div class="flex flex-wrap gap-4 items-center">
              <h3 class="text-lg font-semibold text-gray-800 mr-4">Course Filters</h3>
              
              <select
                v-model="analyticsFilters.course"
                class="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-gray-900"
              >
                <option value="" disabled>Select Course</option>
                <option v-for="course in courses" :key="course" :value="course">
                  {{ course }}
                </option>
              </select>

              <select
                v-model="analyticsFilters.year"
                class="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-gray-900"
              >
                <option value="" disabled>Select Year</option>
                <option v-for="year in years" :key="year" :value="year">
                  {{ year }}
                </option>
              </select>

              <select
                v-model="analyticsFilters.term"
                class="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 text-gray-900"
                @change="updateFilters"
              >
                <option value="" disabled>Select Term</option>
                <option v-for="term in terms" :key="term" :value="term">
                  {{ term }}
                </option>
              </select>

              <button
                @click="updateFilters"
                class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Update Analytics
              </button>
            </div>
          </div>

          <!-- Analytics Viewer -->
          <AnalyticsViewer :filters="analyticsFilters" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
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
</style>
