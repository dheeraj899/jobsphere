"""
URL configuration for Project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

schema_view = get_schema_view(
    openapi.Info(
        title="JobSphere API",
        default_version='v1',
        description="API documentation for JobSphere",
        contact=openapi.Contact(email="support@jobsphere.example.com"),
    ),
    public=True,
    authentication_classes=(JWTAuthentication,),
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', RedirectView.as_view(url='swagger/', permanent=False)),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('accounts/', include('django.contrib.auth.urls')),
    # Admin interface
    path('admin/', admin.site.urls),
    
    # API v1 endpoints
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/profile/', include('apps.profile.urls')),
    path('api/v1/jobs/', include('apps.jobs.urls')),
    path('api/v1/map/', include('apps.map.urls')),
    path('api/v1/activity/', include('apps.activity.urls')),
    path('api/v1/messaging/', include('apps.messaging.urls')),
    path('api/v1/search/', include('apps.search.urls')),
    path('api/v1/media/', include('apps.media.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/navigation/', include('apps.navigation.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
