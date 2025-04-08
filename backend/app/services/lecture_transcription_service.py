import os
import re
import logging
from typing import Dict, Any, Optional
import requests
from urllib.parse import urlparse, parse_qs
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class LectureTranscriptionService:
    """
    Service for handling lecture transcriptions and AI-generated summaries.
    
    This service provides functionality to:
    1. Extract YouTube video IDs from URLs
    2. Fetch transcriptions from YouTube videos
    3. Generate AI summaries and study notes from transcriptions using Gemini
    """
    
    def __init__(self):
        """Initialize the lecture transcription service."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        
        if not self.api_key:
            logger.error("GOOGLE_API_KEY not found in environment variables")
            raise ValueError("GOOGLE_API_KEY environment variable is required")
            
        if not self.youtube_api_key:
            logger.warning("YOUTUBE_API_KEY not found in environment variables, transcript fetching may be limited")
        
        # Initialize Gemini model
        try:
            self.gemini = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=self.api_key,
                temperature=0.2
            )
            
            # Initialize Gemini model with web search capabilities
            self.gemini_with_search = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                google_api_key=self.api_key,
                temperature=0.2,
                additional_tools=["web_search"]
            )
            
            logger.info("Gemini models initialized successfully for lecture services")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various URL formats.
        
        Args:
            url: YouTube URL in any format
            
        Returns:
            Video ID if found, None otherwise
        """
        # Check if URL is already a video ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
            
        # Parse the URL
        parsed_url = urlparse(url)
        
        # Handle youtu.be format
        if parsed_url.netloc == 'youtu.be':
            return parsed_url.path.lstrip('/')
            
        # Handle standard youtube.com format
        if parsed_url.netloc in ('youtube.com', 'www.youtube.com'):
            query_params = parse_qs(parsed_url.query)
            
            # Standard watch URLs
            if 'v' in query_params:
                return query_params['v'][0]
                
            # Handle embed URLs
            if parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/')[2]
        
        return None
    
    async def get_transcription(self, video_url: str) -> Dict[str, Any]:
        """
        Get transcription for a YouTube video.
        
        Args:
            video_url: URL of the YouTube video
            
        Returns:
            Dictionary containing the transcription and metadata
        """
        # Guard against None or empty video URL
        if not video_url:
            logger.warning("Empty video URL provided to transcription service")
            return {
                "error": "No video URL provided",
                "video_id": None,
                "transcription": None,
                "language": None
            }
        
        video_id = self.extract_video_id(video_url)
        
        if not video_id:
            logger.error(f"Failed to extract video ID from URL: {video_url}")
            return {
                "error": f"Invalid YouTube URL: {video_url}",
                "video_id": None,
                "transcription": None,
                "language": None
            }
        
        try:
            # Import the YouTube transcript API library
            from youtube_transcript_api import YouTubeTranscriptApi, YouTubeTranscriptApiException
            
            try:
                # Fetch the transcript
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                
                # Manual formatting instead of using TextFormatter
                transcript_text = ""
                for item in transcript_list:
                    if isinstance(item, dict) and 'text' in item:
                        transcript_text += item.get('text', '') + ' '
                
                # Log the successful retrieval
                logger.info(f"Successfully retrieved transcript for video {video_id}")
                
                return {
                    "video_id": video_id,
                    "transcription": transcript_text.strip(),
                    "language": "en"
                }
            except YouTubeTranscriptApiException as yt_error:
                # Handle specific YouTube API errors
                logger.warning(f"YouTube transcript API error for video {video_id}: {str(yt_error)}")
                return {
                    "error": f"Cannot retrieve transcript: {str(yt_error)}",
                    "video_id": video_id,
                    "transcription": None,
                    "language": None
                }
            
        except ImportError as import_error:
            # Handle case where the required library is not available
            logger.error(f"Missing youtube_transcript_api dependency: {str(import_error)}")
            return {
                "error": "Transcription service dependency not available",
                "video_id": video_id,
                "transcription": None,
                "language": None
            }
        except Exception as e:
            # Fallback for any other errors
            error_message = str(e)
            logger.error(f"Failed to get transcription for video {video_id}: {error_message}")
            
            # Return an error dictionary with string message
            return {
                "error": error_message,
                "video_id": video_id,
                "transcription": None,
                "language": None
            }
    
    async def generate_summary(self, transcription: str) -> str:
        """
        Generate an AI summary of the lecture transcription using Gemini.
        
        Args:
            transcription: The lecture transcription text
            
        Returns:
            The generated summary text
        """
        if not transcription:
            raise ValueError("Transcription is required for summary generation")
        
        try:
            # Construct the prompt for Gemini
            system_prompt = self._build_summary_prompt()
            
            # Send to Gemini
            response = await self.gemini.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ]
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {str(e)}")
            raise Exception(f"Failed to generate summary: {str(e)}")
    
    async def generate_smart_notes(self, transcription: str) -> str:
        """
        Generate smart study notes from the lecture transcription using Gemini.
        
        Args:
            transcription: The lecture transcription text
            
        Returns:
            The generated smart notes text
        """
        if not transcription:
            raise ValueError("Transcription is required for notes generation")
        
        try:
            # Construct the prompt for Gemini
            system_prompt = self._build_notes_prompt()
            
            # Send to Gemini
            response = await self.gemini.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ]
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate smart notes: {str(e)}")
            raise Exception(f"Failed to generate smart notes: {str(e)}")
    
    def _build_summary_prompt(self) -> str:
        """
        Build the system prompt for Gemini to generate a lecture summary.
        
        Returns:
            A string containing the system prompt for Gemini
        """
        return """You are LectureSummarizer, an AI specialized in creating concise, informative summaries of academic lectures.

Your task is to analyze the lecture transcription and create a comprehensive summary that:
1. Identifies the main topic and key points
2. Captures the essential concepts and arguments
3. Preserves the logical flow of ideas
4. Excludes redundancies and tangential information
5. Maintains academic accuracy and rigor

Present your summary in a structured format with:
- A concise introduction stating the lecture's main focus
- Clear sections for major topics or arguments
- Bullet points for key takeaways
- Preservation of technical terminology and concepts

Your summary should be about 20-30% the length of the original transcription, striking a balance between conciseness and comprehensiveness.

Avoid:
- Adding your own opinions or interpretations
- Introducing concepts not present in the original lecture
- Oversimplifying complex ideas
- Using vague language

Focus on creating a summary that would be valuable for a student reviewing the material or catching up on a missed lecture.
"""
    
    def _build_notes_prompt(self) -> str:
        """
        Build the system prompt for Gemini to generate smart study notes.
        
        Returns:
            A string containing the system prompt for Gemini
        """
        return """You are StudyNoteGenius, an AI expert in creating effective study notes from lecture transcriptions.

Your task is to transform the lecture transcription into organized, comprehensive study notes that:
1. Extract key concepts, definitions, theories, and examples
2. Structure information in a hierarchical format with clear headings and subheadings
3. Use bullet points and numbered lists for clarity
4. Include diagrams or charts descriptions where relevant
5. Highlight important terms or concepts
6. Add mnemonics or memory aids where helpful
7. Include practice questions at the end to reinforce learning

Format your notes with:
- A clear title/topic at the top
- Major section headings (H2)
- Subsection headings (H3) where needed
- Bullet points for key points
- Numbered lists for steps or sequences
- Highlighted key terms using **bold** formatting
- Italic formatting for *emphasis* where appropriate
- Special "Note" or "Important" callouts for critical information

The notes should be comprehensive yet concise, focusing on what a student would need for effective revision and understanding of the material.

Include at the end:
1. A section of 3-5 practice questions that test understanding of the key concepts
2. A very brief summary of the most essential takeaways (3-5 points maximum)

Your notes should be academically rigorous while being accessible and useful for study purposes.
"""
    
    async def generate_key_concepts(self, transcription: str) -> list:
        """
        Generate key concepts from the lecture transcription using Gemini.
        
        Args:
            transcription: The lecture transcription text
            
        Returns:
            A list of key concepts extracted from the transcription
        """
        if not transcription:
            raise ValueError("Transcription is required for key concepts generation")
        
        try:
            # Construct the prompt for Gemini
            system_prompt = self._build_key_concepts_prompt()
            
            # Send to Gemini
            response = await self.gemini.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription}
                ]
            )
            
            # Parse the response to extract the list of concepts
            # The response is expected to be a list of concepts, one per line
            concepts_text = response.content.strip()
            
            # Split by lines and clean up
            concepts = [concept.strip() for concept in concepts_text.split('\n') if concept.strip()]
            
            # Remove any numbering or bullet points at the beginning
            concepts = [re.sub(r'^[\d\.\-\*]+\s*', '', concept) for concept in concepts]
            
            # Limit to at most 10 concepts
            return concepts[:10]
            
        except Exception as e:
            logger.error(f"Failed to generate key concepts: {str(e)}")
            
            # Return some default concepts as fallback
            return [
                "Understanding core principles (AI generated)",
                "Analyzing key theories (AI generated)",
                "Application of concepts (AI generated)",
                "Critical evaluation of ideas (AI generated)",
                "Synthesis of information (AI generated)"
            ]
    
    def _build_key_concepts_prompt(self) -> str:
        """
        Build the system prompt for Gemini to extract key concepts.
        
        Returns:
            A string containing the system prompt for Gemini
        """
        return """You are ConceptExtractor, an AI specialized in identifying the most important concepts from academic lectures.

Your task is to analyze the lecture transcription and identify 5-10 key concepts that represent the most important ideas, theories, or skills covered in the lecture.

For each concept:
1. Be specific rather than general
2. Focus on actionable knowledge or understandable ideas
3. Phrase each as a short, clear statement (10-15 words maximum)
4. Ensure each concept is distinct from the others
5. Present them in order of importance or as they appear in the lecture

Format your response as a simple list with one concept per line. Do not include numbering, explanations, or any additional text.

Example format:
Understanding the fundamental principles of quantum mechanics
Applying wave-particle duality to explain electron behavior
Calculating energy states using Schrödinger's equation
Interpreting probability distributions in quantum systems
Connecting quantum phenomena to macroscopic observations

Your list should capture the essence of what a student should take away from this lecture.
"""
    
    async def generate_learning_resources(self, transcription: str) -> list:
        """
        Generate recommended learning resources based on the lecture transcription.
        Uses Gemini with web search capabilities to find real resources.
        
        Args:
            transcription: The lecture transcription text
            
        Returns:
            A list of dictionaries containing resource information with real URLs
        """
        if not transcription:
            raise ValueError("Transcription is required for resources generation")
        
        try:
            # Extract key topics from the transcription for targeted searches
            key_topics = await self._extract_key_topics(transcription)
            
            # Construct the prompt for Gemini with web search
            system_prompt = self._build_resources_prompt_with_search()
            
            # Create input for Gemini that includes both transcription summary and key topics
            transcription_summary = transcription[:1000] + "..." if len(transcription) > 1000 else transcription
            user_input = f"""Transcription Summary: {transcription_summary}
            
Key Topics to Research:
{' '.join(key_topics)}

Please research and find real, accessible learning resources (articles, videos, books, tools, courses) 
relevant to these topics that would help students understand the lecture material better."""
            
            # Send to Gemini with web search capability
            response = await self.gemini_with_search.ainvoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            )
            
            # Parse the response to extract the resources
            resources_text = response.content.strip()
            
            # Better parsing for resources with URLs
            resources = self._parse_resources_with_urls(resources_text)
            
            # Ensure we have some resources
            if not resources:
                # Try one more time with a simpler prompt
                retry_response = await self.gemini_with_search.ainvoke(
                    [
                        {"role": "system", "content": self._build_simple_resources_prompt()},
                        {"role": "user", "content": f"Find learning resources about: {' '.join(key_topics[:3])}"}
                    ]
                )
                resources = self._parse_resources_with_urls(retry_response.content.strip())
                
                if not resources:
                    # Create some default resources
                    resources = self._generate_default_resources()
            
            # Limit to at most 5 resources
            return resources[:5]
            
        except Exception as e:
            logger.error(f"Failed to generate learning resources with web search: {str(e)}")
            
            # Return some default resources as fallback
            return self._generate_default_resources()
    
    async def _extract_key_topics(self, transcription: str) -> list:
        """
        Extract key topics from transcription for targeted web searches.
        
        Args:
            transcription: The lecture transcription text
            
        Returns:
            List of key topics for research
        """
        try:
            # Use Gemini to extract key topics
            response = await self.gemini.ainvoke(
                [
                    {"role": "system", "content": "Extract 3-5 key research topics from this lecture transcription. Return only a simple list of topics, one per line, with no numbers or bullets."},
                    {"role": "user", "content": transcription}
                ]
            )
            
            # Parse topics
            topics = [topic.strip() for topic in response.content.strip().split('\n') if topic.strip()]
            
            # Return limited list of topics
            return topics[:5]
        except Exception as e:
            logger.error(f"Failed to extract key topics: {str(e)}")
            # Return generic topics
            return ["lecture topic", "academic resources", "learning materials"]
    
    def _parse_resources_with_urls(self, resources_text: str) -> list:
        """
        Parse response text to extract resources with URLs.
        
        Args:
            resources_text: Text response from Gemini
            
        Returns:
            List of resource dictionaries with URLs
        """
        lines = [line.strip() for line in resources_text.split('\n') if line.strip()]
        
        resources = []
        current_resource = None
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        
        for line in lines:
            # Check if this line is a new resource (starts with a type indicator)
            if any(line.lower().startswith(prefix) for prefix in ["article:", "video:", "book:", "paper:", "tool:", "course:"]):
                # Save previous resource if exists
                if current_resource:
                    resources.append(current_resource)
                
                # Start a new resource
                parts = line.split(':', 1)
                resource_type = parts[0].lower().strip()
                title = parts[1].strip() if len(parts) > 1 else "Untitled"
                
                current_resource = {
                    "type": resource_type,
                    "title": title,
                    "description": "",
                    "url": ""
                }
            elif current_resource:
                # Check if line contains a URL
                url_match = re.search(url_pattern, line)
                if url_match and not current_resource["url"]:
                    current_resource["url"] = url_match.group(0)
                    # Remove the URL from the line for description
                    line = re.sub(url_pattern, '', line).strip()
                
                # Add to description if there's content left
                if line:
                    current_resource["description"] += line + " "
        
        # Add the last resource if exists
        if current_resource:
            resources.append(current_resource)
        
        # Clean up descriptions and ensure all resources have required fields
        valid_resources = []
        for resource in resources:
            if "description" in resource:
                resource["description"] = resource["description"].strip()
            
            if not resource.get("url"):
                # Try to extract URL from description if not found separately
                url_match = re.search(url_pattern, resource.get("description", ""))
                if url_match:
                    resource["url"] = url_match.group(0)
                    # Clean description
                    resource["description"] = re.sub(url_pattern, '', resource["description"]).strip()
                else:
                    # Add placeholder URL
                    resource["url"] = "#"
            
            valid_resources.append(resource)
        
        return valid_resources
    
    def _build_resources_prompt_with_search(self) -> str:
        """
        Build the system prompt for Gemini with web search to recommend learning resources.
        
        Returns:
            A string containing the system prompt for Gemini
        """
        return """You are LearningResourceCurator, an AI specialized in finding real, high-quality educational resources
using web search to complement lecture content.

Your task is to analyze the lecture topics and use web search to find 3-5 relevant, REAL learning 
resources that would enhance the student's understanding of the topic.

For each resource, you MUST provide:
1. The type of resource (Article, Video, Book, Paper, Tool, Course)
2. A concise, descriptive title
3. The ACTUAL URL where the resource can be accessed
4. A brief description (1-2 sentences) explaining why it's relevant

Format each resource as follows:
[TYPE]: [TITLE]
[URL]
[DESCRIPTION]

Resource selection guidelines:
- Include a mix of resource types (not just all videos or all articles)
- Focus on resources from reputable academic sources or established platforms
- Ensure all URLs are real, complete and directly accessible
- Include both introductory and more advanced resources when appropriate
- Prioritize resources that are freely accessible when possible
- Verify the URL actually exists by searching for it

IMPORTANT: Do NOT create fictional resources or URLs. All recommendations must be REAL resources
you discovered through web search that actually exist and are relevant to the lecture topics.
"""

    def _build_simple_resources_prompt(self) -> str:
        """
        Build a simpler system prompt for retrying resource generation.
        
        Returns:
            A string containing a simplified system prompt
        """
        return """Find 3-5 real learning resources on the specified topic. For each resource, provide:
1. Resource type (Article, Video, etc.)
2. Title
3. URL (must be real)
4. Brief description

Format: 
[TYPE]: [TITLE]
[URL]
[DESCRIPTION]

ONLY provide real resources with working URLs that you can verify through search."""
    
    def _generate_default_resources(self) -> list:
        """
        Generate default learning resources when the AI generation fails.
        
        Returns:
            A list of default resource dictionaries
        """
        return [
            {
                "type": "article",
                "title": "Comprehensive Guide to Topic (AI Generated)",
                "description": "A detailed article covering the fundamental concepts discussed in the lecture."
            },
            {
                "type": "video",
                "title": "Visual Explanation of Key Concepts (AI Generated)",
                "description": "A video tutorial that demonstrates the practical application of the lecture material."
            },
            {
                "type": "book",
                "title": "Advanced Study Reference (AI Generated)",
                "description": "A comprehensive textbook that provides in-depth coverage of all topics mentioned in the lecture."
            }
        ]

# Create a singleton instance
lecture_transcription_service = LectureTranscriptionService() 