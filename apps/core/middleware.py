"""Middleware для внедрения современных заголовков безопасности."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """
    Добавляет заголовки безопасности в каждый HTTP-ответ:
    - Content-Security-Policy (CSP)
    - Permissions-Policy
    - Referrer-Policy
    - Cross-Origin-Opener-Policy
    - X-Content-Type-Options
    """

    DEFAULT_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    DEFAULT_PERMISSIONS_POLICY = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Content-Security-Policy
        if "Content-Security-Policy" not in response:
            csp = getattr(settings, "SECURE_CSP_HEADER", self.DEFAULT_CSP)
            if csp:
                response["Content-Security-Policy"] = csp

        # Permissions-Policy
        if "Permissions-Policy" not in response:
            perm_policy = getattr(
                settings, "SECURE_PERMISSIONS_POLICY_HEADER", self.DEFAULT_PERMISSIONS_POLICY
            )
            if perm_policy:
                response["Permissions-Policy"] = perm_policy

        # Referrer-Policy
        if "Referrer-Policy" not in response:
            response["Referrer-Policy"] = getattr(
                settings, "SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin"
            )

        # Cross-Origin-Opener-Policy
        if "Cross-Origin-Opener-Policy" not in response:
            response["Cross-Origin-Opener-Policy"] = getattr(
                settings, "SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin"
            )

        # X-Content-Type-Options
        if "X-Content-Type-Options" not in response:
            response["X-Content-Type-Options"] = "nosniff"

        return response
