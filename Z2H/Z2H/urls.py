"""
URL configuration for Z2H project.

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
from django.urls import path, include, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)
from django.views.generic import TemplateView

urlpatterns = [
    path('z2hdjadmin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='api-schema'),
        name='api-docs',
    ),
    path('api/z2h/app/', include('apps.app.urls')),
    path('api/z2h/user/', include('apps.user.urls')),
    path('api/z2h/utils/', include('apps.utils.urls')),
]

urlpatterns += [
    re_path(r'^admin(?:.*)/?$', TemplateView.as_view(template_name='index.html'), name='app'),
    re_path(r'^(?!admin)(?:.*)/?$',
        TemplateView.as_view(template_name='site_index.html'),
        name='site'),
]