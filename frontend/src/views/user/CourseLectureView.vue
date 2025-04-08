<template>
  <div class="flex h-screen bg-gradient-to-br from-gray-50 to-gray-100">
    <SideNavBar />

    <!-- Main Content Container -->
    <div class="flex-1 overflow-hidden flex flex-col">
      <!-- Loading State -->
      <div v-if="loading" class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <div
            class="w-16 h-16 border-4 border-maroon-600 border-t-transparent rounded-full animate-spin mx-auto"
          ></div>
          <p class="mt-4 text-gray-600">Loading course content...</p>
        </div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <div class="w-16 h-16 mx-auto text-red-500">
            <span class="material-icons text-6xl">error_outline</span>
          </div>
          <p class="mt-4 text-gray-800 font-medium">{{ error }}</p>
          <button
            @click="retryLoading"
            class="mt-4 px-4 py-2 bg-maroon-600 text-white rounded-lg hover:bg-maroon-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>

      <template v-else>
        <!-- Course Header -->
        <CourseTopNav
          :course="currentCourse"
          :current-lecture="selectedLecture"
          :is-bookmarked="isBookmarked"
          :progress="progress"
          @toggle-bookmark="toggleBookmark"
          @toggle-notes="toggleNotes"
          @back-to-courses="navigateBack"
        />

        <!-- Main Course Layout -->
        <div class="flex flex-1 overflow-hidden">
          <!-- Course Navigation Sidebar -->
          <CourseSideNav
            :weeks="weeks"
            :selected-lecture="selectedLecture"
            :completed-lectures="completedLectures"
            :total-lectures="totalLectures"
            :is-collapsed="isSidebarCollapsed"
            @select-lecture="selectLecture"
            @toggle-collapse="toggleSidebar"
            class="flex-shrink-0"
          />

          <!-- Main Content Area -->
          <div
            class="flex-1 overflow-y-auto bg-gradient-to-b from-slate-50 to-white border-l border-slate-200"
            :class="{ 'lg:ml-0': !isSidebarCollapsed }"
          >
            <div class="px-6 py-4 max-w-6xl mx-auto">
              <div v-if="selectedLecture" class="space-y-4">
                <!-- Breadcrumb Navigation -->
                <nav aria-label="Course navigation" class="text-sm mb-3">
                  <ol class="flex items-center space-x-2">
                    <li>
                      <span class="text-slate-500">{{ currentCourse.title }}</span>
                    </li>
                    <li>
                      <span class="text-slate-400 mx-2">›</span>
                      <span class="text-slate-500">Week {{ selectedLecture.week }}</span>
                    </li>
                    <li>
                      <span class="text-slate-400 mx-2">›</span>
                      <span class="text-slate-900">{{ selectedLecture.title }}</span>
                    </li>
                  </ol>
                </nav>

                <!-- Video Player Section -->
                <section aria-label="Lecture video" class="mb-4">
                  <div v-if="videoError" class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                    <div class="flex items-start">
                      <span class="material-symbols-outlined text-red-500 mr-3">error_outline</span>
                      <div>
                        <h3 class="font-medium text-red-800">Video playback error</h3>
                        <p class="text-red-700 mt-1">{{ videoError }}</p>
                        <div class="mt-3 flex space-x-3">
                          <button 
                            @click="tryBackupVideo" 
                            class="px-3 py-1 bg-maroon-100 text-maroon-700 rounded hover:bg-maroon-200 transition-colors"
                          >
                            Try Backup Source
                          </button>
                          <button 
                            @click="reportVideoIssue" 
                            class="px-3 py-1 bg-slate-200 text-slate-700 rounded hover:bg-slate-300 transition-colors"
                          >
                            Report Issue
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <CourseVideoPlayer
                    :video-url="currentVideoUrl"
                    :poster-image="selectedLecture.thumbnailUrl || ''"
                    :current-time="videoProgress"
                    :use-native-controls="true"
                    @time-update="updateVideoProgress"
                    @video-complete="handleVideoComplete"
                    @video-error="handleVideoError"
                  />

                  <!-- Video Controls -->
                  <div class="flex items-center justify-between mt-2">
                    <div class="flex items-center space-x-4">
                      <button
                        @click="togglePlaybackSpeed"
                        class="px-3 py-1 text-sm bg-slate-100 rounded-full hover:bg-slate-200 transition-colors flex items-center space-x-1"
                      >
                        <span class="material-symbols-outlined text-sm">speed</span>
                        <span>{{ playbackSpeed }}x</span>
                      </button>
                      <button
                        @click="toggleCaptions"
                        class="px-3 py-1 text-sm bg-slate-100 rounded-full hover:bg-slate-200 transition-colors flex items-center space-x-1"
                        :class="{ 'bg-maroon-100 text-maroon-600': captionsEnabled }"
                      >
                        <span class="material-symbols-outlined text-sm">closed_caption</span>
                        <span>CC</span>
                      </button>
                      <button
                        @click="toggleTranscription"
                        class="px-3 py-1 text-sm bg-slate-100 rounded-full hover:bg-slate-200 transition-colors flex items-center space-x-1"
                        :class="{ 'bg-maroon-100 text-maroon-600': showTranscription }"
                      >
                        <span class="material-symbols-outlined text-sm">description</span>
                        <span>Transcription</span>
                      </button>
                    </div>
                    <div class="flex items-center space-x-2">
                      <button
                        @click="toggleFullscreen"
                        class="p-2 rounded-full hover:bg-slate-100 transition-colors"
                      >
                        <span class="material-symbols-outlined">fullscreen</span>
                      </button>
                    </div>
                  </div>
                </section>

                <!-- Lecture Content -->
                <div class="grid grid-cols-1 xl:grid-cols-3 gap-8 mb-4">
                  <div class="xl:col-span-2 space-y-8">
                    <!-- Lecture Info -->
                    <div class="bg-white rounded-2xl shadow-lg p-6">
                      <div class="flex items-start justify-between">
                        <div class="space-y-3">
                          <h2 class="text-2xl font-bold text-slate-900">
                            {{ selectedLecture.title }}
                          </h2>
                          <p class="text-slate-600 leading-relaxed">
                            {{ selectedLecture.description }}
                          </p>
                        </div>
                        <div class="relative w-20 h-20">
                          <svg class="progress-ring" width="80" height="80">
                            <circle
                              class="text-slate-200"
                              stroke-width="6"
                              fill="transparent"
                              r="37"
                              cx="40"
                              cy="40"
                            ></circle>
                            <circle
                              class="text-maroon-500"
                              stroke-width="6"
                              stroke-dasharray="NaN, 234"
                              fill="transparent"
                              r="37"
                              cx="40"
                              cy="40"
                              style="filter: drop-shadow(0 0 8px rgba(139, 0, 0, 0.2))"
                            ></circle>
                          </svg>
                          <button
                            class="absolute inset-0 flex items-center justify-center w-full h-full transition-transform duration-300 hover:scale-105"
                          >
                            <span
                              class="material-symbols-outlined text-3xl"
                              :class="isLectureCompleted ? 'text-emerald-500' : 'text-maroon-500'"
                            >
                              {{ isLectureCompleted ? 'check_circle' : 'play_circle' }}
                            </span>
                          </button>
                        </div>
                      </div>
                      <div class="mt-6 flex flex-wrap gap-3">
                        <button
                          class="px-5 py-2.5 bg-maroon-500 text-white rounded-xl hover:bg-maroon-600 transition-all duration-300 flex items-center space-x-2 shadow-md hover:shadow-lg"
                        >
                          <span class="material-symbols-outlined">download</span>
                          <span>Resources</span>
                        </button>
                      </div>
                    </div>

                    <!-- Key Concepts -->
                    <div class="bg-white rounded-2xl shadow-lg p-6">
                      <h3 class="text-xl font-bold text-slate-900 mb-5">
                        Key Concepts
                        <span v-if="loadingConcepts" class="ml-2 inline-block w-4 h-4 border-2 border-maroon-600 border-t-transparent rounded-full animate-spin"></span>
                      </h3>
                      
                      <!-- Fallback Data Indicator -->
                      <div v-if="isShowingFallbackData && keyConcepts.length > 0" class="bg-yellow-50 p-2 rounded-md text-sm text-yellow-700 mb-4 flex items-center">
                        <span class="material-icons text-yellow-500 mr-1 text-sm">info</span>
                        <span>Showing suggested concepts. Loading real data...</span>
                      </div>
                      
                      <div v-if="loadingConcepts" class="flex justify-center py-4">
                        <div class="w-8 h-8 border-4 border-maroon-600 border-t-transparent rounded-full animate-spin"></div>
                      </div>
                      <div v-else-if="conceptsError" class="text-center py-4 bg-red-50 rounded-lg p-4">
                        <span class="material-icons text-red-500 text-2xl mb-2">error_outline</span>
                        <p class="text-red-700 mb-2">{{ conceptsError }}</p>
                        <button @click="fetchKeyConcepts" class="px-4 py-2 bg-maroon-500 text-white rounded-lg hover:bg-maroon-600 transition-colors flex items-center mx-auto">
                          <span class="material-icons text-sm mr-1">refresh</span>
                          Retry
                        </button>
                      </div>
                      <div v-else-if="keyConcepts.length > 0">
                        <!-- Categorized Concepts Display -->
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <!-- Core Concepts -->
                          <div class="md:col-span-2">
                            <h4 class="text-md font-semibold text-maroon-600 mb-3 flex items-center">
                              <span class="material-icons text-sm mr-1 text-maroon-600">stars</span>
                              Core Concepts
                            </h4>
                            <ul class="space-y-3">
                              <li
                                v-for="(concept, index) in keyConcepts.slice(0, 2)"
                                :key="`core-${index}`"
                                class="flex items-start space-x-3 p-3 bg-maroon-50/40 rounded-lg hover:bg-maroon-50 transition-colors cursor-pointer"
                                @click="highlightConcept(concept)"
                              >
                                <span class="material-symbols-outlined text-maroon-600 mt-1">
                                  clinical_notes
                                </span>
                                <span class="text-slate-800 leading-relaxed">{{ concept }}</span>
                              </li>
                            </ul>
                          </div>
                          
                          <!-- Supporting Concepts -->
                          <div>
                            <h4 class="text-md font-semibold text-maroon-600 mb-3 mt-4 flex items-center">
                              <span class="material-icons text-sm mr-1 text-maroon-600">extension</span>
                              Supporting Ideas
                            </h4>
                            <ul class="space-y-2">
                              <li
                                v-for="(concept, index) in keyConcepts.slice(2, 4)"
                                :key="`supporting-${index}`"
                                class="flex items-start space-x-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                                @click="highlightConcept(concept)"
                              >
                                <span class="material-symbols-outlined text-maroon-600 mt-1">
                                  check_circle
                                </span>
                                <span class="text-slate-700 leading-relaxed">{{ concept }}</span>
                              </li>
                            </ul>
                          </div>

                          <!-- Advanced Concepts -->
                          <div>
                            <h4 class="text-md font-semibold text-maroon-600 mb-3 mt-4 flex items-center">
                              <span class="material-icons text-sm mr-1 text-maroon-600">psychology</span>
                              Advanced Topics
                            </h4>
                            <ul class="space-y-2">
                              <li
                                v-for="(concept, index) in keyConcepts.slice(4)"
                                :key="`advanced-${index}`"
                                class="flex items-start space-x-3 p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                                @click="highlightConcept(concept)"
                              >
                                <span class="material-symbols-outlined text-maroon-600 mt-1">
                                  insights
                                </span>
                                <span class="text-slate-700 leading-relaxed">{{ concept }}</span>
                              </li>
                            </ul>
                          </div>
                        </div>
                        
                        <!-- Key Concepts Refresh Button -->
                        <div class="flex justify-between mt-6 items-center">
                          <button 
                            @click="fetchKeyConcepts" 
                            class="px-4 py-2 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors text-sm flex items-center"
                            :disabled="loadingConcepts"
                          >
                            <span class="material-icons text-sm mr-1" :class="{ 'animate-spin': loadingConcepts }">refresh</span>
                            {{ loadingConcepts ? 'Refreshing...' : 'Refresh Concepts' }}
                            </button>
                          <span v-if="lastConceptsUpdateTime" class="text-xs text-slate-400">
                            Updated: {{ formatDateRelative(lastConceptsUpdateTime) }}
                          </span>
                        </div>
                      </div>
                      <div v-else class="text-center py-6">
                        <span class="material-icons text-gray-400 text-4xl mb-2">psychology</span>
                        <p class="text-slate-500 mb-3">No key concepts available for this lecture.</p>
                        <button @click="fetchKeyConcepts" class="px-4 py-2 bg-maroon-500 text-white rounded-lg hover:bg-maroon-600 transition-colors flex items-center mx-auto">
                          <span class="material-icons text-sm mr-1">auto_fix_high</span>
                          Generate Concepts
                            </button>
                          </div>
                    </div>

                    <!-- Learning Resources Section in Sidebar -->
                    <div v-if="selectedTab === 'learning-resources'" class="flex flex-col space-y-4 h-full overflow-auto px-4 py-2">
                      <div v-if="isLoadingResources" class="flex justify-center items-center h-32">
                        <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary"></div>
                      </div>

                      <div v-else>
                        <h3 class="text-lg font-semibold mb-3">Learning Resources</h3>
                        
                        <!-- Fallback Data Indicator -->
                        <div v-if="isShowingFallbackData" class="bg-yellow-50 p-2 rounded-md text-sm text-yellow-700 mb-4 flex items-center">
                          <span class="material-icons text-yellow-500 mr-1 text-sm">info</span>
                          <span>Showing suggested resources. Loading real data...</span>
                        </div>
                        
                        <!-- Resources List -->
                        <div v-for="(resource, idx) in learningResources" :key="idx" class="mb-4 p-3 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow border border-gray-200">
                          <!-- YouTube Video Resource with Thumbnail -->
                          <div v-if="resource.type === 'video' && resource.youtubeId" class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800">Video</span>
                            </div>
                            
                            <!-- YouTube Thumbnail with Play Button -->
                            <div class="relative rounded-md overflow-hidden mb-2 cursor-pointer" @click="loadYoutubeVideo(resource.youtubeId)">
                              <img :src="`https://img.youtube.com/vi/${resource.youtubeId}/mqdefault.jpg`" class="w-full h-auto rounded-md" alt="Video thumbnail">
                              <div class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20 hover:bg-opacity-30 transition-all">
                                <span class="material-icons text-white text-4xl">play_circle</span>
                              </div>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <div class="flex justify-between mt-1">
                              <button @click="loadYoutubeVideo(resource.youtubeId)" class="text-sm text-primary flex items-center hover:text-primary-dark transition-colors">
                                <span class="material-icons mr-1 text-sm">play_arrow</span>
                                Play Video
                              </button>
                              <a :href="`https://www.youtube.com/watch?v=${resource.youtubeId}`" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                                <span class="material-icons mr-1 text-sm">open_in_new</span>
                                YouTube
                              </a>
                            </div>
                          </div>
                          
                          <!-- Regular Video Resource without YouTube ID -->
                          <div v-else-if="resource.type === 'video'" class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800">Video</span>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                              <span class="material-icons mr-1 text-sm">videocam</span>
                              Find Video on YouTube
                            </a>
                          </div>
                          
                          <!-- Article Resource -->
                          <div v-else-if="resource.type === 'article'" class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">Article</span>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                              <span class="material-icons mr-1 text-sm">article</span>
                              Read Article
                            </a>
                          </div>
                          
                          <!-- Paper Resource -->
                          <div v-else-if="resource.type === 'paper'" class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">Paper</span>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                              <span class="material-icons mr-1 text-sm">description</span>
                              View Paper
                            </a>
                          </div>
                          
                          <!-- Book Resource -->
                          <div v-else-if="resource.type === 'book'" class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-amber-100 text-amber-800">Book</span>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <a :href="resource.url" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                              <span class="material-icons mr-1 text-sm">menu_book</span>
                              Find Book
                            </a>
                          </div>
                          
                          <!-- Tool or Other Resource -->
                          <div v-else class="flex flex-col">
                            <div class="flex justify-between items-start mb-2">
                              <h4 class="font-medium text-md text-slate-800">{{ resource.title }}</h4>
                              <span class="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">
                                {{ resource.type ? resource.type.charAt(0).toUpperCase() + resource.type.slice(1) : 'Resource' }}
                              </span>
                            </div>
                            
                            <p class="text-sm text-gray-600 mb-2">{{ resource.description }}</p>
                            
                            <a v-if="resource.url && resource.url !== '#'" :href="resource.url" target="_blank" rel="noopener noreferrer" class="text-sm text-blue-600 hover:text-blue-800 transition-colors flex items-center">
                              <span class="material-icons mr-1 text-sm">link</span>
                              Open Resource
                            </a>
                          </div>
                        </div>
                        
                        <!-- No Resources Message -->
                        <div v-if="learningResources.length === 0" class="text-center py-6">
                          <span class="material-icons text-gray-400 text-4xl mb-2">search_off</span>
                          <p class="text-gray-500">No learning resources available.</p>
                        </div>
                        
                        <!-- Refresh Button -->
                        <div class="flex justify-center mt-4">
                          <button
                            @click="fetchLearningResources" 
                            class="px-4 py-2 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors text-sm flex items-center"
                            :disabled="isFetchingRealResources"
                          >
                            <span class="material-icons text-sm mr-1" :class="{ 'animate-spin': isFetchingRealResources }">refresh</span>
                            {{ isFetchingRealResources ? 'Refreshing...' : 'Refresh Resources' }}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Sidebar Content -->
                  <div class="space-y-8">
                    <!-- Placeholder for future sidebar content -->
                  </div>
                </div>

                <!-- Navigation Buttons -->
                <div class="flex items-center justify-between pt-4 border-t border-slate-200">
                  <button
                    v-if="previousLecture"
                    @click="selectLecture(previousLecture)"
                    class="flex items-center space-x-2 text-slate-600 hover:text-maroon-600 transition-colors"
                  >
                    <span class="material-symbols-outlined">arrow_back</span>
                    <span>Previous Lecture</span>
                  </button>
                  <div class="flex-1"></div>
                  <button
                    v-if="nextLecture"
                    @click="selectLecture(nextLecture)"
                    class="flex items-center space-x-2 text-slate-600 hover:text-maroon-600 transition-colors"
                  >
                    <span>Next Lecture</span>
                    <span class="material-symbols-outlined">arrow_forward</span>
                  </button>
                </div>
              </div>

              <!-- Empty State -->
              <div v-else class="h-full flex items-center justify-center">
                <div class="text-center max-w-md py-12 space-y-6">
                  <div class="inline-flex p-6 bg-maroon-50 rounded-2xl">
                    <span class="material-symbols-outlined text-4xl text-maroon-600">school</span>
                  </div>
                  <h2 class="text-2xl font-bold text-slate-900">Begin Your Learning Journey</h2>
                  <p class="text-slate-600">
                    Select a module from the curriculum to start learning
                  </p>
                  <button
                    @click="selectFirstLecture"
                    class="px-6 py-3 bg-maroon-600 text-white rounded-lg hover:bg-maroon-700 transition-colors"
                  >
                    Start First Lecture
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Notes/Transcription Panel -->
          <div
            v-if="showNotes || showTranscription"
            class="w-96 border-l border-slate-200 bg-white overflow-hidden flex flex-col transition-all duration-300"
          >
            <div
              class="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50"
            >
              <div class="flex items-center space-x-3">
                <!-- Tab navigation -->
                <div class="flex">
                  <button 
                    @click="activeTab = 'notes'; showNotes = true; showTranscription = true;" 
                    class="px-3 py-1 text-sm font-medium mr-2"
                    :class="activeTab === 'notes' ? 'text-maroon-600 border-b-2 border-maroon-600' : 'text-slate-600 hover:text-maroon-500'"
                  >
                    Notes
                  </button>
                  <button 
                    @click="activeTab = 'transcription'; showNotes = true; showTranscription = true;" 
                    class="px-3 py-1 text-sm font-medium"
                    :class="activeTab === 'transcription' ? 'text-maroon-600 border-b-2 border-maroon-600' : 'text-slate-600 hover:text-maroon-500'"
                  >
                    Transcription
                  </button>
                </div>
                <span
                  class="text-xs text-slate-500 bg-slate-200 px-2 py-1 rounded-full"
                  v-if="noteSaveStatus && activeTab === 'notes'"
                >
                  {{ noteSaveStatus }}
                </span>
              </div>
              <button
                @click="closeSidebar"
                class="close-button-material"
              >
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>

            <!-- Notes content -->
            <div v-if="activeTab === 'notes'" class="flex flex-col h-full">
            <!-- Formatting Toolbar -->
            <div class="border-b border-slate-200 p-2 bg-white">
              <div class="flex items-center space-x-1">
                <button
                  v-for="tool in formattingTools"
                  :key="tool.command"
                  @click="formatText(tool.command)"
                  class="p-2 rounded hover:bg-slate-100 transition-colors"
                  :class="{ 'bg-maroon-50 text-maroon-600': tool.isActive }"
                  :title="tool.label"
                >
                  <span class="material-symbols-outlined text-sm">{{ tool.icon }}</span>
                </button>
                <div class="h-4 w-px bg-slate-200 mx-1"></div>
                <button
                  @click="insertTimestamp"
                  class="p-2 rounded hover:bg-slate-100 transition-colors flex items-center space-x-1"
                  title="Insert current video timestamp"
                >
                  <span class="material-symbols-outlined text-sm">timer</span>
                  <span class="text-xs font-medium">{{ formatTime(videoProgress) }}</span>
                </button>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto p-4">
              <textarea
                v-model="currentNotes"
                  placeholder="Take notes for this lecture..."
                  class="w-full h-full resize-none border-0 focus:ring-0 p-0 bg-transparent text-slate-800"
                @input="handleNotesInput"
                @keydown="handleKeyboardShortcuts"
              ></textarea>
              </div>
            </div>

            <!-- Transcription content -->
            <div v-else-if="activeTab === 'transcription'" class="flex-1 overflow-hidden">
              <LectureTranscription 
                :lecture-id="String(selectedLecture?.id || '')" 
                :course-id="courseId || 'default'"
                :video-url="selectedLecture?.videoUrl || ''" 
              />
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SideNavBar from '@/layouts/SideNavBar.vue'
import CourseTopNav from '@/components/course/CourseTopNav.vue'
import CourseSideNav from '@/components/course/CourseSideNav.vue'
import CourseVideoPlayer from '@/components/course/CourseVideoPlayer.vue'
import CourseLectureContent from '@/components/course/CourseLectureContent.vue'
import LectureTranscription from '@/components/course/LectureTranscription.vue'
import { useCourse } from '@/composables/useCourse'
import { useNotification } from '@/composables/useNotification'
import api from '@/utils/api'
import { useToast } from 'vue-toastification'
import { useChatStore } from '@/stores/useChatStore'

