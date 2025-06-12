from django.contrib import admin
from .models import Kategori, Urun, Musteri, Garson, Siparis, SiparisUrun

class SiparisUrunInline(admin.TabularInline):
    model = SiparisUrun
    extra = 0
    readonly_fields = ('toplam_fiyat',)

@admin.register(Siparis)
class SiparisAdmin(admin.ModelAdmin):
    list_display = ('masa_no', 'olusturma_tarihi', 'durum', 'odeme_durum', 'toplam_tutar')
    list_filter = ('durum', 'odeme_durum', 'olusturma_tarihi')
    search_fields = ('masa_no',)
    readonly_fields = ('toplam_tutar', 'odeme_tarihi')
    inlines = [SiparisUrunInline]

@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ('isim', 'sira')
    ordering = ('sira',)

@admin.register(Urun)
class UrunAdmin(admin.ModelAdmin):
    list_display = ('isim', 'kategori', 'fiyat', 'stokta')
    list_filter = ('kategori', 'stokta')
    search_fields = ('isim', 'aciklama')

@admin.register(Musteri)
class MusteriAdmin(admin.ModelAdmin):
    list_display = ('isim', 'masa_no', 'oturum_baslangic', 'aktif')
    list_filter = ('aktif',)

@admin.register(Garson)
class GarsonAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

@admin.register(SiparisUrun)
class SiparisUrunAdmin(admin.ModelAdmin):
    list_display = ('siparis', 'urun', 'adet', 'birim_fiyat')
