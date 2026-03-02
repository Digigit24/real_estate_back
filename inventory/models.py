from django.db import models


class FacingEnum(models.TextChoices):
    NORTH = 'NORTH', 'North'
    SOUTH = 'SOUTH', 'South'
    EAST = 'EAST', 'East'
    WEST = 'WEST', 'West'
    NORTH_EAST = 'NORTH_EAST', 'North East'
    NORTH_WEST = 'NORTH_WEST', 'North West'
    SOUTH_EAST = 'SOUTH_EAST', 'South East'
    SOUTH_WEST = 'SOUTH_WEST', 'South West'


class UnitStatusEnum(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    RESERVED = 'RESERVED', 'Reserved'
    BOOKED = 'BOOKED', 'Booked'
    REGISTERED = 'REGISTERED', 'Registered'
    SOLD = 'SOLD', 'Sold'
    BLOCKED = 'BLOCKED', 'Blocked'


class BHKTypeEnum(models.TextChoices):
    STUDIO = 'STUDIO', 'Studio'
    ONE_BHK = '1BHK', '1 BHK'
    ONE_POINT_FIVE_BHK = '1.5BHK', '1.5 BHK'
    TWO_BHK = '2BHK', '2 BHK'
    TWO_POINT_FIVE_BHK = '2.5BHK', '2.5 BHK'
    THREE_BHK = '3BHK', '3 BHK'
    FOUR_BHK = '4BHK', '4 BHK'
    PENTHOUSE = 'PENTHOUSE', 'Penthouse'
    VILLA = 'VILLA', 'Villa'
    PLOT = 'PLOT', 'Plot'
    COMMERCIAL = 'COMMERCIAL', 'Commercial'


class Project(models.Model):
    """Real estate project / development"""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    name = models.TextField()
    rera_number = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.TextField(null=True, blank=True)
    state = models.TextField(null=True, blank=True)
    pincode = models.TextField(null=True, blank=True)
    google_maps_url = models.TextField(null=True, blank=True)

    total_units = models.IntegerField(default=0)
    launch_date = models.DateField(null=True, blank=True)
    possession_date = models.DateField(null=True, blank=True)

    logo_url = models.TextField(null=True, blank=True)
    banner_url = models.TextField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_projects_tenant_id'),
            models.Index(fields=['tenant_id', 'is_active'], name='idx_projects_tenant_active'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'name'],
                name='unique_project_name_per_tenant'
            )
        ]

    def __str__(self):
        return self.name


class Tower(models.Model):
    """Tower or phase within a project"""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='towers',
        db_column='project_id'
    )
    name = models.TextField()
    total_floors = models.IntegerField(default=1)
    units_per_floor = models.IntegerField(default=1)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'towers'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_towers_tenant_id'),
            models.Index(fields=['project'], name='idx_towers_project_id'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'name'],
                name='unique_tower_name_per_project'
            )
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class Unit(models.Model):
    """Individual unit / flat within a tower"""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    tower = models.ForeignKey(
        Tower,
        on_delete=models.CASCADE,
        related_name='units',
        db_column='tower_id'
    )
    unit_number = models.TextField()
    floor_number = models.IntegerField()
    bhk_type = models.CharField(max_length=20, choices=BHKTypeEnum.choices)
    carpet_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    built_up_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    super_built_up_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    facing = models.CharField(
        max_length=20,
        choices=FacingEnum.choices,
        null=True,
        blank=True
    )

    # Pricing
    base_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    floor_rise_premium = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    facing_premium = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    parking_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    other_charges = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=UnitStatusEnum.choices,
        default=UnitStatusEnum.AVAILABLE,
        db_index=True
    )

    # Which lead has reserved/booked this unit
    reserved_for_lead_id = models.BigIntegerField(null=True, blank=True, db_index=True)

    remarks = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'units'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_units_tenant_id'),
            models.Index(fields=['tower'], name='idx_units_tower_id'),
            models.Index(fields=['status'], name='idx_units_status'),
            models.Index(fields=['floor_number'], name='idx_units_floor_number'),
            models.Index(fields=['bhk_type'], name='idx_units_bhk_type'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tower', 'unit_number'],
                name='unique_unit_number_per_tower'
            )
        ]

    @property
    def total_price(self):
        base = self.base_price or 0
        return base + self.floor_rise_premium + self.facing_premium + self.parking_charges + self.other_charges

    def __str__(self):
        return f"{self.tower} - Unit {self.unit_number} (Floor {self.floor_number})"