export default {
  name: 'CourseLectureView',
  components: {
    SideNavBar,
    CourseTopNav,
    CourseSideNav,
    CourseVideoPlayer,
    CourseLectureContent,
    LectureTranscription,
  },

  setup() {
    const toast = useToast()
    const route = useRoute()
    const router = useRouter()
    const { notify } = useNotification()

    // State
    const loading = ref(true)
    const error = ref(null)
    const isSidebarCollapsed = ref(false)
    const playbackSpeed = ref(1)
    const captionsEnabled = ref(false)
    const videoProgress = ref(0)
    const autoSaveTimeout = ref(null)
    const videoError = ref(null)
    const currentVideoUrl = ref('')
    const showTranscription = ref(false)
    const activeTab = ref('notes')
    
    // Key Concepts and Learning Resources state
    const keyConcepts = ref([])
    const learningResources = ref([])
    const loadingConcepts = ref(false)
    const loadingResources = ref(false)
    const conceptsError = ref(null)
    const resourcesError = ref(null)
    const isShowingFallbackData = ref(false)
    const isFetchingRealResources = ref(false)
    const lastResourceUpdateTime = ref(null)
    const lastConceptsUpdateTime = ref(null)

    // Course Data & Methods
    const courseId = route.params.courseId
    const {
      currentCourse,
      selectedLecture,
      isBookmarked,
      showNotes,
      currentNotes,
      completedLectures,
      totalLectures,
      weeks,
      selectLecture,
      markAsComplete,
      getWeekProgress,
      getFileIcon,
      saveNotes,
      completedLecturesCount,
      fetchNotes,
    } = useCourse(courseId)

    // Computed Properties
    const progress = computed(() => {
      if (!currentCourse.value) return 0
      return Math.round((completedLecturesCount.value / totalLectures.value) * 100)
    })

    // Set up backup video URLs
    const backupVideoUrls = {
      // Public test videos from Google
      '101': ['https://storage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 
              'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4'],
      '102': ['https://storage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4',
              'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4'],
      '103': ['https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
              'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'],
      // Add YouTube videos as backups
      'youtube': ['https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                 'https://www.youtube.com/embed/dQw4w9WgXcQ'],
      'default': ['https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4',
                 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4'],
    }

    // Track which backup URL we're currently using
    const currentBackupIndex = ref(0)

    // Handle video errors
    const handleVideoError = (error) => {
      console.error('Video error detected:', error)
      videoError.value = `Unable to load video: ${error}`
      
      // Log additional information for debugging
      if (selectedLecture.value) {
        console.error('Failed lecture:', selectedLecture.value.title)
        console.error('Failed video URL:', currentVideoUrl.value)
      }
      
      // If this wasn't a YouTube URL already, suggest trying YouTube
      if (!currentVideoUrl.value.includes('youtube.com') && !currentVideoUrl.value.includes('youtu.be')) {
        notify.info('Trying alternative video source...')
        tryYoutubeVideo()
      }
    }
    
    // Switch to YouTube video as a fallback
    const tryYoutubeVideo = () => {
      const youtubeBackups = backupVideoUrls['youtube'] || [];
      if (youtubeBackups.length > 0) {
        currentVideoUrl.value = youtubeBackups[0];
        console.log('Trying YouTube backup video:', currentVideoUrl.value);
        videoError.value = null;
        notify.info('Switched to YouTube video source');
      }
    }

    // Try loading from backup source
    const tryBackupVideo = () => {
      if (!selectedLecture.value) return
      
      const lectureId = selectedLecture.value.id.toString()
      const sources = backupVideoUrls[lectureId] || backupVideoUrls.default
      
      // Increment backup index but don't exceed available sources
      currentBackupIndex.value = (currentBackupIndex.value + 1) % sources.length
      
      // Set the new URL
      currentVideoUrl.value = sources[currentBackupIndex.value]
      console.log('Trying backup video source:', currentVideoUrl.value)
      
      // Clear error to hide error message
      videoError.value = null
      
      // Show notification
      notify.info(`Trying backup video source ${currentBackupIndex.value + 1}/${sources.length}`)
    }

    // Report video issue
    const reportVideoIssue = () => {
      const issue = {
        lectureId: selectedLecture.value?.id,
        lectureTitle: selectedLecture.value?.title,
        videoUrl: currentVideoUrl.value,
        error: videoError.value,
        timestamp: new Date().toISOString()
      }
      
      console.log('Reporting video issue:', issue)
      
      // Here you would normally send this to your backend
      // For now, we'll just show a confirmation
      notify.success('Issue reported. Our team will investigate.')
    }

    // Update video URL when selected lecture changes
    watch(selectedLecture, (newLecture) => {
      if (newLecture) {
        // Reset backup index when lecture changes
        currentBackupIndex.value = 0
        videoError.value = null
        
        // Set initial video URL
        currentVideoUrl.value = newLecture.videoUrl || ''
        console.log('Setting video URL:', currentVideoUrl.value)
      }
    }, { immediate: true })

    const previousLecture = computed(() => {
      if (!selectedLecture.value || !weeks.value) return null

      let prevLecture = null
      let foundCurrent = false

      // Iterate through weeks in reverse to find previous lecture
      for (let weekIndex = weeks.value.length - 1; weekIndex >= 0; weekIndex--) {
        const week = weeks.value[weekIndex]
        for (let lectureIndex = week.lectures.length - 1; lectureIndex >= 0; lectureIndex--) {
          const lecture = week.lectures[lectureIndex]
          if (foundCurrent) {
            prevLecture = lecture
            break
          }
          if (lecture.id === selectedLecture.value.id) {
            foundCurrent = true
          }
        }
        if (prevLecture) break
      }

      return prevLecture
    })

    const nextLecture = computed(() => {
      if (!selectedLecture.value || !weeks.value) return null

      let nextLecture = null
      let foundCurrent = false

      // Iterate through weeks to find next lecture
      for (const week of weeks.value) {
        for (const lecture of week.lectures) {
          if (foundCurrent) {
            nextLecture = lecture
            break
          }
          if (lecture.id === selectedLecture.value.id) {
            foundCurrent = true
          }
        }
        if (nextLecture) break
      }

      return nextLecture
    })

    const isLectureCompleted = computed(() => {
      return completedLectures.value.includes(selectedLecture.value?.id)
    })

    // Notes State
    const noteSaveStatus = ref('')
    const noteSaveTimeout = ref(null)
    const formattingTools = ref([
      { icon: 'format_bold', command: 'bold', label: 'Bold (Ctrl+B)', isActive: false },
      { icon: 'format_italic', command: 'italic', label: 'Italic (Ctrl+I)', isActive: false },
      { icon: 'format_list_bulleted', command: 'bullet', label: 'Bullet List', isActive: false },
      { icon: 'format_list_numbered', command: 'number', label: 'Numbered List', isActive: false },
      { icon: 'code', command: 'code', label: 'Code Block', isActive: false },
    ])

    // Methods

    const selectFirstLecture = () => {
      if (weeks.value && weeks.value.length > 0) {
        selectLecture(weeks.value[0].lectures[0])
      }
    }

    const loadCourseData = async () => {
      try {
        loading.value = true
        // API call to load course data
        const token = localStorage.getItem('token') // Retrieve token from localStorage
        if (!token) throw new Error('No authentication token found')
        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
        const response = await api.get(`/user/course/content?course_id=${courseId}`, headers)
        currentCourse.value = response.data
        loading.value = false
        toast.success('Course Content Loaded Successfully')
      } catch (err) {
        const message = err.response?.data?.message || 'Failed to load course content'
        toast.error(message)
        error.value = 'Failed to load course content. Please try again.'
        notify.error('Failed to load course content')
        loading.value = false
      } finally {
        loading.value = false
      }
    }

    const retryLoading = () => {
      error.value = null
      loadCourseData()
    }

    const toggleSidebar = () => {
      isSidebarCollapsed.value = !isSidebarCollapsed.value
    }

    const togglePlaybackSpeed = () => {
      const speeds = [0.5, 1, 1.25, 1.5, 2]
      const currentIndex = speeds.indexOf(playbackSpeed.value)
      playbackSpeed.value = speeds[(currentIndex + 1) % speeds.length]
    }

    const toggleCaptions = () => {
      captionsEnabled.value = !captionsEnabled.value
    }

    const toggleTranscription = () => {
      showTranscription.value = !showTranscription.value
    }

    const updateVideoProgress = (time) => {
      videoProgress.value = time
      // Save progress to backend
    }

    const handleVideoComplete = () => {
      if (!isLectureCompleted.value) {
        markAsComplete(selectedLecture.value.id)
      }
    }

    const autoSaveNotes = () => {
      if (autoSaveTimeout.value) {
        clearTimeout(autoSaveTimeout.value)
      }
      autoSaveTimeout.value = setTimeout(() => {
        saveNotes(selectedLecture.value.id, currentNotes.value)
      }, 1000)
    }

    const handleResourceDownload = async (resource) => {
      try {
        // API call to download resource
        notify.success('Download started')
      } catch (err) {
        notify.error('Failed to download resource')
      }
    }

    const navigateBack = () => {
      router.push('/user/courses')
    }

    const getResourceIcon = (type) => {
      const icons = {
        pdf: {
          icon: 'description',
          color: 'text-maroon-500',
        },
        doc: {
          icon: 'article',
          color: 'text-maroon-400',
        },
        ppt: {
          icon: 'slideshow',
          color: 'text-yellow-500',
        },
        code: {
          icon: 'code',
          color: 'text-yellow-600',
        },
        zip: {
          icon: 'folder_zip',
          color: 'text-yellow-400',
        },
        video: {
          icon: 'play_circle',
          color: 'text-maroon-600',
        },
      }
      return icons[type] || { icon: 'insert_drive_file', color: 'text-slate-500' }
    }

    // Notes Methods
    const handleNotesInput = () => {
      if (noteSaveTimeout.value) {
        clearTimeout(noteSaveTimeout.value)
      }

      noteSaveStatus.value = 'Saving...'

      noteSaveTimeout.value = setTimeout(async () => {
        try {
          if (!selectedLecture.value?.id) {
            throw new Error('No lecture selected')
          }
          await saveNotes(selectedLecture.value.id, currentNotes.value)
          noteSaveStatus.value = 'Saved'
          setTimeout(() => {
            noteSaveStatus.value = ''
          }, 2000)
        } catch (err) {
          console.error('Failed to save notes:', err)
          noteSaveStatus.value = 'Failed to save'
          notify.error('Failed to save notes. Please try again.')
        }
      }, 1000)
    }

    const formatText = (command) => {
      const textarea = document.querySelector('textarea')
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const selectedText = currentNotes.value.substring(start, end)

      let formattedText = ''
      switch (command) {
        case 'bold':
          formattedText = `**${selectedText}**`
          break
        case 'italic':
          formattedText = `_${selectedText}_`
          break
        case 'bullet':
          formattedText = `• ${selectedText}`
          break
        case 'number':
          formattedText = `1. ${selectedText}`
          break
        case 'code':
          formattedText = `\`${selectedText}\``
          break
      }

      currentNotes.value =
        currentNotes.value.substring(0, start) + formattedText + currentNotes.value.substring(end)

      // Update cursor position
      textarea.focus()
      textarea.selectionStart = start + formattedText.length
      textarea.selectionEnd = start + formattedText.length
    }

    const insertTimestamp = () => {
      const timestamp = formatTime(videoProgress.value)
      const textarea = document.querySelector('textarea')
      const cursorPos = textarea.selectionStart

      currentNotes.value =
        currentNotes.value.substring(0, cursorPos) +
        `[${timestamp}] ` +
        currentNotes.value.substring(cursorPos)

      textarea.focus()
      textarea.selectionStart = cursorPos + timestamp.length + 3
      textarea.selectionEnd = cursorPos + timestamp.length + 3
    }

    const handleKeyboardShortcuts = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault()
        formatText('bold')
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
        e.preventDefault()
        formatText('italic')
      }
    }

    const downloadNotes = () => {
      try {
        const blob = new Blob([currentNotes.value], { type: 'text/plain' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${selectedLecture.value?.title || 'lecture'}_notes.txt`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        notify.success('Notes downloaded successfully')
      } catch (err) {
        notify.error('Failed to download notes')
      }
    }

    const clearNotes = () => {
      if (confirm('Are you sure you want to clear all notes? This cannot be undone.')) {
        currentNotes.value = ''
        handleNotesInput()
        notify.success('Notes cleared')
      }
    }

    const getWordCount = computed(() => {
      return currentNotes.value.trim().split(/\s+/).filter(Boolean).length
    })

    // Format time function to convert seconds to MM:SS format
    const formatTime = (seconds) => {
      if (!seconds) return '0:00'
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    // Course Navigation Methods
    const toggleBookmark = async () => {
      try {
        isBookmarked.value = !isBookmarked.value
        // API call to update bookmark status
        await updateBookmarkStatus(selectedLecture.value?.id, isBookmarked.value)
        notify.success(isBookmarked.value ? 'Lecture bookmarked' : 'Bookmark removed')
      } catch (err) {
        isBookmarked.value = !isBookmarked.value // Revert on error
        notify.error('Failed to update bookmark')
      }
    }

    const toggleNotes = () => {
      showNotes.value = !showNotes.value
      showTranscription.value = showNotes.value
      
      if (showNotes.value) {
        // Load notes when panel is opened
        loadNotes(selectedLecture.value?.id)
        // Set the activeTab to 'notes' by default when opening
        activeTab.value = 'notes'
      }
    }

    const closeSidebar = () => {
      showNotes.value = false
      showTranscription.value = false
    }

    // Helper Methods
    const loadNotes = async (lectureId) => {
      if (!lectureId) return

      try {
        noteSaveStatus.value = 'Loading...'
        const notes = await fetchNotes(lectureId)
        currentNotes.value = notes || ''
        noteSaveStatus.value = ''
      } catch (err) {
        noteSaveStatus.value = 'Failed to load'
        notify.error('Failed to load notes. Please try again.')
        console.error('Error loading notes:', err)
      }
    }

    const updateBookmarkStatus = async (lectureId, status) => {
      if (!lectureId) return

      // Implement API call to update bookmark status
      // This is a placeholder for the actual API implementation
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve()
        }, 500)
      })
    }

    // Watch for lecture changes to load notes
    watch(
      () => selectedLecture.value?.id,
      (newId) => {
        if (newId && showNotes.value) {
          loadNotes(newId)
        }
      },
    )

    // Add a new watch for lecture changes to trigger key concepts generation
    watch(
      () => selectedLecture.value?.id,
      (newId) => {
        if (newId) {
          // Show notification that concepts are being generated
          toast.info('Generating key concepts for this lecture...', {
            position: 'bottom-right',
            timeout: 3000
          })
          
          // Set loading state to true before fetch
          loadingConcepts.value = true
          isShowingFallbackData.value = true
          
          // Fetch key concepts
          fetchKeyConcepts()
          
          // Ensure chat is available
          const chatStore = useChatStore()
          if (!chatStore.isOpen && !chatStore.initialized) {
            chatStore.initialize()
          }
        }
      },
      { immediate: true }
    )

    // Fetch Key Concepts
    const fetchKeyConcepts = async () => {
      if (!selectedLecture.value) return;
      
      loadingConcepts.value = true;
      conceptsError.value = null;
      
      // Immediately show mock/fallback data
      const fallbackConcepts = [
        "Understanding core principles of the topic",
        "Key theories and frameworks discussed",
        "Application of concepts in real-world settings",
        "Critical analysis and evaluation methods",
        "Integration with existing knowledge",
        "Future developments and research directions"
      ];
      
      // Check localStorage first
      const storedConcepts = localStorage.getItem(`keyConcepts_${selectedLecture.value.id}`);
      if (storedConcepts) {
        try {
          keyConcepts.value = JSON.parse(storedConcepts);
          loadingConcepts.value = false;
        } catch (e) {
          console.error('Error parsing stored concepts:', e);
          keyConcepts.value = fallbackConcepts;
          loadingConcepts.value = false;
        }
      } else {
        // Show fallback immediately
        keyConcepts.value = fallbackConcepts;
        loadingConcepts.value = false;
      }
      
      // Then fetch real data in background without causing frontend errors
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          console.warn('No authentication token found');
          return; // Exit early but don't throw - we already have fallback data showing
        }
        
        const headers = {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        };
        
        // Try to fetch data without breaking the UI
        let url = `${import.meta.env.VITE_API_URL || ''}/api/v1/courses/${currentCourse.value.id}/lectures/${selectedLecture.value.id}/key-concepts`;
        
        // Safely add video_url as query parameter if available
        try {
          if (selectedLecture.value.videoUrl) {
            const urlObj = new URL(url, window.location.origin);
            urlObj.searchParams.append('video_url', selectedLecture.value.videoUrl);
            url = urlObj.toString();
          }
        } catch (urlError) {
          console.warn('Error constructing URL with video_url param:', urlError);
          // Continue with original URL if there's an error
        }
        
        console.log('Attempting to fetch key concepts from:', url);
        
        // Use fetch with timeout instead of axios to prevent request aborts
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // 8-second timeout
        
        try {
          const response = await fetch(url, {
            method: 'GET',
            headers: {
              Authorization: headers.headers.Authorization,
              'Content-Type': 'application/json'
            },
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          if (response.ok) {
            const data = await response.json();
            if (data?.concepts) {
              keyConcepts.value = data.concepts;
              localStorage.setItem(`keyConcepts_${selectedLecture.value.id}`, JSON.stringify(keyConcepts.value));
              lastConceptsUpdateTime.value = new Date().toISOString(); // Add this line
              isShowingFallbackData.value = false; // Add this line
            }
          } else if (response.status === 404 || response.status === 500) {
            console.log(`GET request failed with ${response.status}, trying POST`);
            
            // Try POST request if GET fails (404 or 500)
            try {
              const postResponse = await fetch(
                `${import.meta.env.VITE_API_URL || ''}/api/v1/courses/${currentCourse.value.id}/lectures/${selectedLecture.value.id}/key-concepts`, 
                {
                  method: 'POST',
                  headers: {
                    Authorization: headers.headers.Authorization,
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({ video_url: selectedLecture.value.videoUrl }),
                }
              );
              
              if (postResponse.ok) {
                const data = await postResponse.json();
                if (data?.concepts) {
                  keyConcepts.value = data.concepts;
                  localStorage.setItem(`keyConcepts_${selectedLecture.value.id}`, JSON.stringify(keyConcepts.value));
                  lastConceptsUpdateTime.value = new Date().toISOString(); // Add this line
                  isShowingFallbackData.value = false; // Add this line
                }
              } else {
                console.warn('POST request also failed:', postResponse.status);
                // Continue showing fallback - no need to throw error
              }
            } catch (postError) {
              console.warn('Error during POST request:', postError);
              // Continue showing fallback - no need to throw error
            }
          }
        } catch (fetchError) {
          console.warn('Fetch error:', fetchError);
          // If fetch was aborted due to timeout, show a toast
          if (fetchError.name === 'AbortError') {
            toast.warning('Request for key concepts timed out. Using fallback data.');
          }
        }
      } catch (error) {
        console.warn('Error in fetchKeyConcepts:', error);
        // We're already showing fallback data, so just log the error
      }
    };
    
    // Fetch Learning Resources using Gemini and YouTube API
    const fetchLearningResources = async () => {
      if (!selectedLecture.value) return;
      
      loadingResources.value = true;
      resourcesError.value = null;
      isShowingFallbackData.value = true;
      
      // Immediately show mock/fallback data
      const fallbackResources = [
        {
          title: "Introduction to the Topic",
          description: "Overview of key learning points from this lecture topic.",
          type: "video",
          url: "#"
        },
        {
          title: "Related Academic Paper",
          description: "Academic research that supports or extends the lecture content.",
          type: "paper",
          url: "#"
        },
        {
          title: "Additional Reading",
          description: "Supplementary material that provides more context about this subject.",
          type: "article",
          url: "#"
        },
        {
          title: "Hands-On Practice Tool",
          description: "Interactive tool to practice concepts from this lecture.",
          type: "tool",
          url: "#"
        }
      ];
      
      // Initialize with fallback data
      learningResources.value = [...fallbackResources];
      
      // Check localStorage first
      const storageKey = `learning-resources-${courseId}-${selectedLecture.value.id}`;
      const storedResources = localStorage.getItem(storageKey);
      if (storedResources) {
        try {
          const parsedResources = JSON.parse(storedResources);
          learningResources.value = parsedResources;
          isShowingFallbackData.value = false;
          loadingResources.value = false;
          console.log("Using cached learning resources from localStorage");
        } catch (error) {
          console.error("Error parsing stored learning resources:", error);
        }
      }
      
      // Get token for authorization
      const token = localStorage.getItem('token');
      if (!token) {
        console.error("No authentication token found");
        loadingResources.value = false;
        return;
      }
      
      // Indicate we're fetching real data in the background
      isFetchingRealResources.value = true;
      
      // Prepare URL with query parameters for Gemini integration
      const apiUrl = new URL(`${import.meta.env.VITE_API_URL}/courses/${courseId}/lectures/${selectedLecture.value.id}/learning-resources`);
      
      // Add video_url parameter if available
      if (currentVideoUrl.value) {
        apiUrl.searchParams.append('video_url', currentVideoUrl.value);
      }
      
      // Add parameters for Gemini and YouTube integration
      apiUrl.searchParams.append('use_gemini', 'true');
      apiUrl.searchParams.append('include_youtube', 'true');
      
      // Topic from lecture title for better search context
      const searchTopic = selectedLecture.value.title || '';
      if (searchTopic) {
        apiUrl.searchParams.append('topic', encodeURIComponent(searchTopic));
      }
      
      // Function to retry with exponential backoff
      const fetchWithRetry = async (retries = 3, delay = 1000) => {
        try {
          const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          if (response.status === 404) {
            console.log("Resources not found, generating new ones...");
            
            // Send POST request to generate resources
            const postResponse = await fetch(apiUrl, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                video_url: currentVideoUrl.value,
                use_gemini: true,
                include_youtube: true,
                topic: searchTopic
              })
            });
            
            if (!postResponse.ok) {
              throw new Error(`Failed to generate resources: ${postResponse.status}`);
            }
            
            return await postResponse.json();
          }
          
          if (!response.ok) {
            throw new Error(`Failed to fetch resources: ${response.status}`);
          }
          
          return await response.json();
          
        } catch (error) {
          if (retries <= 0) {
            // If all retries failed, try direct YouTube search as fallback
            console.log("All API requests failed. Falling back to direct YouTube search.");
            return fetchYouTubeVideos(searchTopic);
          }
          
          console.log(`Retry attempt left: ${retries}. Retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          return fetchWithRetry(retries - 1, delay * 2);
        }
      };
      
      try {
        const data = await fetchWithRetry();
        if (data) {
          // Update resources with real data
          const resources = Array.isArray(data.resources) ? data.resources : [];
          
          // Process resources to ensure YouTube IDs are extracted
          const processedResources = resources.map(resource => {
            if (resource.type === 'video' && resource.url) {
              // Extract YouTube ID from URL if present
              const youtubeId = extractYoutubeId(resource.url);
              if (youtubeId) {
                return {
                  ...resource,
                  youtubeId
                };
              }
            }
            return resource;
          });
          
          learningResources.value = processedResources;
          isShowingFallbackData.value = false;
          
          // Cache in localStorage for future use
          localStorage.setItem(storageKey, JSON.stringify(processedResources));
        }
      } catch (error) {
        console.error("Error fetching learning resources:", error);
        // We keep the fallback data visible in case of error
      } finally {
        loadingResources.value = false;
        isFetchingRealResources.value = false;
      }
    };
    
    // Extract YouTube video ID from a URL
    const extractYoutubeId = (url) => {
      if (!url) return null;
      
      // Handle various YouTube URL formats
      const regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
      const match = url.match(regExp);
      return (match && match[7].length === 11) ? match[7] : null;
    };
    
    // Fetch YouTube videos directly as a fallback
    const fetchYouTubeVideos = async (topic) => {
      console.log("Simulating YouTube video search for topic:", topic);
      
      // This is a simulated response - in a real implementation, 
      // you would call the YouTube API or use a backend service
      const mockYouTubeResults = {
        resources: [
          {
            title: `${topic} - Comprehensive Tutorial`,
            description: "In-depth video explanation with practical examples",
            type: "video",
            url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            youtubeId: "dQw4w9WgXcQ"
          },
          {
            title: `${topic} for Beginners`,
            description: "Simplified explanation perfect for newcomers to the subject",
            type: "video",
            url: "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
            youtubeId: "kJQP7kiw5Fk"
          },
          {
            title: `Advanced ${topic} Techniques`,
            description: "Next-level concepts and applications for experienced learners",
            type: "video",
            url: "https://www.youtube.com/watch?v=JGwWNGJdvx8",
            youtubeId: "JGwWNGJdvx8"
          }
        ]
      };
      
      return mockYouTubeResults;
    };
    
    // Load YouTube video into the player
    const loadYoutubeVideo = (videoId) => {
      if (!videoId) return;
      
      // Update video source with YouTube embed URL
      currentVideoUrl.value = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
      videoError.value = null;
      
      // Update active panel to show video
      showTranscription.value = false;
      
      // Log video loading for analytics
      console.log("Loading YouTube video:", videoId);
      
      // Save to recent videos in localStorage
      saveRecentVideo({
        id: videoId,
        title: "YouTube Video",
        source: "youtube",
        url: `https://www.youtube.com/watch?v=${videoId}`,
        timestamp: new Date().toISOString()
      });
    };
    
    // Save recently watched video to localStorage
    const saveRecentVideo = (videoData) => {
      try {
        const recentVideos = JSON.parse(localStorage.getItem('recent-videos') || '[]');
        
        // Check if this video is already in the list
        const existingIndex = recentVideos.findIndex(v => v.id === videoData.id);
        if (existingIndex >= 0) {
          // Remove the existing entry
          recentVideos.splice(existingIndex, 1);
        }
        
        // Add the new entry at the beginning
        recentVideos.unshift(videoData);
        
        // Keep only the most recent 10 videos
        const trimmedVideos = recentVideos.slice(0, 10);
        
        localStorage.setItem('recent-videos', JSON.stringify(trimmedVideos));
      } catch (error) {
        console.error("Error saving recent video:", error);
      }
    };

    // Lifecycle Hooks
    onMounted(() => {
      loadCourseData()
      // Restore video progress from saved state
    })

    onBeforeUnmount(() => {
      if (autoSaveTimeout.value) {
        clearTimeout(autoSaveTimeout.value)
      }
      // Save final state
    })

    // Watch for route changes to update content
    watch(
      () => route.params.courseId,
      (newId) => {
        if (newId && newId !== courseId) {
          loadCourseData()
        }
      },
    )

    // Add formatDateRelative function
    const formatDateRelative = (timestamp) => {
      if (!timestamp) return '';
      
      const now = new Date();
      const date = new Date(timestamp);
      const diffInSeconds = Math.floor((now - date) / 1000);
      
      if (diffInSeconds < 60) {
        return 'just now';
      } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'} ago`;
      } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
      } else {
        return date.toLocaleDateString();
      }
    };

    // Highlight selected concept
    const highlightConcept = (concept) => {
      if (!concept) return;
      
      // Show a toast with the concept
      toast.info(`Focusing on: ${concept}`, {
        timeout: 3000,
        position: "bottom-center"
      });
      
      // In a real implementation, you could:
      // 1. Scroll to relevant part of the video
      // 2. Add the concept to user's study notes
      // 3. Find related resources
      // 4. Show more detail about the concept
      
      // For now, we'll just log it
      console.log("User selected concept:", concept);
    };

    return {
      // State
      loading,
      error,
      isSidebarCollapsed,
      playbackSpeed,
      captionsEnabled,
      videoProgress,
      videoError,
      currentVideoUrl,
      showTranscription,
      activeTab,
      
      // Key Concepts and Learning Resources
      keyConcepts,
      learningResources,
      loadingConcepts,
      loadingResources,
      conceptsError,
      resourcesError,
      isShowingFallbackData,
      lastConceptsUpdateTime,
      fetchKeyConcepts,
      fetchLearningResources,
      highlightConcept,

      // Course Data
      currentCourse,
      selectedLecture,
      isBookmarked,
      showNotes,
      currentNotes,
      completedLectures,
      totalLectures,
      weeks,
      progress,
      previousLecture,
      nextLecture,
      isLectureCompleted,

      // Methods
      selectLecture,
      toggleBookmark,
      toggleNotes,
      toggleSidebar,
      togglePlaybackSpeed,
      toggleCaptions,
      toggleTranscription,
      updateVideoProgress,
      handleVideoComplete,
      handleVideoError,
      tryBackupVideo,
      tryYoutubeVideo,
      reportVideoIssue,
      autoSaveNotes,
      handleResourceDownload,
      retryLoading,
      navigateBack,
      getFileIcon,
      markAsComplete,
      getResourceIcon,
      noteSaveStatus,
      formattingTools,
      handleNotesInput,
      formatText,
      insertTimestamp,
      handleKeyboardShortcuts,
      downloadNotes,
      clearNotes,
      getWordCount,
      formatTime,
      selectFirstLecture,
      closeSidebar,
      formatDateRelative,
      loadYoutubeVideo,
    }
  },
}
</script>

