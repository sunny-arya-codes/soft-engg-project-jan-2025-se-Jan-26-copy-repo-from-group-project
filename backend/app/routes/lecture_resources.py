from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import logging
from app.routes.auth import get_current_user
from app.services.lecture_transcription_service import lecture_transcription_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Define request/response models
class VideoUrlRequest(BaseModel):
    video_url: str

class NotesRequest(BaseModel):
    notes: str

class TranscriptionResponse(BaseModel):
    transcription: str
    video_id: Optional[str] = None
    language: Optional[str] = None

class SummaryResponse(BaseModel):
    summary: str

class NotesResponse(BaseModel):
    notes: str

class SmartNotesResponse(BaseModel):
    smart_notes: str
    
class KeyConceptResponse(BaseModel):
    concepts: List[str]

class Resource(BaseModel):
    type: str
    title: str
    description: str
    url: Optional[str] = "#"
    
class ResourceResponse(BaseModel):
    resources: List[Resource]

# API Routes for lecture resources
@router.get("/courses/{course_id}/lectures/{lecture_id}/transcription",
    summary="Get lecture transcription",
    description="Get the transcription for a specific lecture",
    response_model=TranscriptionResponse
)
async def get_lecture_transcription(
    course_id: str, 
    lecture_id: str,
    video_url: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the transcription for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        video_url: Optional YouTube URL to generate transcription if not found in database
        current_user: The authenticated user
        
    Returns:
        The lecture transcription
    """
    try:
        # Here we would typically retrieve the transcription from a database
        # For this example, we'll simulate a database lookup
        
        # Simulated database check - in a real implementation, you'd query your DB
        # transcription = db.get_transcription(lecture_id)
        
        # Placeholder response
        # TODO: Replace with actual database lookup
        transcription = None
        
        if not transcription:
            # If no transcription is found in the database and a video URL is provided,
            # try to get it from YouTube
            if not video_url:
                # No transcription in database and no URL provided
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No transcription found for lecture {lecture_id} and no video URL provided"
                )
            
            # Generate the transcription from YouTube using the provided URL
            try:
                transcription_data = await lecture_transcription_service.get_transcription(video_url)
                
                # Check if there was an error in retrieving the transcription
                if "error" in transcription_data and transcription_data.get("error"):
                    logger.error(f"Error in transcription service: {transcription_data.get('error')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch transcription: {transcription_data.get('error')}"
                    )
                
                # Here you would save the transcription to the database
                # db.save_transcription(lecture_id, transcription_data)
                
                return TranscriptionResponse(
                    transcription=transcription_data.get("transcription", ""),
                    video_id=transcription_data.get("video_id"),
                    language=transcription_data.get("language")
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to fetch transcription from YouTube: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch transcription from the provided video URL: {str(e)}"
                )
        
        return TranscriptionResponse(
            transcription=transcription.get("transcription", ""),
            video_id=transcription.get("video_id"),
            language=transcription.get("language")
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture transcription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching lecture transcription: {str(e)}"
        )

@router.post("/courses/{course_id}/lectures/{lecture_id}/transcription",
    summary="Generate lecture transcription",
    description="Generate a transcription for a specific lecture from a YouTube video",
    response_model=TranscriptionResponse
)
async def generate_lecture_transcription(
    course_id: str, 
    lecture_id: str,
    request: VideoUrlRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate a transcription for a specific lecture from a YouTube video.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: The video URL request body
        current_user: The authenticated user
        
    Returns:
        The generated lecture transcription
    """
    try:
        # Get the transcription using the service
        transcription_data = await lecture_transcription_service.get_transcription(request.video_url)
        
        # Check if there was an error in retrieving the transcription
        if "error" in transcription_data and transcription_data.get("error"):
            logger.error(f"Error in transcription service: {transcription_data.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch transcription: {transcription_data.get('error')}"
            )
        
        # Here we would typically save the transcription to a database
        # For this example, we'll just return the generated transcription
        
        # TODO: Add database storage code
        # db.save_transcription(lecture_id, transcription_data)
        
        return TranscriptionResponse(
            transcription=transcription_data.get("transcription", ""),
            video_id=transcription_data.get("video_id"),
            language=transcription_data.get("language")
        )
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating lecture transcription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating lecture transcription: {str(e)}"
        )

