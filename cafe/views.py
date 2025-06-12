from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from .forms import GarsonLoginForm, MusteriOturumForm
from django.http import JsonResponse
from django.utils import timezone

from .models import Kategori, Urun, Siparis, SiparisUrun, Musteri, Garson, User
from decimal import Decimal

# Create your views here.

def is_admin(user):
    return user.is_superuser

def is_garson(user):
    return hasattr(user, 'garson')

def giris_secim(request):
    if request.method == 'POST':
        if 'masa_no' in request.POST and 'isim' in request.POST:  # Müşteri girişi
            masa_no = request.POST.get('masa_no')
            isim = request.POST.get('isim')
            if masa_no and isim:
                # Masa numarası kontrolü
                try:
                    masa_no = int(masa_no)
                    if masa_no < 1 or masa_no > 20:
                        messages.error(request, 'Geçersiz masa numarası. Lütfen 1-20 arası bir masa seçin.')
                        return redirect('giris_secim')
                except ValueError:
                    messages.error(request, 'Geçersiz masa numarası.')
                    return redirect('giris_secim')
                
                # Masa dolu mu kontrol et
                aktif_masa = Musteri.objects.filter(
                    masa_no=masa_no,
                    aktif=True
                ).exists()
                
                if aktif_masa:
                    messages.error(request, f'Masa {masa_no} şu anda dolu.')
                    return redirect('giris_secim')
                
                # Yeni müşteri kaydını oluştur
                musteri = Musteri.objects.create(
                    isim=isim,
                    masa_no=masa_no,
                    aktif=True
                )
                request.session['masa_no'] = masa_no
                request.session['musteri_id'] = musteri.id
                request.session['sepet'] = {}
                return redirect('menu')
                
        elif 'username' in request.POST:  # Admin veya Garson girişi
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_superuser:  # Admin girişi
                    login(request, user)
                    return redirect('admin_panel')
                elif hasattr(user, 'garson'):  # Garson girişi
                    login(request, user)
                    return redirect('garson_panel')
                else:
                    messages.error(request, 'Bu hesap garson veya yönetici hesabı değil.')
            else:
                messages.error(request, 'Geçersiz kullanıcı bilgileri.')
            
    return render(request, 'cafe/giris_secim.html')

def musteri_oturum(request):
    if request.method == 'POST':
        form = MusteriOturumForm(request.POST)
        if form.is_valid():
            musteri = form.save()
            request.session['masa_no'] = musteri.masa_no
            request.session['musteri_id'] = musteri.id
            request.session['sepet'] = {}
            messages.success(request, f'Masa {musteri.masa_no} için oturum açıldı.')
            return redirect('menu')
        else:
            messages.error(request, 'Lütfen tüm alanları doğru şekilde doldurun.')
    else:
        form = MusteriOturumForm()
    return render(request, 'cafe/musteri/musteri_oturum.html', {'form': form})

def menu(request):
    if 'masa_no' not in request.session:
        messages.error(request, 'Lütfen önce masa numarası girin.')
        return redirect('giris_secim')
    
    kategoriler = Kategori.objects.prefetch_related('urunler').all()
    sepet = request.session.get('sepet', {})
    sepet_urun_sayisi = sum(adet for adet in sepet.values())
    
    # Masaya ait bekleyen sipariş sayısı
    bekleyen_siparis_sayisi = Siparis.objects.filter(
        masa_no=request.session['masa_no'],
        odeme_durum='bekliyor'
    ).count()
    
    return render(request, 'cafe/musteri/menu.html', {
        'kategoriler': kategoriler,
        'masa_no': request.session['masa_no'],
        'sepet_urun_sayisi': sepet_urun_sayisi,
        'bekleyen_siparis_sayisi': bekleyen_siparis_sayisi
    })

def sepete_ekle(request):
    if request.method == 'POST':
        urun_id = request.POST.get('urun_id')
        sepet = request.session.get('sepet', {})
        
        if urun_id:
            sepet[urun_id] = sepet.get(urun_id, 0) + 1
            request.session['sepet'] = sepet
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def sepet(request):
    if 'masa_no' not in request.session:
        messages.error(request, 'Lütfen önce masa numarası girin.')
        return redirect('musteri_oturum')
    
    sepet = request.session.get('sepet', {})
    sepet_urunler = []
    toplam = 0
    
    for urun_id, adet in sepet.items():
        urun = Urun.objects.get(id=urun_id)
        toplam_fiyat = urun.fiyat * adet
        toplam += toplam_fiyat
        sepet_urunler.append({
            'id': urun.id,
            'isim': urun.isim,
            'aciklama': urun.aciklama,
            'resim': urun.resim,
            'adet': adet,
            'birim_fiyat': urun.fiyat,
            'toplam_fiyat': toplam_fiyat
        })
    
    return render(request, 'cafe/musteri/sepet.html', {
        'sepet_urunler': sepet_urunler,
        'toplam': toplam
    })

