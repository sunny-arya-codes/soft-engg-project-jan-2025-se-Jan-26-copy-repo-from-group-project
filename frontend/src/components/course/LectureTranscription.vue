<template>
  <div class="lecture-transcription-container">
    <!-- Tab Navigation -->
    <div class="tab-navigation">
      <button 
        @click="setActiveTab('transcription')" 
        :class="['tab-button', { active: activeTab === 'transcription' }]"
      >
        <i class="fas fa-file-alt mr-2"></i>
        Transcription
      </button>
      <button 
        @click="setActiveTab('summary')" 
        :class="['tab-button', { active: activeTab === 'summary' }]"
      >
        <i class="fas fa-chart-bar mr-2"></i>
        Summary
      </button>
      <button 
        @click="setActiveTab('notes')" 
        :class="['tab-button', { active: activeTab === 'notes' }]"
      >
        <i class="fas fa-sticky-note mr-2"></i>
        Smart Notes
      </button>
    </div>

    <!-- Content Area -->
    <div class="content-area">
      <!-- Transcription Tab Content -->
      <div v-if="activeTab === 'transcription'" class="tab-content">
        <div v-if="loadingTranscription" class="loading-container">
          <div class="spinner"></div>
          <p>Loading transcription...</p>
        </div>
        
        <div v-else-if="transcriptionError" class="error-container">
          <p class="error-message">{{ transcriptionError }}</p>
          <button @click="fetchTranscription" class="retry-button">
            <i class="fas fa-sync-alt mr-2"></i> Retry
          </button>
        </div>
        
        <div v-else-if="transcription" class="transcription-content">
          <div v-html="renderedTranscription" class="markdown-content"></div>
        </div>
        
        <div v-else class="empty-state">
          <i class="fas fa-file-alt mb-3 text-4xl text-gray-300"></i>
          <p>No transcription available for this lecture.</p>
        </div>
      </div>

      <!-- Summary Tab Content -->
      <div v-if="activeTab === 'summary'" class="tab-content">
        <div v-if="loadingSummary" class="loading-container">
          <div class="spinner"></div>
          <p>Loading summary...</p>
        </div>
        
        <div v-else-if="summaryError" class="error-container">
          <p class="error-message">{{ summaryError }}</p>
          <button @click="fetchSummary" class="retry-button">
            <i class="fas fa-sync-alt mr-2"></i> Retry
          </button>
        </div>
        
        <div v-else-if="summary" class="summary-content">
          <div v-html="renderedSummary" class="markdown-content"></div>
        </div>
        
        <div v-else class="empty-state">
          <i class="fas fa-chart-bar mb-3 text-4xl text-gray-300"></i>
          <p>No summary available for this lecture.</p>
        </div>
      </div>

      <!-- Smart Notes Tab Content -->
      <div v-if="activeTab === 'notes'" class="tab-content">
        <div v-if="loadingNotes" class="loading-container">
          <div class="spinner"></div>
          <p>Loading smart notes...</p>
        </div>
        
        <div v-else-if="notesError" class="error-container">
          <p class="error-message">{{ notesError }}</p>
          <button @click="fetchNotes" class="retry-button">
            <i class="fas fa-sync-alt mr-2"></i> Retry
          </button>
        </div>
        
        <div v-else-if="notes" class="notes-content">
          <div v-html="renderedSmartNote" class="markdown-content"></div>
        </div>
        
        <div v-else class="empty-state">
          <i class="fas fa-sticky-note mb-3 text-4xl text-gray-300"></i>
          <p>No smart notes available for this lecture.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { marked } from 'marked';
import getAuthToken from '../../utils/auth';
import { API_URL } from '../../config';