@router.get("/courses/{course_id}/lectures/{lecture_id}/summary",
    summary="Get lecture summary",
    description="Get the AI-generated summary for a specific lecture",
    response_model=SummaryResponse
)
async def get_lecture_summary(
    course_id: str, 
    lecture_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the AI-generated summary for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        current_user: The authenticated user
        
    Returns:
        The lecture summary
    """
    try:
        # Here we would typically retrieve the summary from a database
        # For this example, we'll simulate a database lookup
        
        # Simulated database check - in a real implementation, you'd query your DB
        # summary = db.get_summary(lecture_id)
        
        # Placeholder response
        # TODO: Replace with actual database lookup
        summary = None
        
        if not summary:
            # If no summary is found, return a 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No summary found for lecture {lecture_id}"
            )
        
        # Assuming the database stores the summary directly
        return SummaryResponse(summary=summary)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching lecture summary: {str(e)}"
        )

@router.post("/courses/{course_id}/lectures/{lecture_id}/summary",
    summary="Generate lecture summary",
    description="Generate a summary for a specific lecture",
    response_model=SummaryResponse
)
async def generate_lecture_summary(
    course_id: str, 
    lecture_id: str,
    request: Optional[Dict[str, str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate a summary for a specific lecture using AI.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: Optional request containing video_url
        current_user: The authenticated user
        
    Returns:
        The generated summary
    """
    try:
        # Extract video_url from request body if provided
        video_url = None
        if request and "video_url" in request:
            video_url = request["video_url"]
        
        # In a real implementation, you'd first check if the summary already exists in the database
        # summary = db.get_summary(lecture_id)
        # if summary:
        #     return SummaryResponse(summary=summary)
        
        # If there's no summary, we need to get the transcription first
        # transcription = db.get_transcription(lecture_id)
        transcription = None
        
        if not transcription:
            # If no transcription is found in the database and a video URL is provided,
            # try to get it from YouTube
            if not video_url:
                # No transcription in database and no URL provided
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No transcription found for lecture {lecture_id} and no video URL provided"
                )
            
            try:
                transcription_data = await lecture_transcription_service.get_transcription(video_url)
                
                # Check if there was an error in retrieving the transcription
                if "error" in transcription_data and transcription_data.get("error"):
                    logger.error(f"Error in transcription service: {transcription_data.get('error')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch transcription: {transcription_data.get('error')}"
                    )
                
                transcription_text = transcription_data.get("transcription", "")
            except Exception as e:
                logger.error(f"Failed to fetch transcription from YouTube: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch transcription from the provided video URL: {str(e)}"
                )
        else:
            transcription_text = transcription.get("transcription", "")
        
        # Now generate the summary using the AI service
        summary = await lecture_transcription_service.generate_summary(transcription_text)
        
        # In a real implementation, you'd save the summary to the database
        # db.save_summary(lecture_id, summary)
        
        return SummaryResponse(summary=summary)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating lecture summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating lecture summary: {str(e)}"
        )

