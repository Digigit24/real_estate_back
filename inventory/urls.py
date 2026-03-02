from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, TowerViewSet, UnitViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'towers', TowerViewSet, basename='tower')
router.register(r'units', UnitViewSet, basename='unit')

urlpatterns = [
    path('', include(router.urls)),
]
