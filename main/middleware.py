from django.http import HttpResponseNotFound
# main/middleware.py
from urllib.parse import unquote
from django.utils import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class UserOrCookieTimezoneMiddleware:
    COOKIE_NAME = "tz"
    COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 years

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = None
        cookie_raw = request.COOKIES.get(self.COOKIE_NAME)
        cookie_decoded = None
        should_rewrite_cookie = False

       # 1) Authenticated user setting takes precedence ONLY if it's a non-UTC value
        user_tz = getattr(request.user, "timezone",
                          None) if request.user.is_authenticated else None
        if user_tz and user_tz.upper() != "UTC":
            tzname = user_tz

        # 2) Otherwise fall back to cookie
        if tzname is None and cookie_raw:
            cookie_decoded = unquote(cookie_raw)
            if cookie_decoded != cookie_raw:
                should_rewrite_cookie = True
            tzname = cookie_decoded

        activated = False
        error = None
        if tzname:
            try:
                timezone.activate(ZoneInfo(tzname))
                activated = True
            except ZoneInfoNotFoundError as e:
                error = f"ZoneInfoNotFound: {tzname}"
                timezone.deactivate()
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                timezone.deactivate()
        else:
            timezone.deactivate()

        response = self.get_response(request)

        # Debug headers (remove later)
        response.headers["X-TZ-User"] = user_tz or ""
        response.headers["X-TZ-Cookie-Raw"] = cookie_raw or ""
        response.headers["X-TZ-Activated"] = "1" if activated else "0"
        if error:
            logger.warning("TZ activate failed: %s", error)
            response.headers["X-TZ-Error"] = error

        if should_rewrite_cookie and activated:
            response.set_cookie(
                self.COOKIE_NAME,
                tzname,
                max_age=self.COOKIE_MAX_AGE,
                samesite="Lax",
                path="/",
            )
        elif cookie_raw and not activated and not user_tz:
            response.delete_cookie(self.COOKIE_NAME, path="/")

        return response


class BlockWordPressPathsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        blocked_paths = [
            '/wp-includes/wlwmanifest.xml',
            '/xmlrpc.php',
            '/wp-login.php',
            '/blog/wp-includes/wlwmanifest.xml',
            '/web/wp-includes/wlwmanifest.xml',
            '/wordpress/wp-includes/wlwmanifest.xml',
            '/website/wp-includes/wlwmanifest.xml',
            '/wp/wp-includes/wlwmanifest.xml',
            '/news/wp-includes/wlwmanifest.xml',
            '/2018/wp-includes/wlwmanifest.xml',
            '/2019/wp-includes/wlwmanifest.xml',
            '/shop/wp-includes/wlwmanifest.xml',
            '/wp1/wp-includes/wlwmanifest.xml',
            '/test/wp-includes/wlwmanifest.xml',
            '/media/wp-includes/wlwmanifest.xml',
            '/wp2/wp-includes/wlwmanifest.xml',
            '/site/wp-includes/wlwmanifest.xml',
            '/cms/wp-includes/wlwmanifest.xml',
            '/sito/wp-includes/wlwmanifest.xml',
        ]
        if request.path in blocked_paths:
            return HttpResponseNotFound()
        return self.get_response(request)


class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = request.headers.get(
            "X-Request-ID", str(uuid.uuid4()))

    def process_response(self, request, response):
        rid = getattr(request, "request_id", None)
        if rid:
            response["X-Request-ID"] = rid
        return response