<style>
:root {
  /* Primary Colors - Maroon (Adjusted to be less bright) */
  --maroon-50: #fdf2f2;
  --maroon-100: #f3e2e2;
  --maroon-200: #dbc1c1;
  --maroon-300: #c39e9e;
  --maroon-400: #a67979;
  --maroon-500: #8b4444;
  --maroon-600: #722b2b;
  --maroon-700: #591f1f;
  --maroon-800: #411616;
  --maroon-900: #2c0f0f;

  /* Secondary Colors - Yellow (Muted to match maroon) */
  --yellow-50: #fdfaeb;
  --yellow-100: #fdf2c7;
  --yellow-200: #f8e3a3;
  --yellow-300: #f6d47e;
  --yellow-400: #e9b64d;
  --yellow-500: #d49b35;
  --yellow-600: #b37d24;
  --yellow-700: #8c5e1a;
  --yellow-800: #674415;
  --yellow-900: #4d3110;

  /* Neutral Colors - Slate (Kept as is for contrast) */
  --slate-50: #f8fafc;
  --slate-100: #f1f5f9;
  --slate-200: #e2e8f0;
  --slate-300: #cbd5e1;
  --slate-400: #94a3b8;
  --slate-500: #64748b;
  --slate-600: #475569;
  --slate-700: #334155;
  --slate-800: #1e293b;
  --slate-900: #0f172a;
}

