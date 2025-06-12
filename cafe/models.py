from django.db import models
from django.contrib.auth.models import User
import uuid
import os

# Create your models here.

class Garson(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

class Musteri(models.Model):
    isim = models.CharField(max_length=100)
    masa_no = models.IntegerField()
    oturum_baslangic = models.DateTimeField(auto_now_add=True)
    aktif = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.masa_no} - {self.isim}"

def urun_resim_yolu(instance, filename):
    # Dosya uzantısını al
    ext = filename.split('.')[-1]
    # Yeni dosya adını oluştur: urun_adi_uuid.uzanti
    filename = f"{instance.isim}_{uuid.uuid4().hex[:8]}.{ext}"
    # Dosya yolunu döndür
    return os.path.join('urunler', filename)

class Kategori(models.Model):
    isim = models.CharField(max_length=100)
    sira = models.IntegerField(default=0)

    def __str__(self):
        return self.isim

    class Meta:
        verbose_name_plural = "Kategoriler"
        ordering = ['sira']

class Urun(models.Model):
    kategori = models.ForeignKey(Kategori, on_delete=models.CASCADE, related_name='urunler')
    isim = models.CharField(max_length=100)
    aciklama = models.TextField(blank=True)
    fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    resim = models.ImageField(upload_to=urun_resim_yolu, null=True, blank=True)
    stokta = models.BooleanField(default=True)

    def __str__(self):
        return self.isim

    class Meta:
        verbose_name_plural = "Ürünler"

class Siparis(models.Model):
    DURUM_CHOICES = [
        ('beklemede', 'Beklemede'),
        ('hazirlaniyor', 'Hazırlanıyor'),
        ('tamamlandi', 'Tamamlandı'),
        ('iptal', 'İptal')
    ]
    
    ODEME_DURUM = [
        ('bekliyor', 'Ödeme Bekliyor'),
        ('odendi', 'Ödendi'),
        ('iptal', 'İptal')
    ]
    
    masa_no = models.IntegerField()
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    durum = models.CharField(max_length=20, choices=DURUM_CHOICES, default='beklemede')
    odeme_durum = models.CharField(max_length=20, choices=ODEME_DURUM, default='bekliyor')
    toplam_tutar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    odeme_tarihi = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Masa {self.masa_no} - {self.olusturma_tarihi}"

class SiparisUrun(models.Model):
    siparis = models.ForeignKey(Siparis, on_delete=models.CASCADE, related_name='siparis_urunleri')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE)
    adet = models.IntegerField(default=1)
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    toplam_fiyat = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.toplam_fiyat = self.birim_fiyat * self.adet
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.urun.isim} x {self.adet}"
