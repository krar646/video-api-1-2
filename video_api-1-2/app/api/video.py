"""Video API endpoints.

This module implements requirements 12 and 13:
- Req 12: Video information endpoint
- Req 13: Format listing endpoint
- Custom: Extract endpoint for Flutter app
"""

from typing import Any, Optional

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.schemas import (
    FormatsResponse,
    SubtitleResponse,
    VideoFormatResponse,
    VideoInfoResponse,
)
from app.core.validation import URLValidator
from app.middleware.auth import require_api_key
from app.providers.exceptions import InvalidURLError, ProviderError, VideoUnavailableError
from app.providers.manager import ProviderManager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["video"])

# URL validator instance
url_validator = URLValidator()


# Dependency placeholder for provider manager
async def get_provider_manager() -> ProviderManager:
    """Get provider manager instance."""
    raise NotImplementedError("Provider manager dependency not configured")


# 🌟 نموذج البيانات الخاص بالتطبيق (Flutter)
class ExtractRequest(BaseModel):
    url: str
    type: str = "video"
    cookies: Optional[str] = ""


@router.get(
    "/info",
    response_model=VideoInfoResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        400: {"description": "Invalid URL"},
        404: {"description": "Video not found"},
        500: {"description": "Server error"},
    },
)
async def get_video_info(
    url: str = Query(..., description="Video URL"),  # noqa: B008
    include_formats: bool = Query(False, description="Include available formats"),  # noqa: B008
    include_subtitles: bool = Query(False, description="Include available subtitles"),  # noqa: B008
    provider_manager: ProviderManager = Depends(get_provider_manager),  # noqa: B008
) -> Any:
    """
    Get video metadata.

    Returns video information including title, duration, author, etc.
    Optionally includes available formats and subtitles.
    """
    logger.info("video_info_requested", url=url, include_formats=include_formats)

    # Validate URL
    validation = url_validator.validate(url)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_URL",
                "message": validation.error_message,
            },
        )

    # === استثناء يوتيوب فقط ===
    parsed_url_lower = url.lower()
    if "youtube.com" in parsed_url_lower or "youtu.be" in parsed_url_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "YOUTUBE_NOT_ALLOWED",
                "message": "معلومات منصة يوتيوب غير مسموح بها حالياً.",
            },
        )
    # ==========================

    try:
        # Get provider for URL
        provider = provider_manager.get_provider_for_url(url)

        # Get video info
        info = await provider.get_info(
            url=url,
            include_formats=include_formats,
            include_subtitles=include_subtitles,
        )

        # Build response
        response = VideoInfoResponse(
            video_id=info["video_id"],
            title=info["title"],
            duration=info["duration"],
            author=info["author"],
            upload_date=info["upload_date"],
            view_count=info["view_count"],
            thumbnail_url=info["thumbnail_url"],
            description=info["description"],
        )

        # Add formats if requested
        if include_formats and "formats" in info:
            response.formats = [
                VideoFormatResponse(
                    format_id=f["format_id"],
                    ext=f["ext"],
                    resolution=f.get("resolution"),
                    audio_bitrate=f.get("audio_bitrate"),
                    video_codec=f.get("video_codec"),
                    audio_codec=f.get("audio_codec"),
                    filesize=f.get("filesize"),
                    format_type=f.get("format_type", "video+audio"),
                )
                for f in info["formats"]
            ]

        # Add subtitles if requested
        if include_subtitles and "subtitles" in info:
            response.subtitles = [
                SubtitleResponse(
                    language=s["language"],
                    format=s["format"],
                    auto_generated=s["auto_generated"],
                )
                for s in info["subtitles"]
            ]

        logger.info(
            "video_info_retrieved",
            video_id=info["video_id"],
            title=info["title"],
        )

        return response

    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_URL", "message": str(e)},
        )
    except VideoUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VIDEO_UNAVAILABLE", "message": str(e)},
        )
    except ProviderError as e:
        logger.error("provider_error", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "PROVIDER_ERROR", "message": str(e)},
        )
    except Exception as e:
        logger.error("unexpected_error", url=url, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )


