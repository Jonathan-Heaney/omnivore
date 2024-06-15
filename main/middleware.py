from django.http import HttpResponseNotFound


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