export default {
  name: 'LectureTranscription',
  props: {
    courseId: {
      type: String,
      required: true
    },
    lectureId: {
      type: String,
      required: true
    },
    videoUrl: {
      type: String,
      default: null
    }
  },
  setup(props) {
    // State
    const activeTab = ref('transcription');
    const transcription = ref(null);
    const summary = ref(null);
    const notes = ref(null);
    
    // Loading states
    const loadingTranscription = ref(false);
    const loadingSummary = ref(false);
    const loadingNotes = ref(false);
    
    // Error states
    const transcriptionError = ref(null);
    const summaryError = ref(null);
    const notesError = ref(null);

    // Computed properties for rendering markdown
    const renderedTranscription = computed(() => {
      if (!transcription.value) return '';
      
      // Split the transcription into paragraphs and make each a paragraph
      return transcription.value
        .split('\n\n')
        .map(paragraph => `<p>${paragraph}</p>`)
        .join('');
    });

    const renderedSummary = computed(() => {
      if (!summary.value) return '';
      return marked(summary.value);
    });

    const renderedSmartNote = computed(() => {
      if (!notes.value) return '';
      return marked(notes.value);
    });

    // Tab navigation
    const setActiveTab = (tab) => {
      activeTab.value = tab;
      
      // Load data for the tab if it's not already loaded
      if (tab === 'transcription' && !transcription.value && !loadingTranscription.value) {
        fetchTranscription();
      } else if (tab === 'summary' && !summary.value && !loadingSummary.value) {
        fetchSummary();
      } else if (tab === 'notes' && !notes.value && !loadingNotes.value) {
        fetchNotes();
      }
    };

    // API Functions
    const fetchTranscription = async () => {
      loadingTranscription.value = true;
      transcriptionError.value = null;
      
      try {
        // Construct URL with optional video_url parameter
        const url = new URL(`${API_URL}/courses/${props.courseId}/lectures/${props.lectureId}/transcription`);
        
        // Add videoUrl as query parameter if available
        if (props.videoUrl) {
          url.searchParams.append('video_url', props.videoUrl);
        }
        
        console.log('Fetching transcription from:', url.toString());
        
        const token = getAuthToken();
        if (!token) {
          throw new Error('Authentication token is missing. Please log in again.');
        }
        
        console.log('Using auth token (first 15 chars):', token.substring(0, 15) + '...');
        
        const response = await fetch(url.toString(), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token // Token now already includes 'Bearer ' prefix
          }
        });

        console.log('Transcription response status:', response.status);
        
        if (response.status === 404) {
          transcriptionError.value = "Transcription not found. Try generating a new one.";
          return;
        }
        
        if (!response.ok) {
          throw new Error(`Failed to fetch transcription: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Transcription API response:', data);
        
        // Check for different response formats
        if (data.transcription) {
          transcription.value = data.transcription;
        } else if (data.text) {
          transcription.value = data.text;
        } else {
          console.error('Unexpected API response format:', data);
          throw new Error('Unexpected API response format');
        }
        
        // Always fetch summary and smart notes in the background once transcription is loaded
        fetchSummary();
        fetchNotes();
      } catch (error) {
        console.error('Error fetching transcription:', error);
        transcriptionError.value = error.message || 'Failed to load transcription';
      } finally {
        loadingTranscription.value = false;
      }
    };

    const fetchSummary = async () => {
      // Skip the transcription check since we're now always fetching after transcription loads
      // or when the user explicitly requests it
      
      loadingSummary.value = true;
      summaryError.value = null;
      
      try {
        const url = new URL(`${API_URL}/courses/${props.courseId}/lectures/${props.lectureId}/summary`);
        
        // Add videoUrl as query parameter if available
        if (props.videoUrl) {
          url.searchParams.append('video_url', props.videoUrl);
        }
        
        console.log('Fetching summary from:', url.toString());
        
        const token = getAuthToken();
        if (!token) {
          throw new Error('Authentication token is missing. Please log in again.');
        }
        
        console.log('Using auth token (first 15 chars):', token.substring(0, 15) + '...');
        
        let response = await fetch(url.toString(), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token // Token now already includes 'Bearer ' prefix
          }
        });

        console.log('Summary GET response status:', response.status);

        // If summary doesn't exist, generate it
        if (response.status === 404) {
          console.log('Summary not found, generating a new one');
          response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token // Token now already includes 'Bearer ' prefix
            },
            body: JSON.stringify({ video_url: props.videoUrl })
          });
          console.log('Summary POST response status:', response.status);
        }
        
        if (!response.ok) {
          throw new Error(`Failed to fetch summary: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Summary API response:', data);
        
        // Check for different response formats
        if (data.summary) {
          summary.value = data.summary;
        } else if (data.text) {
          summary.value = data.text;
        } else {
          console.error('Unexpected API response format:', data);
          throw new Error('Unexpected API response format');
        }
      } catch (error) {
        console.error('Error fetching summary:', error);
        summaryError.value = error.message || 'Failed to load summary';
      } finally {
        loadingSummary.value = false;
      }
    };

    const fetchNotes = async () => {
      // Skip the transcription check since we're now always fetching after transcription loads
      // or when the user explicitly requests it
      
      loadingNotes.value = true;
      notesError.value = null;
      
      try {
        const url = new URL(`${API_URL}/courses/${props.courseId}/lectures/${props.lectureId}/smart-notes`);
        
        // Add videoUrl as query parameter if available
        if (props.videoUrl) {
          url.searchParams.append('video_url', props.videoUrl);
        }
        
        console.log('Fetching smart notes from:', url.toString());
        
        const token = getAuthToken();
        if (!token) {
          throw new Error('Authentication token is missing. Please log in again.');
        }
        
        console.log('Using auth token (first 15 chars):', token.substring(0, 15) + '...');
        
        let response = await fetch(url.toString(), {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token // Token now already includes 'Bearer ' prefix
          }
        });

        console.log('Smart notes GET response status:', response.status);

        // If notes don't exist, generate them
        if (response.status === 404) {
          console.log('Smart notes not found, generating new ones');
          response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': token // Token now already includes 'Bearer ' prefix
            },
            body: JSON.stringify({ video_url: props.videoUrl })
          });
          console.log('Smart notes POST response status:', response.status);
        }
        
        if (!response.ok) {
          throw new Error(`Failed to fetch smart notes: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Smart notes API response:', data);
        
        // Check for different response formats
        if (data.smart_notes) {
          notes.value = data.smart_notes;
        } else if (data.notes) {
          notes.value = data.notes;
        } else if (data.text) {
          notes.value = data.text;
        } else {
          console.error('Unexpected API response format:', data);
          throw new Error('Unexpected API response format');
        }
      } catch (error) {
        console.error('Error fetching smart notes:', error);
        notesError.value = error.message || 'Failed to load smart notes';
      } finally {
        loadingNotes.value = false;
      }
    };

    // Initial data fetch
    onMounted(() => {
      fetchTranscription();
    });

    // Watch for prop changes to reload data
    watch([() => props.courseId, () => props.lectureId, () => props.videoUrl], 
      () => {
        // Reset data and refetch when props change
        transcription.value = null;
        summary.value = null;
        notes.value = null;
        fetchTranscription();
      }
    );

    return {
      activeTab,
      transcription,
      summary,
      notes,
      loadingTranscription,
      loadingSummary,
      loadingNotes,
      transcriptionError,
      summaryError,
      notesError,
      renderedTranscription,
      renderedSummary,
      renderedSmartNote,
      setActiveTab,
      fetchTranscription,
      fetchSummary,
      fetchNotes
    };
  }
};
</script>

<style scoped>
:root {
  --close-btn-bg: #f1f1f1;
  --close-btn-color: #666666;
  --close-btn-hover-bg: #8b0000;
  --close-btn-hover-color: #ffffff;
}

.lecture-transcription-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  background: #ffffff;
  border: 1px solid #f0f0f0;
}

.tab-navigation {
  display: flex;
  background-color: #ffffff;
  border-bottom: 1px solid #f0f0f0;
  padding: 8px 16px 0;
}

.tab-button {
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-radius: 8px 8px 0 0;
  font-weight: 600;
  color: #5a5a5a;
  cursor: pointer;
  margin-right: 4px;
  transition: all 0.2s ease;
  position: relative;
  top: 1px;
}

.tab-button:hover {
  color: #8b0000; /* Maroon */
  background-color: rgba(139, 0, 0, 0.05);
}

.tab-button.active {
  color: #8b0000; /* Maroon */
  background-color: #ffffff;
  border: 1px solid #f0f0f0;
  border-bottom: 2px solid #8b0000; /* Maroon bottom border for active tab */
}

.content-area {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: #ffffff;
}

.tab-content {
  height: 100%;
  min-height: 400px;
}

.markdown-content {
  line-height: 1.8;
  color: #333333;
  font-size: 16px;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  color: #8b0000; /* Maroon */
  margin-top: 1.5em;
  margin-bottom: 0.75em;
  font-weight: 600;
}

.markdown-content h1 {
  font-size: 1.8em;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 0.3em;
}

.markdown-content h2 {
  font-size: 1.5em;
}

.markdown-content h3 {
  font-size: 1.3em;
}

.markdown-content p {
  margin-bottom: 1.2em;
  color: #383838;
}

.markdown-content ul,
.markdown-content ol {
  margin-left: 2em;
  margin-bottom: 1.2em;
  color: #383838;
}

.markdown-content pre,
.markdown-content code {
  background-color: #f8f8f8;
  border-radius: 4px;
  padding: 0.2em 0.4em;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
  color: #333333;
  border: 1px solid #eaeaea;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(139, 0, 0, 0.1);
  border-radius: 50%;
  border-top-color: #8b0000; /* Maroon */
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
  background-color: #fff8f8;
  border-radius: 8px;
  border: 1px solid #f8e6e6;
}

.error-message {
  color: #d32f2f;
  margin-bottom: 16px;
  font-weight: 500;
}

.retry-button {
  padding: 10px 20px;
  background-color: #8b0000; /* Maroon */
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.2s;
  box-shadow: 0 2px 4px rgba(139, 0, 0, 0.2);
}

.retry-button:hover {
  background-color: #7a0000;
  box-shadow: 0 3px 6px rgba(139, 0, 0, 0.3);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #666666;
  font-style: italic;
  background-color: #fafafa;
  border-radius: 8px;
}

.transcription-content, .summary-content, .notes-content {
  background-color: #ffffff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
</style>

<style>
/* Global styles for markdown content */
.markdown-content h1 {
  @apply text-2xl font-bold mb-4 text-maroon-700;
}
.markdown-content h2 {
  @apply text-xl font-bold mb-3 text-maroon-700;
}
.markdown-content h3 {
  @apply text-lg font-bold mb-2 text-maroon-700;
}
.markdown-content ul {
  @apply list-disc pl-5 mb-4;
}
.markdown-content ol {
  @apply list-decimal pl-5 mb-4;
}
.markdown-content p {
  @apply mb-4;
}
.markdown-content a {
  @apply text-blue-600 hover:underline;
}
.markdown-content blockquote {
  @apply border-l-4 border-gray-300 pl-4 italic text-gray-700;
}
</style> 