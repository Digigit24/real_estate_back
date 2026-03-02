from django.contrib import admin
from .models import Project, Tower, Unit


class TowerInline(admin.TabularInline):
    model = Tower
    extra = 0
    fields = ['name', 'total_floors', 'units_per_floor', 'is_active']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'rera_number', 'total_units', 'launch_date', 'is_active', 'tenant_id']
    list_filter = ['is_active', 'city', 'state']
    search_fields = ['name', 'rera_number', 'city']
    inlines = [TowerInline]


@admin.register(Tower)
class TowerAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'total_floors', 'units_per_floor', 'is_active']
    list_filter = ['is_active', 'project']
    search_fields = ['name', 'project__name']


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = [
        'unit_number', 'tower', 'floor_number', 'bhk_type',
        'carpet_area', 'facing', 'base_price', 'status',
    ]
    list_filter = ['status', 'bhk_type', 'facing', 'tower__project']
    search_fields = ['unit_number', 'tower__name', 'tower__project__name']
    list_editable = ['status']
