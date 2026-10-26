from django.contrib import admin

from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'area', 'owner', 'is_active', 'detail_visibility', 'updated_at')
    list_filter = ('kind', 'is_active', 'detail_visibility')
    search_fields = ('name', 'area', 'address', 'commodities', 'managed_by', 'owner__username')
    list_select_related = ('owner',)
    raw_id_fields = ('owner',)
    actions = ('activate', 'deactivate')

    @admin.action(description='Tampilkan lokasi terpilih di peta')
    def activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} lokasi ditampilkan.')

    @admin.action(description='Sembunyikan lokasi terpilih dari peta')
    def deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} lokasi disembunyikan.')