/* Progress Ring Styles */
.progress-ring circle {
  transition: stroke-dasharray 0.5s ease-out;
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
}

.progress-ring circle.text-slate-200 {
  stroke: var(--slate-200);
}

.progress-ring circle.text-maroon-500 {
  stroke: var(--maroon-500);
  filter: drop-shadow(0 0 4px rgba(114, 43, 43, 0.2));
}

/* Button Styles */
.btn-primary {
  @apply bg-maroon-600 text-white hover:bg-maroon-700 active:bg-maroon-800 
         shadow-sm hover:shadow-md transition-all duration-200;
}

.btn-secondary {
  @apply bg-slate-100 text-slate-700 hover:bg-slate-200 active:bg-slate-300
         shadow-sm transition-all duration-200;
}

/* Card Styles */
.card {
  @apply bg-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-200
         border border-slate-200/80;
}

/* Icon Colors */
.icon-primary {
  @apply text-maroon-600;
}

.icon-secondary {
  @apply text-yellow-600;
}

.icon-neutral {
  @apply text-slate-400;
}

/* Hover Effects */
.hover-primary {
  @apply hover:text-maroon-600 hover:bg-maroon-50;
}

.hover-secondary {
  @apply hover:text-yellow-600 hover:bg-yellow-50;
}

