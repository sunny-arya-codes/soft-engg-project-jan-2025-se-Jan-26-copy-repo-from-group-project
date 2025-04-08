import api from '@/utils/api';

export const RoadmapService = {
  /**
   * Get a learning roadmap for a specific course
   * @param {string} courseId - ID of the course
   * @param {string} difficultyLevel - Optional difficulty level (beginner, intermediate, advanced)
   * @returns {Promise<Object>} - The roadmap data or error
   */
  async getRoadmap(courseId, difficultyLevel = 'intermediate') {
    try {
      console.log(`Fetching roadmap for course ${courseId} with difficulty ${difficultyLevel}`);
      
      // Construct URL with params
      let url = `/roadmap/generate/${courseId}`;
      if (difficultyLevel) {
        url += `?difficulty_level=${difficultyLevel}`;
      }
      
      // Make request - no need to manually add token headers as our API instance handles this
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error fetching roadmap:', error);
      
      // Handle common errors and provide meaningful messages
      if (error.response) {
        if (error.response.status === 401) {
          throw new Error('Authentication required to access roadmap data');
        } else if (error.response.status === 404) {
          throw new Error('Roadmap not found for this course');
        } else {
          const message = error.response.data?.detail || error.response.data?.message;
          throw new Error(message || 'Error fetching roadmap data');
        }
      }
      
      throw error;
    }
  },
  
  /**
   * Update a user's progress in a roadmap
   * @param {string} roadmapId - ID of the roadmap
   * @param {string} milestoneId - ID of the milestone
   * @param {string} status - New status (completed, in_progress, etc.)
   * @returns {Promise<Object>} - Updated progress data
   */
  async updateProgress(roadmapId, milestoneId, status) {
    try {
      // Prepare request body
      const data = {
        roadmapId,
        milestoneId,
        status
      };
      
      // Make request - no need to manually add token headers
      const response = await api.post(`/roadmap/progress`, data);
      return response.data;
    } catch (error) {
      console.error('Error updating roadmap progress:', error);
      
      // Handle common errors
      if (error.response) {
        if (error.response.status === 401) {
          throw new Error('Authentication required to update progress');
        } else {
          const message = error.response.data?.detail || error.response.data?.message;
          throw new Error(message || 'Error updating roadmap progress');
        }
      }
      
      throw error;
    }
  }
}; 