@router.get("/courses/{course_id}/lectures/{lecture_id}/smart-notes",
    summary="Get lecture smart notes",
    description="Get the AI-generated smart notes for a specific lecture",
    response_model=NotesResponse
)
async def get_lecture_smart_notes(
    course_id: str, 
    lecture_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the AI-generated smart notes for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        current_user: The authenticated user
        
    Returns:
        The lecture smart notes
    """
    try:
        # Here we would typically retrieve the notes from a database
        # For this example, we'll simulate a database lookup
        
        # Simulated database check - in a real implementation, you'd query your DB
        # notes = db.get_smart_notes(lecture_id, user_id=current_user["id"])
        
        # Placeholder response
        # TODO: Replace with actual database lookup
        notes = None
        
        if not notes:
            # If no notes are found, return a 404
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No smart notes found for lecture {lecture_id}"
            )
        
        return NotesResponse(notes=notes.get("notes", ""))
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture smart notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching lecture smart notes: {str(e)}"
        )

@router.post("/courses/{course_id}/lectures/{lecture_id}/smart-notes",
    summary="Generate smart notes",
    description="Generate smart notes for a specific lecture",
    response_model=SmartNotesResponse
)
async def generate_lecture_smart_notes(
    course_id: str, 
    lecture_id: str,
    request: Optional[Dict[str, str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate smart notes for a specific lecture using AI.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: Optional request containing video_url
        current_user: The authenticated user
        
    Returns:
        The generated smart notes
    """
    try:
        # Extract video_url from request body if provided
        video_url = None
        if request and "video_url" in request:
            video_url = request["video_url"]
        
        # In a real implementation, you'd first check if smart notes already exist in the database
        # smart_notes = db.get_smart_notes(lecture_id)
        # if smart_notes:
        #     return SmartNotesResponse(smart_notes=smart_notes)
        
        # If there are no smart notes, we need to get the transcription first
        # transcription = db.get_transcription(lecture_id)
        transcription = None
        
        if not transcription:
            # If no transcription is found in the database and a video URL is provided,
            # try to get it from YouTube
            if not video_url:
                # No transcription in database and no URL provided
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No transcription found for lecture {lecture_id} and no video URL provided"
                )
            
            try:
                transcription_data = await lecture_transcription_service.get_transcription(video_url)
                
                # Check if there was an error in retrieving the transcription
                if "error" in transcription_data and transcription_data.get("error"):
                    logger.error(f"Error in transcription service: {transcription_data.get('error')}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch transcription: {transcription_data.get('error')}"
                    )
                
                transcription_text = transcription_data.get("transcription", "")
            except Exception as e:
                logger.error(f"Failed to fetch transcription from YouTube: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch transcription from the provided video URL: {str(e)}"
                )
        else:
            transcription_text = transcription.get("transcription", "")
        
        # Now generate the smart notes using the AI service
        smart_notes = await lecture_transcription_service.generate_smart_notes(transcription_text)
        
        # In a real implementation, you'd save the smart notes to the database
        # db.save_smart_notes(lecture_id, smart_notes)
        
        return SmartNotesResponse(smart_notes=smart_notes)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating lecture smart notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating lecture smart notes: {str(e)}"
        )

@router.put("/courses/{course_id}/lectures/{lecture_id}/smart-notes",
    summary="Save lecture smart notes",
    description="Save user-edited smart notes for a specific lecture",
    response_model=NotesResponse
)
async def save_lecture_smart_notes(
    course_id: str, 
    lecture_id: str,
    request: NotesRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Save user-edited smart notes for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: The notes request body
        current_user: The authenticated user
        
    Returns:
        The saved smart notes
    """
    try:
        if not request.notes:
            raise ValueError("Notes content cannot be empty")
        
        # Here we would save the notes to a database
        # For this example, we'll just return the notes
        
        # TODO: Add database storage code
        # db.save_smart_notes(lecture_id, user_id=current_user["id"], {"text": request.notes})
        
        return NotesResponse(notes=request.notes)
        
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error saving lecture smart notes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving lecture smart notes: {str(e)}"
        )

@router.get("/courses/{course_id}/lectures/{lecture_id}/key-concepts",
    summary="Get lecture key concepts",
    description="Get AI-generated key concepts for a specific lecture",
    response_model=KeyConceptResponse
)
async def get_lecture_key_concepts(
    course_id: str, 
    lecture_id: str,
    video_url: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get AI-generated key concepts for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        video_url: Optional YouTube URL to fetch transcription if not found
        current_user: The authenticated user
        
    Returns:
        The lecture key concepts
    """
    try:
        # Here we would typically retrieve the key concepts from a database
        # For this example, we'll check if they exist and generate if not
        
        # Placeholder for database lookup
        # key_concepts = db.get_key_concepts(lecture_id)
        key_concepts = None
        
        if not key_concepts:
            # If no key concepts found, generate them from the transcription
            try:
                # Get the transcription first
                try:
                    transcription_data = await get_lecture_transcription(course_id, lecture_id, video_url, current_user)
                    transcription_text = transcription_data.transcription
                    
                    if not transcription_text:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No transcription found for lecture {lecture_id}"
                        )
                except HTTPException as http_ex:
                    # If it's a 404 and we have a video URL, provide a more helpful error
                    if http_ex.status_code == 404 and video_url:
                        logger.warning(f"No transcription found for lecture {lecture_id}, trying to generate with video URL")
                        # We'll fallback to default concepts for now to avoid frontend breakage
                        return KeyConceptResponse(concepts=[
                            "Understanding lecture concepts (placeholder)",
                            "Key theories from the lecture (placeholder)",
                            "Practical applications (placeholder)",
                            "Important definitions (placeholder)",
                            "Further learning opportunities (placeholder)"
                        ])
                    raise  # Re-raise if it's any other HTTP exception
                
                # Generate key concepts from transcription
                # In a real implementation, this would use an AI service
                concepts = await lecture_transcription_service.generate_key_concepts(transcription_text)
                
                # In a real implementation, we would save these to the database
                # db.save_key_concepts(lecture_id, concepts)
                
                return KeyConceptResponse(concepts=concepts)
            except Exception as e:
                logger.error(f"Error generating key concepts: {str(e)}")
                # Return fallback concepts rather than 500 error for better UX
                return KeyConceptResponse(concepts=[
                    "Understanding lecture concepts (error fallback)",
                    "Key theories from the lecture (error fallback)",
                    "Practical applications (error fallback)",
                    "Important definitions (error fallback)",
                    "Further learning opportunities (error fallback)"
                ])
        else:
            return KeyConceptResponse(concepts=key_concepts)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture key concepts: {str(e)}")
        # Return fallback data instead of error for better UX
        return KeyConceptResponse(concepts=[
            "Understanding core concepts (system error fallback)",
            "Analyzing key theories (system error fallback)",
            "Application of principles (system error fallback)",
            "Critical evaluation of ideas (system error fallback)",
            "Synthesis of information (system error fallback)"
        ])