/* Focus States */
.focus-primary {
  @apply focus:ring-2 focus:ring-maroon-500 focus:ring-offset-2;
}

/* Button States */
.btn-maroon {
  @apply bg-maroon-600 text-white hover:bg-maroon-700 
         shadow-sm hover:shadow-md transition-all duration-200;
}

.btn-maroon-light {
  @apply bg-maroon-50 text-maroon-600 hover:bg-maroon-100 
         shadow-sm transition-all duration-200;
}

/* Progress Bars */
.progress-bar-bg {
  @apply bg-slate-100;
}

.progress-bar-fill {
  @apply bg-gradient-to-r from-maroon-600 to-maroon-500;
}

/* Status Indicators */
.status-complete {
  @apply text-emerald-600;
}

.status-incomplete {
  @apply text-maroon-500;
}

/* Interactive Elements */
.interactive-element {
  @apply transition-all duration-200 ease-in-out;
}

.interactive-hover {
  @apply transform hover:scale-105 transition-transform duration-200;
}

.interactive-press {
  @apply transform active:scale-95 transition-transform duration-100;
}

/* Card and Button Base Styles */
.card-base {
  @apply bg-white rounded-2xl shadow-sm 
         border border-slate-200 transition-all duration-200;
}

.button-base {
  @apply rounded-lg transition-all duration-200 
         focus:outline-none focus:ring-2 focus:ring-offset-2;
}