def sepet_urun_artir(request):
    if request.method == 'POST':
        urun_id = request.POST.get('urun_id')
        sepet = request.session.get('sepet', {})
        if urun_id in sepet:
            sepet[urun_id] += 1
            request.session['sepet'] = sepet
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def sepet_urun_azalt(request):
    if request.method == 'POST':
        urun_id = request.POST.get('urun_id')
        sepet = request.session.get('sepet', {})
        if urun_id in sepet:
            if sepet[urun_id] > 1:
                sepet[urun_id] -= 1
            else:
                del sepet[urun_id]
            request.session['sepet'] = sepet
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def sepet_urun_kaldir(request):
    if request.method == 'POST':
        urun_id = request.POST.get('urun_id')
        sepet = request.session.get('sepet', {})
        if urun_id in sepet:
            del sepet[urun_id]
            request.session['sepet'] = sepet
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def sepet_bosalt(request):
    if request.method == 'POST':
        request.session['sepet'] = {}
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def garson_cagir(request):
    if request.method == 'POST':
        masa_no = request.POST.get('masa_no')
        if masa_no:
            # Garson çağırma işlemi burada yapılacak
            return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def musteri_panel(request):
    return redirect('menu')

@login_required
@user_passes_test(is_admin)
def admin_panel(request):
    bekleyen_siparis = Siparis.objects.filter(durum='beklemede').count()
    tamamlanan_siparis = Siparis.objects.filter(durum='tamamlandi').count()
    aktif_masalar = Siparis.objects.filter(odeme_durum='bekliyor').values('masa_no').distinct().count()
    
    context = {
        'garson_sayisi': Garson.objects.count(),
        'urun_sayisi': Urun.objects.count(),
        'bekleyen_siparis': bekleyen_siparis,
        'tamamlanan_siparis': tamamlanan_siparis,
        'aktif_masalar': aktif_masalar
    }
    return render(request, 'cafe/admin/panel.html', context)

@login_required
@user_passes_test(is_admin)
def kategori_listesi(request):
    kategoriler = Kategori.objects.all().order_by('sira')
    return render(request, 'cafe/admin/kategori_listesi.html', {'kategoriler': kategoriler})

@login_required
@user_passes_test(is_admin)
def kategori_ekle(request):
    if request.method == 'POST':
        isim = request.POST.get('isim')
        sira = request.POST.get('sira')
        if isim and sira:
            Kategori.objects.create(isim=isim, sira=sira)
            messages.success(request, 'Kategori başarıyla eklendi.')
            return redirect('kategori_listesi')
    return render(request, 'cafe/admin/kategori_ekle.html')

@login_required
@user_passes_test(is_admin)
def urun_listesi(request):
    urunler = Urun.objects.all().select_related('kategori')
    return render(request, 'cafe/admin/urun_listesi.html', {'urunler': urunler})

@login_required
@user_passes_test(is_admin)
def urun_ekle(request):
    if request.method == 'POST':
        kategori = get_object_or_404(Kategori, id=request.POST.get('kategori'))
        isim = request.POST.get('isim')
        aciklama = request.POST.get('aciklama')
        fiyat = request.POST.get('fiyat')
        resim = request.FILES.get('resim')
        
        if isim and fiyat:
            urun = Urun.objects.create(
                kategori=kategori,
                isim=isim,
                aciklama=aciklama,
                fiyat=fiyat,
                resim=resim if resim else None
            )
            messages.success(request, 'Ürün başarıyla eklendi.')
            return redirect('urun_listesi')
    
    kategoriler = Kategori.objects.all().order_by('sira')
    return render(request, 'cafe/admin/urun_ekle.html', {'kategoriler': kategoriler})

