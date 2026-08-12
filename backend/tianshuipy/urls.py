"""
URL configuration for tianshuipy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic.base import RedirectView
from django.views.static import serve
from django.urls import path, include, re_path, reverse
from rest_framework.schemas.openapi import SchemaGenerator

def home_view(request):
    """首页视图 - 显示系统信息"""
    return render(request, 'index.html')

def overlay_analysis_demo_view(request):
    """叠加分析演示页面"""
    return render(request, 'overlay_analysis_demo.html')


def api_docs_view(request):
    """API 文档首页"""
    return render(request, 'api_docs.html', {
        'schema_url': reverse('api-schema'),
    })


def api_schema_view(request):
    """输出 OpenAPI schema JSON"""
    generator = SchemaGenerator(
        title='天水平台 API 文档',
        description='天水平台后端接口的 OpenAPI 描述。',
        url=request.build_absolute_uri('/'),
    )
    schema = generator.get_schema(request=request, public=True)
    return JsonResponse(schema, json_dumps_params={'ensure_ascii': False})

urlpatterns = [
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    path("", home_view, name="home"),  # 根路径显示首页
    path("admin/", admin.site.urls),
    path("overlay-analysis-demo/", overlay_analysis_demo_view, name="overlay-analysis-demo"),  # 叠加分析演示页面
    path("api/docs/", api_docs_view, name="api-docs"),
    path("api/schema/", api_schema_view, name="api-schema"),
    path("api/v1/", include([
        path("users/", include('users.urls')),
        path("environment/", include('environment.urls')),
    ])),
    path("api/", RedirectView.as_view(url='/api/v1/', permanent=False)),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