/* Custom Backgrounds */
.bg-gradient-maroon {
  @apply bg-gradient-to-r from-maroon-600 to-maroon-500;
}

.bg-gradient-yellow {
  @apply bg-gradient-to-r from-yellow-600 to-yellow-500;
}

/* Custom Shadows */
.shadow-maroon {
  box-shadow: 0 4px 14px -2px rgba(114, 43, 43, 0.12);
}

.shadow-hover {
  @apply transition-shadow duration-200 hover:shadow-lg;
}

/* Status Colors */
.status-success {
  @apply text-emerald-600 bg-emerald-50;
}

.status-pending {
  @apply text-maroon-600 bg-maroon-50;
}

.status-neutral {
  @apply text-slate-600 bg-slate-50;
}

/* Icon Styles */
.icon-container {
  @apply flex items-center justify-center w-10 h-10 rounded-lg 
         transition-all duration-200;
}

.icon-primary {
  @apply text-maroon-600 bg-maroon-50 hover:bg-maroon-100;
}

.icon-secondary {
  @apply text-yellow-600 bg-yellow-50 hover:bg-yellow-100;
}

.icon-neutral {
  @apply text-slate-600 bg-slate-50 hover:bg-slate-100;
}

/* Material Icons Styles */
.material-symbols-outlined {
  font-variation-settings:
    'FILL' 0,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
  color: inherit; /* Ensure icons inherit text color */
  font-family: 'Material Symbols Outlined';
}

