from django.core.management.base import BaseCommand
from cafe.models import Musteri, Siparis
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Eski kayıtları ve tutarsız verileri temizler'

    def handle(self, *args, **options):
        # 24 saatten eski aktif müşterileri temizle
        eski_tarih = timezone.now() - timedelta(hours=24)
        eski_musteriler = Musteri.objects.filter(
            aktif=True,
            oturum_baslangic__lt=eski_tarih
        )
        eski_musteri_sayisi = eski_musteriler.count()
        eski_musteriler.update(aktif=False)
        
        # Tutarsız müşteri kayıtlarını temizle
        tutarsiz_musteriler = Musteri.objects.filter(
            aktif=True
        ).exclude(
            masa_no__in=Siparis.objects.filter(
                odeme_durum='bekliyor'
            ).values_list('masa_no', flat=True)
        )
        tutarsiz_musteri_sayisi = tutarsiz_musteriler.count()
        tutarsiz_musteriler.update(aktif=False)
        
        # Ödeme bekleyen siparişi olmayan masalardaki müşterileri temizle
        aktif_masalar = Siparis.objects.filter(
            odeme_durum='bekliyor'
        ).values_list('masa_no', flat=True).distinct()
        
        gereksiz_musteriler = Musteri.objects.filter(
            aktif=True
        ).exclude(
            masa_no__in=aktif_masalar
        )
        gereksiz_musteri_sayisi = gereksiz_musteriler.count()
        gereksiz_musteriler.update(aktif=False)
        
        self.stdout.write(self.style.SUCCESS(
            f'Temizleme tamamlandı:\n'
            f'- {eski_musteri_sayisi} eski müşteri kaydı temizlendi\n'
            f'- {tutarsiz_musteri_sayisi} tutarsız müşteri kaydı temizlendi\n'
            f'- {gereksiz_musteri_sayisi} gereksiz müşteri kaydı temizlendi'
        )) 