"""Custom exceptions for MarkCrawl.

These exceptions are raised instead of sys.exit() so that MarkCrawl
can be used as a library without killing the caller's process.
CLI entry points catch these and convert to sys.exit() with a message.
"""


class MarkcrawlError(Exception):
    """Base exception for all MarkCrawl errors."""


class MarkcrawlConfigError(MarkcrawlError):
    """Raised when a required configuration value is missing.

    Examples: missing API key, missing environment variable.
    """


class MarkcrawlDependencyError(MarkcrawlError):
    """Raised when an optional dependency is not installed.

    Examples: openai, anthropic, playwright, supabase, mcp.
    """