.material-symbols-rounded {
  font-variation-settings:
    'FILL' 1,
    'wght' 400,
    'GRAD' 0,
    'opsz' 24;
  color: inherit; /* Ensure icons inherit text color */
  font-family: 'Material Symbols Rounded';
}

/* Dark background fix */
.bg-slate-700 .material-symbols-outlined,
.bg-slate-800 .material-symbols-outlined,
.bg-slate-900 .material-symbols-outlined,
.bg-maroon-600 .material-symbols-outlined,
.bg-maroon-700 .material-symbols-outlined,
.bg-maroon-800 .material-symbols-outlined {
  color: white; /* Override to white on dark backgrounds */
}

/* Explicit colors for specific icons */
.icon-bookmark {
  color: var(--maroon-600) !important;
}

.icon-bookmark-outline {
  color: var(--maroon-500) !important;
}

.icon-notes {
  color: var(--maroon-500) !important;
}

/* Custom Gradients */
.gradient-primary {
  @apply bg-gradient-to-r from-maroon-600 to-maroon-500;
}

.gradient-secondary {
  @apply bg-gradient-to-r from-yellow-600 to-yellow-500;
}

/* Transitions */
.transition-smooth {
  @apply transition-all duration-300 ease-in-out;
}

/* Notes Panel Styles */
.notes-panel-enter-active,
.notes-panel-leave-active {
  transition: transform 0.3s ease-in-out;
}

.notes-panel-enter-from,
.notes-panel-leave-to {
  transform: translateX(100%);
}

textarea {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  line-height: 1.6;
  tab-size: 4;
}

/* Add these to your existing styles */
.formatting-button {
  @apply p-2 rounded hover:bg-slate-100 transition-colors;
}

.formatting-button.active {
  @apply bg-maroon-50 text-maroon-600;
}

.notes-footer-button {
  @apply flex items-center space-x-1 text-sm text-slate-600 hover:text-maroon-600 transition-colors;
}

/* Add these styles for bookmark animation */
.material-symbols-outlined.bookmark {
  transition: transform 0.2s ease-in-out;
}

.material-symbols-outlined.bookmark:hover {
  transform: scale(1.1);
}

.material-symbols-outlined.bookmark.filled {
  animation: bookmark-pulse 0.4s ease-in-out;
}

@keyframes bookmark-pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
  }
}
</style>