@router.post("/courses/{course_id}/lectures/{lecture_id}/key-concepts",
    summary="Generate lecture key concepts",
    description="Generate key concepts for a specific lecture",
    response_model=KeyConceptResponse
)
async def generate_lecture_key_concepts(
    course_id: str, 
    lecture_id: str,
    request: Optional[Dict[str, str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate key concepts for a specific lecture using AI.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: Optional request containing video_url
        current_user: The authenticated user
        
    Returns:
        The generated key concepts
    """
    try:
        # Extract video_url from request body if provided
        video_url = None
        if request and "video_url" in request:
            video_url = request["video_url"]
        
        # Get the transcription first
        try:
            transcription_data = await get_lecture_transcription(course_id, lecture_id, video_url, current_user)
            transcription_text = transcription_data.transcription
            
            if not transcription_text:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No transcription found for lecture {lecture_id}"
                )
            
            # Generate key concepts from transcription using AI
            concepts = await lecture_transcription_service.generate_key_concepts(transcription_text)
            
            # In a real implementation, we would save these to the database
            # db.save_key_concepts(lecture_id, concepts)
            
            return KeyConceptResponse(concepts=concepts)
        except HTTPException as http_ex:
            # If the HTTP exception is from the transcription service, re-raise it
            raise http_ex
        except Exception as e:
            logger.error(f"Error generating key concepts: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating key concepts: {str(e)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating lecture key concepts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating lecture key concepts: {str(e)}"
        )

@router.get("/courses/{course_id}/lectures/{lecture_id}/learning-resources",
    summary="Get lecture learning resources",
    description="Get AI-generated learning resources for a specific lecture",
    response_model=ResourceResponse
)
async def get_lecture_learning_resources(
    course_id: str, 
    lecture_id: str,
    video_url: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get AI-generated learning resources for a specific lecture.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        video_url: Optional YouTube URL to fetch transcription if not found
        current_user: The authenticated user
        
    Returns:
        The lecture learning resources
    """
    try:
        # Here we would typically retrieve the resources from a database
        # For this example, we'll check if they exist and generate if not
        
        # Placeholder for database lookup
        # resources = db.get_learning_resources(lecture_id)
        resources = None
        
        if not resources:
            # If no resources found, generate them from the transcription
            try:
                # Get the transcription first
                try:
                    transcription_data = await get_lecture_transcription(course_id, lecture_id, video_url, current_user)
                    transcription_text = transcription_data.transcription
                    
                    if not transcription_text:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No transcription found for lecture {lecture_id}"
                        )
                except HTTPException as http_ex:
                    # If it's a 404 and we have a video URL, provide a more helpful error
                    if http_ex.status_code == 404 and video_url:
                        logger.warning(f"No transcription found for lecture {lecture_id}, trying to generate with video URL")
                        # We'll fallback to default resources for now to avoid frontend breakage
                        return ResourceResponse(resources=[
                            {
                                "type": "article",
                                "title": "Introduction to the Topic (placeholder)",
                                "description": "A comprehensive article covering the basics."
                            },
                            {
                                "type": "video",
                                "title": "Video Tutorial Series (placeholder)",
                                "description": "Step-by-step video explanations with examples."
                            },
                            {
                                "type": "book",
                                "title": "Recommended Textbook (placeholder)",
                                "description": "The definitive resource on this subject."
                            }
                        ])
                    raise  # Re-raise if it's any other HTTP exception
                
                # Generate resources from transcription
                resources = await lecture_transcription_service.generate_learning_resources(transcription_text)
                
                # In a real implementation, we would save these to the database
                # db.save_learning_resources(lecture_id, resources)
                
                return ResourceResponse(resources=resources)
            except Exception as e:
                logger.error(f"Error generating learning resources: {str(e)}")
                # Return fallback resources rather than 500 error for better UX
                return ResourceResponse(resources=[
                    {
                        "type": "article",
                        "title": "Introduction to the Topic (error fallback)",
                        "description": "A comprehensive article covering the basics of this subject area."
                    },
                    {
                        "type": "video",
                        "title": "Video Tutorial Series (error fallback)",
                        "description": "Step-by-step video explanations with practical examples."
                    },
                    {
                        "type": "book",
                        "title": "Recommended Textbook (error fallback)",
                        "description": "The definitive resource on this subject with in-depth coverage."
                    }
                ])
        else:
            return ResourceResponse(resources=resources)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture learning resources: {str(e)}")
        # Return fallback data instead of error for better UX
        return ResourceResponse(resources=[
            {
                "type": "article",
                "title": "Introduction to the Topic (system error fallback)",
                "description": "A comprehensive article covering the basics of this subject area."
            },
            {
                "type": "video",
                "title": "Video Tutorial Series (system error fallback)",
                "description": "Step-by-step video explanations with practical examples."
            },
            {
                "type": "book",
                "title": "Recommended Textbook (system error fallback)",
                "description": "The definitive resource on this subject with in-depth coverage."
            }
        ])

@router.post("/courses/{course_id}/lectures/{lecture_id}/learning-resources",
    summary="Generate lecture learning resources",
    description="Generate learning resources for a specific lecture",
    response_model=ResourceResponse
)
async def generate_lecture_learning_resources(
    course_id: str, 
    lecture_id: str,
    request: Optional[Dict[str, str]] = Body(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate learning resources for a specific lecture using AI.
    
    Args:
        course_id: The ID of the course
        lecture_id: The ID of the lecture
        request: Optional request containing video_url
        current_user: The authenticated user
        
    Returns:
        The generated learning resources
    """
    try:
        # Extract video_url from request body if provided
        video_url = None
        if request and "video_url" in request:
            video_url = request["video_url"]
        
        # Get the transcription first
        try:
            transcription_data = await get_lecture_transcription(course_id, lecture_id, video_url, current_user)
            transcription_text = transcription_data.transcription
            
            if not transcription_text:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No transcription found for lecture {lecture_id}"
                )
            
            # Generate resources from transcription using AI
            resources = await lecture_transcription_service.generate_learning_resources(transcription_text)
            
            # In a real implementation, we would save these to the database
            # db.save_learning_resources(lecture_id, resources)
            
            return ResourceResponse(resources=resources)
        except HTTPException as http_ex:
            # If the HTTP exception is from the transcription service, re-raise it
            raise http_ex
        except Exception as e:
            logger.error(f"Error generating learning resources: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating learning resources: {str(e)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating lecture learning resources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating lecture learning resources: {str(e)}"
        ) 