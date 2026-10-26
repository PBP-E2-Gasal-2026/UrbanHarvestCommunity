# from django.contrib import admin
# Register your models here.

from .models import Merchant, Profile, Role, SellerApplication, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff')
    search_fields = ('username', 'email')
    exclude = ('password',)


@admin.register(SellerApplication)
class SellerApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'status', 'created_at', 'reviewed_by')
    list_filter = ('status',)


admin.site.register(Role)
admin.site.register(Profile)
admin.site.register(Merchant)