@router.get(
    "/formats",
    response_model=FormatsResponse,
    dependencies=[Depends(require_api_key)],
    responses={
        400: {"description": "Invalid URL"},
        404: {"description": "Video not found"},
        500: {"description": "Server error"},
    },
)
async def get_video_formats(
    url: str = Query(..., description="Video URL"),  # noqa: B008
    provider_manager: ProviderManager = Depends(get_provider_manager),  # noqa: B008
) -> Any:
    """
    Get available video formats.
    """
    logger.info("formats_requested", url=url)

    # Validate URL
    validation = url_validator.validate(url)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_URL", "message": validation.error_message},
        )

    # === استثناء يوتيوب فقط ===
    parsed_url_lower = url.lower()
    if "youtube.com" in parsed_url_lower or "youtu.be" in parsed_url_lower:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "YOUTUBE_NOT_ALLOWED", "message": "صيغ منصة يوتيوب غير مسموح بها حالياً."},
        )
    # ==========================

    try:
        # Get provider for URL
        provider = provider_manager.get_provider_for_url(url)

        # Get formats (single API call, no redundant get_info)
        formats = await provider.list_formats(url)

        # Convert to response format
        format_responses = [
            VideoFormatResponse(
                format_id=f.format_id,
                ext=f.ext,
                resolution=f.resolution,
                audio_bitrate=f.audio_bitrate,
                video_codec=f.video_codec,
                audio_codec=f.audio_codec,
                filesize=f.filesize,
                format_type=f.format_type,
            )
            for f in formats
        ]

        # Group by type
        video_audio = [f for f in format_responses if f.format_type == "video+audio"]
        video_only = [f for f in format_responses if f.format_type == "video-only"]
        audio_only = [f for f in format_responses if f.format_type == "audio-only"]

        response = FormatsResponse(
            formats=format_responses,
            video_audio=video_audio,
            video_only=video_only,
            audio_only=audio_only,
        )

        logger.info("formats_retrieved", url=url, total_formats=len(formats))

        return response

    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_URL", "message": str(e)},
        )
    except VideoUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "VIDEO_UNAVAILABLE", "message": str(e)},
        )
    except ProviderError as e:
        logger.error("provider_error", url=url, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "PROVIDER_ERROR", "message": str(e)},
        )
    except Exception as e:
        logger.error("unexpected_error", url=url, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )


# =========================================================
# 🌟 المسار المخصص للتطبيق (Flutter) - Extract Endpoint
# =========================================================
@router.post(
    "/extract",
    dependencies=[Depends(require_api_key)],
)
async def extract_media_for_app(
    request: ExtractRequest,
    provider_manager: ProviderManager = Depends(get_provider_manager),
) -> Any:
    """
    Custom endpoint for the Flutter app.
    Accepts POST requests with JSON body.
    """
    url = request.url
    logger.info("app_extract_requested", url=url, type=request.type)

    # 🌟 استثناء صارم ليوتيوب
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "YOUTUBE_NOT_ALLOWED",
                "message": "لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل."
            },
        )

    try:
        # Validate URL
        validation = url_validator.validate(url)
        if not validation.is_valid:
            raise InvalidURLError(validation.error_message)

        # Get provider for URL
        provider = provider_manager.get_provider_for_url(url)

        # Get video info
        info = await provider.get_info(
            url=url,
            include_formats=True,
            include_subtitles=False,
        )

        # تجهيز الرد بالشكل اللي التطبيق بتاعك متوقعه
        return {
            "success": True,
            "status": "success",
            "type": request.type,
            "title": info.get("title", "فيديو"),
            "thumbnail": info.get("thumbnail_url", ""),
            "formats": info.get("formats", []),
            "video_url": info.get("formats", [{}])[-1].get("url", "") if info.get("formats") else "",
        }

    except InvalidURLError as e:
        raise HTTPException(status_code=400, detail={"error_code": "INVALID_URL", "message": str(e)})
    except VideoUnavailableError as e:
        raise HTTPException(status_code=404, detail={"error_code": "VIDEO_UNAVAILABLE", "message": str(e)})
    except ProviderError as e:
        raise HTTPException(status_code=500, detail={"error_code": "PROVIDER_ERROR", "message": str(e)})
    except Exception as e:
        logger.error("app_extract_error", url=url, error=str(e))
        raise HTTPException(status_code=500, detail={"error_code": "INTERNAL_ERROR", "message": str(e)})