@login_required
@user_passes_test(is_admin)
def siparisler(request):
    durum = request.GET.get('durum')
    
    siparisler = Siparis.objects.all()
    
    if durum in ['beklemede', 'hazirlaniyor', 'tamamlandi', 'iptal']:
        siparisler = siparisler.filter(durum=durum)
    
    siparisler = siparisler.prefetch_related('siparis_urunleri__urun')\
        .order_by('-olusturma_tarihi')
        
    return render(request, 'cafe/admin/siparisler.html', {
        'siparisler': siparisler,
        'secili_durum': durum
    })

@login_required
@user_passes_test(is_admin)
def siparis_durumu_guncelle(request, siparis_id):
    if request.method == 'POST':
        siparis = get_object_or_404(Siparis, id=siparis_id)
        yeni_durum = request.POST.get('durum')
        if yeni_durum in ['beklemede', 'hazirlaniyor', 'tamamlandi', 'iptal']:
            siparis.durum = yeni_durum
            # Sipariş iptal edilirse ödeme durumunu da iptal yap
            if yeni_durum == 'iptal':
                siparis.odeme_durum = 'iptal'
            siparis.save()
            messages.success(request, 'Sipariş durumu güncellendi.')
    return redirect('siparisler')

@login_required
@user_passes_test(is_garson)
def garson_panel(request):
    # Aktif masaları getir
    masalar = []
    for masa_no in range(1, 21):  # 1'den 20'ye kadar masa numaraları
        aktif_musteri = Musteri.objects.filter(
            masa_no=masa_no,
            aktif=True
        ).first()
        
        # Masaya ait bekleyen siparişleri getir
        masa_siparisler = Siparis.objects.filter(
            masa_no=masa_no,
            odeme_durum='bekliyor'
        ).prefetch_related(
            'siparis_urunleri',
            'siparis_urunleri__urun'
        ).order_by('olusturma_tarihi')
        
        # Masanın toplam tutarını hesapla
        toplam_tutar = sum(siparis.toplam_tutar for siparis in masa_siparisler)
        
        # Masanın durumunu belirle
        dolu = bool(aktif_musteri and masa_siparisler)
        
        if dolu:
            masa_data = {
                'no': masa_no,
                'dolu': True,
                'musteri': aktif_musteri.isim if aktif_musteri else None,
                'sure': aktif_musteri.oturum_baslangic.strftime('%H:%M') if aktif_musteri else None,
                'siparisler': [],
                'toplam_tutar': float(toplam_tutar)
            }
            
            # Siparişleri JSON için hazırla
            for siparis in masa_siparisler:
                siparis_data = {
                    'id': siparis.id,
                    'durum': siparis.durum,
                    'get_durum_display': siparis.get_durum_display(),
                    'olusturma_tarihi': siparis.olusturma_tarihi.strftime('%H:%M'),
                    'toplam_tutar': float(siparis.toplam_tutar),
                    'siparis_urunleri': []
                }
                
                for urun in siparis.siparis_urunleri.all():
                    siparis_data['siparis_urunleri'].append({
                        'urun': {
                            'isim': urun.urun.isim
                        },
                        'adet': urun.adet,
                        'birim_fiyat': float(urun.birim_fiyat),
                        'toplam_fiyat': float(urun.toplam_fiyat)
                    })
                
                masa_data['siparisler'].append(siparis_data)
            
            masalar.append(masa_data)
        else:
            masalar.append({
                'no': masa_no,
                'dolu': False,
                'musteri': None,
                'sure': None,
                'siparisler': [],
                'toplam_tutar': 0
            })
    
    # Aktif siparişleri getir
    siparisler = Siparis.objects.exclude(
        durum__in=['tamamlandi', 'iptal']
    ).prefetch_related(
        'siparis_urunleri',
        'siparis_urunleri__urun'
    ).order_by('olusturma_tarihi')
    
    import json
    masalar_json = json.dumps(masalar)
    
    return render(request, 'cafe/garson/panel.html', {
        'masalar': masalar,
        'siparisler': siparisler,
        'masalar_json': masalar_json
    })

@login_required
@user_passes_test(is_garson)
def siparis_durumu_guncelle(request, siparis_id):
    if request.method == 'POST':
        siparis = get_object_or_404(Siparis, id=siparis_id)
        yeni_durum = request.POST.get('durum')
        
        if yeni_durum in ['beklemede', 'hazirlaniyor', 'tamamlandi', 'iptal']:
            siparis.durum = yeni_durum
            # Sipariş iptal edilirse ödeme durumunu da iptal yap
            if yeni_durum == 'iptal':
                siparis.odeme_durum = 'iptal'
            siparis.save()
            return JsonResponse({'success': True})
            
    return JsonResponse({'success': False})

