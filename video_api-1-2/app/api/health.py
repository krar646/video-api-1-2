"""Health check endpoints.

This module implements requirements 11, 30, and 37:
- Req 11: Health monitoring with component verification
- Req 30: Detailed health checks
- Req 37: Container health probes (liveness/readiness)
"""

import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Literal

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app import __version__
from app.api.schemas import ComponentHealth, HealthResponse, LivenessResponse, ReadinessResponse
from app.core.checks import check_ffmpeg, check_nodejs, check_ytdlp


def _is_test_mode() -> bool:
    """Check if test mode is enabled via environment variable."""
    return os.environ.get("APP_TESTING_TEST_MODE", "").lower() in ("true", "1", "yes")


# Capture test mode at module import time (env var may not be visible in async context)
_TEST_MODE_CACHED = _is_test_mode()

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])

# Track application start time for uptime calculation
_start_time: float = time.time()


def reset_start_time() -> None:
    """Reset the start time (for testing)."""
    global _start_time
    _start_time = time.time()


async def _check_ytdlp() -> ComponentHealth:
    """Check yt-dlp availability and version."""
    result = await check_ytdlp()
    if result.available:
        return ComponentHealth(status="healthy", version=result.version)
    return ComponentHealth(
        status="unhealthy",
        details={"error": result.error or "yt-dlp not available"},
    )


async def _check_ffmpeg() -> ComponentHealth:
    """Check ffmpeg availability and version."""
    result = await check_ffmpeg()
    if result.available:
        return ComponentHealth(status="healthy", version=result.version)
    return ComponentHealth(
        status="unhealthy",
        details={"error": result.error or "ffmpeg not available"},
    )


async def _check_nodejs() -> ComponentHealth:
    """Check Node.js availability and version."""
    result = await check_nodejs(min_version=20)
    if result.available:
        return ComponentHealth(status="healthy", version=result.version)
    return ComponentHealth(
        status="unhealthy",
        version=result.version,
        details={"error": result.error or "Node.js not available"},
    )


def _check_storage() -> ComponentHealth:
    """Check storage availability."""
    try:
        from app.services.storage import get_storage_manager

        storage = get_storage_manager()
        usage = storage.get_disk_usage()

        return ComponentHealth(
            status="healthy",
            details={
                "available_gb": round(usage.available / (1024**3), 2),
                "used_percent": round(usage.percent_used, 1),
            },
        )
    except RuntimeError:
        # Storage manager not configured yet
        return ComponentHealth(
            status="unhealthy",
            details={"error": "Storage manager not configured"},
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            details={"error": str(e)},
        )


def _check_cookies() -> ComponentHealth:
    """Check cookie status for providers."""
    try:
        # Import from main to get the configured cookie service
        from app.main import get_cookie_service

        cookie_service = get_cookie_service()
        providers = cookie_service.list_providers_with_cookies()

        if not providers:
            return ComponentHealth(
                status="unhealthy",
                details={"error": "No cookie files configured"},
            )

        # Check if any provider has valid cookies
        healthy_providers = [p for p, info in providers.items() if info.get("exists", False)]

        if healthy_providers:
            details: Dict[str, Any] = {}
            for provider, info in providers.items():
                details[provider] = {
                    "exists": info.get("exists", False),
                    "age_hours": info.get("age_hours"),
                }
                if info.get("age_hours") and info["age_hours"] > 168:  # 7 days
                    details[provider]["warning"] = "Cookie file is older than 7 days"

            return ComponentHealth(status="healthy", details=details)

        return ComponentHealth(
            status="unhealthy",
            details={"error": "No valid cookie files found", "providers": providers},
        )
    except RuntimeError:
        # Cookie service not configured yet
        return ComponentHealth(
            status="unhealthy",
            details={"error": "Cookie service not configured"},
        )
    except Exception as e:
        return ComponentHealth(
            status="unhealthy",
            details={"error": str(e)},
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        200: {"description": "All components healthy"},
        503: {"description": "One or more components unhealthy"},
    },
)
async def health_check() -> JSONResponse:
    """
    Detailed health check endpoint.

    Verifies all system components:
    - yt-dlp availability and version
    - ffmpeg availability and version
    - Node.js >= 20 availability
    - Cookie file status
    - Storage availability

    Returns HTTP 200 if all components are healthy,
    HTTP 503 if any component is unhealthy.
    """
    # Run all async checks concurrently
    ytdlp_task = _check_ytdlp()
    ffmpeg_task = _check_ffmpeg()
    nodejs_task = _check_nodejs()

    ytdlp_health, ffmpeg_health, nodejs_health = await asyncio.gather(
        ytdlp_task, ffmpeg_task, nodejs_task
    )

    # These are sync checks
    storage_health = _check_storage()
    cookie_health = _check_cookies()

    components = {
        "ytdlp": ytdlp_health,
        "ffmpeg": ffmpeg_health,
        "nodejs": nodejs_health,
        "storage": storage_health,
        "cookie": cookie_health,
    }

    # Determine overall status
    all_healthy = all(c.status == "healthy" for c in components.values())
    overall_status: Literal["healthy", "unhealthy"] = "healthy" if all_healthy else "unhealthy"

    uptime = time.time() - _start_time

    response = HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=__version__,
        uptime_seconds=round(uptime, 2),
        test_mode=_TEST_MODE_CACHED,
        components=components,
    )

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    logger.info(
        "health_check_completed",
        status=overall_status,
        components={k: v.status for k, v in components.items()},
    )

    return JSONResponse(content=response.model_dump(), status_code=status_code)


@router.get("/liveness", response_model=LivenessResponse)
async def liveness_check() -> LivenessResponse:
    """
    Liveness probe endpoint.

    Returns HTTP 200 if the process is alive.
    Used by container orchestration to determine if the container
    should be restarted.
    """
    return LivenessResponse(status="alive")


@router.get(
    "/readiness",
    response_model=ReadinessResponse,
    responses={
        200: {"description": "Service is ready to accept traffic"},
        503: {"description": "Service is not ready"},
    },
)
async def readiness_check() -> JSONResponse:
    """
    Readiness probe endpoint.

    Returns HTTP 200 if the service is ready to accept traffic.
    Used by load balancers to determine if traffic should be routed
    to this instance.

    Checks:
    - yt-dlp is available
    - Storage manager is configured
    """
    issues = []

    # Quick yt-dlp check
    ytdlp_health = await _check_ytdlp()
    if ytdlp_health.status != "healthy":
        issues.append("yt-dlp not available")

    # Quick storage check
    storage_health = _check_storage()
    if storage_health.status != "healthy":
        issues.append("Storage not ready")

    if issues:
        response = ReadinessResponse(
            status="not_ready",
            ready=False,
            message="; ".join(issues),
        )
        return JSONResponse(
            content=response.model_dump(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return JSONResponse(
        content=ReadinessResponse(status="ready", ready=True).model_dump(),
        status_code=status.HTTP_200_OK,
    )