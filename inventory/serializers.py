from rest_framework import serializers
from common.mixins import TenantMixin
from .models import Project, Tower, Unit, UnitStatusEnum


class ProjectSerializer(TenantMixin):
    tower_count = serializers.IntegerField(source='towers.count', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'rera_number', 'description', 'location',
            'address', 'city', 'state', 'pincode', 'google_maps_url',
            'total_units', 'launch_date', 'possession_date',
            'logo_url', 'banner_url', 'is_active',
            'tower_count', 'owner_user_id', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'tower_count', 'created_at', 'updated_at']


class ProjectListSerializer(TenantMixin):
    tower_count = serializers.IntegerField(source='towers.count', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'city', 'state', 'rera_number',
            'total_units', 'launch_date', 'possession_date',
            'is_active', 'tower_count', 'logo_url', 'created_at',
        ]
        read_only_fields = ['id', 'tower_count', 'created_at']


class TowerSerializer(TenantMixin):
    project_name = serializers.CharField(source='project.name', read_only=True)
    unit_count = serializers.IntegerField(source='units.count', read_only=True)

    class Meta:
        model = Tower
        fields = [
            'id', 'project', 'project_name', 'name',
            'total_floors', 'units_per_floor', 'description',
            'is_active', 'unit_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'project_name', 'unit_count', 'created_at', 'updated_at']


class UnitSerializer(TenantMixin):
    tower_name = serializers.CharField(source='tower.name', read_only=True)
    project_name = serializers.CharField(source='tower.project.name', read_only=True)
    project_id = serializers.IntegerField(source='tower.project.id', read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Unit
        fields = [
            'id', 'tower', 'tower_name', 'project_id', 'project_name',
            'unit_number', 'floor_number', 'bhk_type',
            'carpet_area', 'built_up_area', 'super_built_up_area', 'facing',
            'base_price', 'floor_rise_premium', 'facing_premium',
            'parking_charges', 'other_charges', 'total_price',
            'status', 'reserved_for_lead_id',
            'remarks', 'is_active', 'owner_user_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tower_name', 'project_id', 'project_name',
            'total_price', 'created_at', 'updated_at',
        ]


class UnitListSerializer(TenantMixin):
    """Lightweight serializer for unit lists and grid views"""
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Unit
        fields = [
            'id', 'tower', 'unit_number', 'floor_number', 'bhk_type',
            'carpet_area', 'facing', 'base_price', 'total_price',
            'status', 'reserved_for_lead_id',
        ]
        read_only_fields = ['id', 'total_price']


class UnitGridCellSerializer(serializers.Serializer):
    """Single cell in the unit grid (floor x flat position)"""
    id = serializers.IntegerField()
    unit_number = serializers.CharField()
    floor_number = serializers.IntegerField()
    bhk_type = serializers.CharField()
    carpet_area = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    facing = serializers.CharField(allow_null=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    status = serializers.CharField()
    reserved_for_lead_id = serializers.IntegerField(allow_null=True)


class UnitGridRowSerializer(serializers.Serializer):
    """One floor row in the unit grid"""
    floor_number = serializers.IntegerField()
    units = UnitGridCellSerializer(many=True)


class PriceCalculatorSerializer(serializers.Serializer):
    """Input for the price calculator"""
    base_price = serializers.DecimalField(max_digits=14, decimal_places=2)
    floor_rise_premium = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    facing_premium = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    parking_charges = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_charges = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)


class UnitReserveSerializer(serializers.Serializer):
    """Reserve a unit for a specific lead"""
    lead_id = serializers.IntegerField()


class UnitStatusUpdateSerializer(serializers.Serializer):
    """Update unit status"""
    status = serializers.ChoiceField(choices=UnitStatusEnum.choices)
    lead_id = serializers.IntegerField(required=False, allow_null=True)
