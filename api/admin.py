from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Help, Event

# @admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('phone_number', 'full_name', 'gender', 'marital_status', 'profession', 'city', 'specific_place', 'is_staff', 'is_active' ) #,
    list_filter = ('city', 'gender', 'is_staff', 'gender',) 
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Permissions', {'fields': ( 'groups', 'user_permissions', 'is_staff', 'is_active', 'is_superuser')}), #
        ('Important dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'is_staff', 'is_active')} #
        ),
    )
    search_fields = ('phone_number',)
    ordering = ('phone_number',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'description',
        'location',
        'caption',
        'edir',
        'date',
        'status',
        'created_date',
    )

    list_filter = ('status', 'date', 'edir')
    search_fields = ('title', 'description', 'location', 'caption')
    ordering = ('-created_date',)

    readonly_fields = ('created_date',)

    fieldsets = (
        ('Event Information', {
            'fields': ('edir', 'title', 'description', 'caption')
        }),
        ('Location & Media', {
            'fields': ('location', 'image')
        }),
        ('Schedule & Status', {
            'fields': ('date', 'status')
        }),
        ('System Info', {
            'fields': ('created_date',)
        }),
    )

@admin.register(Help)
class HelpAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer','type', 'created_date')
    list_filter = ('type',)
    search_fields = ('question', 'answer')
    ordering = ('type', 'question')

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.register(CustomUser, CustomUserAdmin)