@login_required
@user_passes_test(is_admin)
def garson_listesi(request):
    garsonlar = Garson.objects.all()
    return render(request, 'cafe/admin/garson_listesi.html', {'garsonlar': garsonlar})

@login_required
@user_passes_test(is_admin)
def garson_ekle(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if username and email and password:
            user = User.objects.create_user(username=username, email=email, password=password)
            Garson.objects.create(user=user)
            messages.success(request, 'Garson başarıyla eklendi.')
            return redirect('garson_listesi')
            
    return render(request, 'cafe/admin/garson_ekle.html')

@login_required
@user_passes_test(is_admin)
def garson_sil(request, garson_id):
    garson = get_object_or_404(Garson, id=garson_id)
    user = garson.user
    user.delete()  # Garson silindiğinde ilişkili user da silinecek
    messages.success(request, 'Garson başarıyla silindi.')
    return redirect('garson_listesi')

@login_required
@user_passes_test(is_admin)
def kategori_duzenle(request, kategori_id):
    kategori = get_object_or_404(Kategori, id=kategori_id)
    if request.method == 'POST':
        isim = request.POST.get('isim')
        sira = request.POST.get('sira')
        if isim and sira:
            kategori.isim = isim
            kategori.sira = sira
            kategori.save()
            messages.success(request, 'Kategori başarıyla güncellendi.')
            return redirect('kategori_listesi')
    return render(request, 'cafe/admin/kategori_duzenle.html', {'kategori': kategori})

@login_required
@user_passes_test(is_admin)
def urun_duzenle(request, urun_id):
    urun = get_object_or_404(Urun, id=urun_id)
    if request.method == 'POST':
        kategori = get_object_or_404(Kategori, id=request.POST.get('kategori'))
        isim = request.POST.get('isim')
        aciklama = request.POST.get('aciklama')
        fiyat = request.POST.get('fiyat')
        stokta = request.POST.get('stokta') == 'on'
        
        if isim and fiyat:
            urun.kategori = kategori
            urun.isim = isim
            urun.aciklama = aciklama
            urun.fiyat = fiyat
            urun.stokta = stokta
            
            if 'resim' in request.FILES:
                urun.resim = request.FILES['resim']
            elif request.POST.get('resim_sil') == 'on':
                urun.resim = None
                
            urun.save()
            messages.success(request, 'Ürün başarıyla güncellendi.')
            return redirect('urun_listesi')
            
    kategoriler = Kategori.objects.all().order_by('sira')
    return render(request, 'cafe/admin/urun_duzenle.html', {
        'urun': urun,
        'kategoriler': kategoriler
    })

@login_required
@user_passes_test(is_admin)
def garson_duzenle(request, garson_id):
    garson = get_object_or_404(Garson, id=garson_id)
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if username and email:
            user = garson.user
            user.username = username
            user.email = email
            if password:
                user.set_password(password)
            user.save()
            messages.success(request, 'Garson bilgileri başarıyla güncellendi.')
            return redirect('garson_listesi')
            
    return render(request, 'cafe/admin/garson_duzenle.html', {'garson': garson})

def siparis_onayla(request):
    if request.method == 'POST':
        masa_no = request.session.get('masa_no')
        sepet = request.session.get('sepet', {})
        
        if not masa_no or not sepet:
            return JsonResponse({'success': False, 'error': 'Geçersiz sipariş'})
        
        # Yeni sipariş oluştur
        siparis = Siparis.objects.create(
            masa_no=masa_no,
            durum='beklemede',
            odeme_durum='bekliyor'
        )
        
        toplam_tutar = 0
        # Sepetteki ürünleri siparişe ekle
        for urun_id, adet in sepet.items():
            urun = Urun.objects.get(id=urun_id)
            SiparisUrun.objects.create(
                siparis=siparis,
                urun=urun,
                adet=adet,
                birim_fiyat=urun.fiyat
            )
            toplam_tutar += urun.fiyat * adet
        
        # Toplam tutarı güncelle
        siparis.toplam_tutar = toplam_tutar
        siparis.save()
        
        # Sepeti temizle
        request.session['sepet'] = {}
        
        return JsonResponse({'success': True, 'siparis_id': siparis.id})
    return JsonResponse({'success': False})

def odemeler(request):
    masa_no = request.session.get('masa_no')
    if not masa_no:
        messages.error(request, 'Lütfen önce masa numarası girin.')
        return redirect('giris_secim')
    
    # Masaya ait ödenmemiş siparişleri getir
    siparisler = Siparis.objects.filter(
        masa_no=masa_no,
        odeme_durum='bekliyor'
    ).prefetch_related(
        'siparis_urunleri',
        'siparis_urunleri__urun'
    ).order_by('-olusturma_tarihi')
    
    toplam_tutar = sum(siparis.toplam_tutar for siparis in siparisler)
    bekleyen_siparis_sayisi = siparisler.count()
    
    return render(request, 'cafe/musteri/odemeler.html', {
        'siparisler': siparisler,
        'toplam_tutar': toplam_tutar,
        'bekleyen_siparis_sayisi': bekleyen_siparis_sayisi
    })

def odeme_yap(request):
    if request.method == 'POST':
        # Seçili siparişleri ödenmiş olarak işaretle
        siparis_ids_str = request.POST.get('siparis_ids[]', '')
        siparis_ids = siparis_ids_str.split(',')
        
        if siparis_ids:
            # Önce tüm siparişlerin tamamlandı durumunda olduğunu kontrol et
            tamamlanmamis_siparis = Siparis.objects.filter(
                id__in=siparis_ids
            ).exclude(durum='tamamlandi').exists()
            
            if tamamlanmamis_siparis:
                return JsonResponse({
                    'success': False, 
                    'error': 'Tamamlanmamış siparişler için ödeme yapılamaz.'
                })
            
            # Siparişleri bul ve masa numarasını al
            ilk_siparis = Siparis.objects.filter(id=siparis_ids[0]).first()
            if not ilk_siparis:
                return JsonResponse({'success': False, 'error': 'Sipariş bulunamadı'})
            
            masa_no = ilk_siparis.masa_no
            
            # Tüm siparişler tamamlandıysa ödemeyi gerçekleştir
            Siparis.objects.filter(
                id__in=siparis_ids,
                masa_no=masa_no
            ).update(
                odeme_durum='odendi',
                odeme_tarihi=timezone.now()
            )
            
            # Masaya ait bekleyen başka sipariş var mı kontrol et
            bekleyen_siparis = Siparis.objects.filter(
                masa_no=masa_no,
                odeme_durum='bekliyor'
            ).exists()
            
            # Bekleyen sipariş yoksa masayı ve müşteriyi kapat
            if not bekleyen_siparis:
                # Aktif müşteriyi bul
                musteri = Musteri.objects.filter(
                    masa_no=masa_no,
                    aktif=True
                ).first()
                
                if musteri:
                    # Müşteriyi pasif yap
                    musteri.aktif = False
                    musteri.save()
                    
                    # Müşterinin session'ını bul ve sil
                    from django.contrib.sessions.models import Session
                    for session in Session.objects.all():
                        session_data = session.get_decoded()
                        if session_data.get('musteri_id') == musteri.id:
                            session.delete()
            
            return JsonResponse({'success': True})
            
    return JsonResponse({'success': False, 'error': 'Geçersiz istek'})

def masa_kapat(request):
    if request.method == 'POST':
        masa_no = request.session.get('masa_no')
        musteri_id = request.session.get('musteri_id')
        
        if not masa_no:
            return JsonResponse({'success': False, 'error': 'Geçersiz masa'})
        
        # Masada bekleyen sipariş var mı kontrol et
        bekleyen_siparis = Siparis.objects.filter(
            masa_no=masa_no,
            odeme_durum='bekliyor'
        ).exists()
        
        if bekleyen_siparis:
            return JsonResponse({
                'success': False,
                'error': 'Bekleyen siparişler olduğu için masa kapatılamaz.'
            })
        
        # Müşteri kaydını pasif yap
        if musteri_id:
            Musteri.objects.filter(id=musteri_id).update(aktif=False)
        
        # Oturumu sonlandır
        request.session.flush()
        return JsonResponse({
            'success': True,
            'redirect': True,
            'redirect_url': '/'
        })
        
    return JsonResponse({'success': False})

def garson_cikis(request):
    logout(request)
    return redirect('giris_secim')
