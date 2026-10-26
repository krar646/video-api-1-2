"""Input validation utilities for the API layer.

This module provides validation functions for URLs, format IDs, and other
parameters that are used across API endpoints.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional, Set
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)


class AudioFormat(str, Enum):
    """Supported audio output formats."""

    MP3 = "mp3"
    M4A = "m4a"
    WAV = "wav"
    OPUS = "opus"


class AudioQuality(str, Enum):
    """Supported audio quality levels."""

    LOW = "128"
    MEDIUM = "192"
    HIGH = "320"


@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: Optional[str] = None


class URLValidator:
    """Validates URLs, allowing all platforms supported by yt-dlp except YouTube."""

    # YouTube domains to block
    BLOCKED_DOMAINS: FrozenSet[str] = frozenset(
        {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
            "youtube-nocookie.com",
        }
    )

    # Dangerous URL schemes that should always be rejected
    DANGEROUS_SCHEMES: FrozenSet[str] = frozenset(
        {
            "javascript",
            "data",
            "file",
            "vbscript",
            "about",
        }
    )

    def __init__(self, allowed_domains: Optional[Set[str]] = None):
        """
        Initialize URL validator.

        Args:
            allowed_domains: Kept for backwards compatibility.
        """
        pass

    def validate(self, url: str) -> ValidationResult:  # noqa: C901
        """Validate a URL, allowing all platforms except YouTube.

        Args:
            url: URL to validate

        Returns:
            ValidationResult with validation status and any error message
        """
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False, error_message="URL is required and must be a string"
            )

        url = url.strip()
        if not url:
            return ValidationResult(is_valid=False, error_message="URL cannot be empty")

        try:
            parsed = urlparse(url)
        except ValueError as e:
            logger.warning("URL parsing failed", url=url, error=str(e))
            return ValidationResult(is_valid=False, error_message="Invalid URL format")

        # Check for dangerous schemes
        scheme = parsed.scheme.lower() if parsed.scheme else ""
        if scheme in self.DANGEROUS_SCHEMES:
            logger.warning("Dangerous URL scheme detected", url=url, scheme=scheme)
            return ValidationResult(
                is_valid=False, error_message=f"URL scheme '{scheme}' is not allowed"
            )

        # Require http or https
        if scheme not in ("http", "https", ""):
            return ValidationResult(
                is_valid=False, error_message="URL must use http or https scheme"
            )

        # Extract and validate domain
        netloc = parsed.netloc.lower()
        if not netloc:
            # Handle URLs without scheme
            path_parts = parsed.path.split("/")
            if path_parts:
                potential_domain = path_parts[0].lower()
                if potential_domain and "." in potential_domain:
                    netloc = potential_domain

        if not netloc:
            return ValidationResult(is_valid=False, error_message="URL must include a valid domain")

        domain = parsed.hostname
        if domain:
            domain = domain.lower()
        else:
            domain = netloc.split(":")[0].split("@")[-1]

        # Check if domain is YouTube (Blocked) with Google policy compliance message
        if domain in self.BLOCKED_DOMAINS or any(yt in domain for yt in ["youtube.com", "youtu.be"]):
            logger.debug("YouTube URL blocked by validator", url=url, domain=domain)
            return ValidationResult(
                is_valid=False,
                error_message="لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل",
            )

        logger.debug("URL validated successfully (non-YouTube)", url=url, domain=domain)
        return ValidationResult(is_valid=True, sanitized_value=url)

    def is_valid(self, url: str) -> bool:
        """
        Quick check if URL is valid and not YouTube.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and allowed, False otherwise
        """
        return self.validate(url).is_valid


class FormatValidator:
    """Validates yt-dlp format IDs and specifications."""

    FORMAT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_+-]+$")
    MAX_FORMAT_ID_LENGTH = 50

    SPECIAL_SELECTORS: FrozenSet[str] = frozenset(
        {
            "best",
            "worst",
            "bestvideo",
            "worstvideo",
            "bestaudio",
            "worstaudio",
            "bestvideo+bestaudio",
            "best[height<=720]",
            "best[height<=1080]",
        }
    )

    def validate_format_id(self, format_id: str) -> ValidationResult:
        """Validate a format ID."""
        if not format_id or not isinstance(format_id, str):
            return ValidationResult(is_valid=False, error_message="Format ID is required")

        format_id = format_id.strip()
        if not format_id:
            return ValidationResult(is_valid=False, error_message="Format ID cannot be empty")

        if len(format_id) > self.MAX_FORMAT_ID_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_message=f"Format ID exceeds maximum length of {self.MAX_FORMAT_ID_LENGTH}",
            )

        if format_id.lower() in self.SPECIAL_SELECTORS:
            return ValidationResult(is_valid=True, sanitized_value=format_id)

        if not self.FORMAT_ID_PATTERN.match(format_id):
            return ValidationResult(
                is_valid=False,
                error_message="Format ID contains invalid characters",
            )

        return ValidationResult(is_valid=True, sanitized_value=format_id)

    def is_valid_format_id(self, format_id: str) -> bool:
        """Quick check if format ID is valid."""
        return self.validate_format_id(format_id).is_valid


class ParameterValidator:
    """Validates API request parameters."""

    def validate_audio_format(self, audio_format: str) -> ValidationResult:
        if not audio_format:
            return ValidationResult(is_valid=False, error_message="Audio format is required")

        try:
            AudioFormat(audio_format.lower())
            return ValidationResult(is_valid=True, sanitized_value=audio_format.lower())
        except ValueError:
            valid_formats = [f.value for f in AudioFormat]
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid audio format. Valid options: {', '.join(valid_formats)}",
            )

    def validate_audio_quality(self, quality: str) -> ValidationResult:
        if not quality:
            return ValidationResult(is_valid=False, error_message="Audio quality is required")

        try:
            AudioQuality(quality)
            return ValidationResult(is_valid=True, sanitized_value=quality)
        except ValueError:
            valid_qualities = [f.value for f in AudioQuality]
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid audio quality. Valid options: {', '.join(valid_qualities)}kbps",
            )

    def validate_language_code(self, lang_code: str) -> ValidationResult:
        if not lang_code or not isinstance(lang_code, str):
            return ValidationResult(is_valid=False, error_message="Language code is required")

        lang_code = lang_code.strip().lower()
        pattern = re.compile(r"^[a-z]{2,3}(-[a-zA-Z]{2,4})?$")

        if not pattern.match(lang_code):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid language code format. Use ISO 639 format (e.g., 'en', 'en-US')",
            )

        return ValidationResult(is_valid=True, sanitized_value=lang_code)

    def validate_positive_integer(
        self, value: int, name: str, max_value: Optional[int] = None
    ) -> ValidationResult:
        if not isinstance(value, int) or isinstance(value, bool):
            return ValidationResult(is_valid=False, error_message=f"{name} must be an integer")

        if value <= 0:
            return ValidationResult(
                is_valid=False, error_message=f"{name} must be a positive integer"
            )

        if max_value is not None and value > max_value:
            return ValidationResult(
                is_valid=False,
                error_message=f"{name} exceeds maximum allowed value of {max_value}",
            )

        return ValidationResult(is_valid=True, sanitized_value=str(value))


# Singleton instances for convenience
url_validator = URLValidator()
format_validator = FormatValidator()
parameter_validator = ParameterValidator()


def validate_format_id(format_id: str) -> bool:
    """Convenience function to validate format IDs."""
    return format_validator.is_valid_format_id(format_id)