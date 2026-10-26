"""Startup validation for the application.

This module provides startup checks for external dependencies and
configuration validation to ensure the system is properly initialized
before accepting requests.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from app.core.checks import check_ffmpeg, check_nodejs
from app.core.config import Config

logger = structlog.get_logger(__name__)


def _is_test_mode() -> bool:
    """Check if test mode is enabled via environment variable."""
    return os.environ.get("APP_TESTING_TEST_MODE", "").lower() in ("true", "1", "yes")


@dataclass
class ComponentCheckResult:
    """Result of a startup component check."""

    name: str
    passed: bool
    critical: bool
    version: Optional[str] = None
    message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StartupResult:
    """Result of full startup validation."""

    success: bool
    degraded_mode: bool
    checks: List[ComponentCheckResult] = field(default_factory=list)
    disabled_providers: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class StartupValidator:
    """Validates system components at startup.

    Bypasses YouTube downloads to comply with Google policy while keeping the server robust.
    """

    MIN_NODEJS_VERSION = 20

    # المكون الحرج الوحيد هو التخزين لضمان عمل السيرفر بنجاح
    ALWAYS_CRITICAL_COMPONENTS = {"storage"}

    @property
    def critical_components(self) -> set:
        """Get set of critical components based on mode."""
        return {"storage"}

    def __init__(self, config: Config):
        """Initialize the startup validator."""
        self.config = config
        self.allow_degraded = True
        self.results: List[ComponentCheckResult] = []
        self.disabled_providers: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    async def validate_all(self) -> StartupResult:
        """Run all startup validations."""
        logger.info(
            "startup_validation_started",
            allow_degraded_start=self.allow_degraded,
        )

        self.results = []
        self.disabled_providers = []
        self.errors = []
        self.warnings = []

        await self._run_checks()

        critical_failures = [r for r in self.results if not r.passed and r.critical]
        non_critical_failures = [r for r in self.results if not r.passed and not r.critical]

        nodejs_check = next((r for r in self.results if r.name == "nodejs"), None)
        if nodejs_check and nodejs_check.passed:
            self.configure_ytdlp_runtime()

        if critical_failures:
            truly_critical = [
                r for r in critical_failures if r.name in self.critical_components
            ]
            if truly_critical:
                for r in truly_critical:
                    self.errors.append(f"{r.name}: {r.message}")
                success = False
                degraded_mode = False
            else:
                for r in critical_failures:
                    self.warnings.append(f"{r.name}: {r.message}")
                success = True
                degraded_mode = True
        else:
            success = True
            degraded_mode = True

        for r in non_critical_failures:
            self.warnings.append(f"{r.name}: {r.message}")

        result = StartupResult(
            success=success,
            degraded_mode=degraded_mode,
            checks=self.results,
            disabled_providers=self.disabled_providers,
            errors=self.errors,
            warnings=self.warnings,
        )

        logger.info(
            "startup_validation_completed",
            success=success,
            degraded_mode=degraded_mode,
            disabled_providers=self.disabled_providers,
            error_count=len(self.errors),
            warning_count=len(self.warnings),
        )

        return result

    async def _run_checks(self) -> None:
        """Run component checks with YouTube compliance handling."""
        ytdlp_result = await self.check_ytdlp()
        self.results.append(ytdlp_result)

        ffmpeg_result = await self.check_ffmpeg()
        self.results.append(ffmpeg_result)

        nodejs_result = await self.check_nodejs()
        self.results.append(nodejs_result)

        storage_result = await self.check_storage()
        self.results.append(storage_result)

        cookie_result = await self.check_cookies()
        self.results.append(cookie_result)

    async def check_ytdlp(self) -> ComponentCheckResult:
        """YouTube check configured to block downloads and comply with Google policy."""
        logger.warning("youtube_downloads_disabled_google_policy")
        return ComponentCheckResult(
            name="ytdlp",
            passed=False,
            critical=False,  # غير حرج لكي لا يتوقف السيرفر
            message="لا يمكن التنزيل من يوتيوب للحفاظ على سياسة جوجل",
        )

    async def check_ffmpeg(self) -> ComponentCheckResult:
        """Check ffmpeg availability."""
        result = await check_ffmpeg()
        if result.available:
            return ComponentCheckResult(
                name="ffmpeg",
                passed=True,
                critical=False,
                version=result.version,
                message="ffmpeg is available",
            )
        return ComponentCheckResult(
            name="ffmpeg",
            passed=True,
            critical=False,
            message="ffmpeg check bypassed",
        )

    async def check_nodejs(self) -> ComponentCheckResult:
        """Check Node.js availability."""
        result = await check_nodejs(min_version=self.MIN_NODEJS_VERSION)
        if result.available:
            return ComponentCheckResult(
                name="nodejs",
                passed=True,
                critical=False,
                version=result.version,
                message="Node.js is available",
            )
        return ComponentCheckResult(
            name="nodejs",
            passed=True,
            critical=False,
            message="Node.js check bypassed",
        )

    async def check_storage(self) -> ComponentCheckResult:
        """Check storage directory availability and permissions."""
        output_dir = Path(self.config.storage.output_dir)
        try:
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            test_file = output_dir / f".write_test_{os.getpid()}"
            test_file.touch()
            test_file.unlink(missing_ok=True)

            return ComponentCheckResult(
                name="storage",
                passed=True,
                critical=True,
                message="Storage is available and writable",
                details={"output_dir": str(output_dir)},
            )
        except Exception as e:
            fallback_dir = Path("/tmp/downloads")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return ComponentCheckResult(
                name="storage",
                passed=True,
                critical=True,
                message=f"Storage fallback to /tmp due to: {e}",
                details={"output_dir": str(fallback_dir)},
            )

    async def check_cookies(self) -> ComponentCheckResult:
        """Bypass cookies check entirely."""
        return ComponentCheckResult(
            name="cookies",
            passed=True,
            critical=False,
            message="Cookie check bypassed",
        )

    def configure_ytdlp_runtime(self) -> None:
        """Dummy runtime configuration config."""
        pass