"""
main.py - Ana Döngü ve Terminal Ekranı (Modül 5)
================================================

Bu dosya projenin "orkestra şefi"dir. Kendisi veri toplamaz veya veritabanına
doğrudan SQL yazmaz. Diğer modülleri doğru sırayla çağırır:

    1) interface_collector -> verileri topla (dict)
    2) db_manager          -> dict'i SQLite'a kaydet
    3) Ekrana canlı özet bas
    4) Belirlenen süre kadar bekle ve başa dön

Çalıştırma:   python main.py
Durdurma:     Ctrl + C

Hafta 1 kapsamı: 5 değişkenin her saniye toplanıp kaydedilmesi.
"""

import os    # Terminal ekranını temizlemek için (cls / clear komutu)
import time  # Döngü aralığındaki bekleme (sleep) ve süre ölçümü için

import db_manager
import interface_collector


# ---------------------------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------------------------

# İki ölçüm arasındaki süre (saniye). Ödev gereksinimi: her saniye ölçüm.
INTERVAL_SECONDS = 1.0

# Ekrandaki tablonun genişliği (karakter sayısı)
SCREEN_WIDTH = 56


# ---------------------------------------------------------------------------
# EKRAN FONKSİYONLARI
# ---------------------------------------------------------------------------

def clear_screen():
    """
    Terminal ekranını temizler. Böylece tablo her saniye aynı yerde güncellenir
    ve alt alta kayan yazılar yerine "canlı" bir görünüm elde edilir.

    os.name değeri Windows'ta "nt", Linux/macOS'ta "posix" olur.
    Windows'ta temizleme komutu "cls", diğerlerinde "clear"dır.
    """
    os.system("cls" if os.name == "nt" else "clear")


def display_summary(data, cycle, total_records):
    """
    Son ölçümü terminalde hizalı bir tablo halinde gösterir.

    Parametreler:
        data (dict)        : Son toplanan ölçüm verileri
        cycle (int)        : Program açıldığından beri kaçıncı ölçüm döngüsü
        total_records (int): Veritabanındaki toplam kayıt sayısı

    Biçimlendirme notu: f"{metin:<22}" metni 22 karakterlik alana sola yaslar.
    Bu sayede değerler alt alta düzgün bir sütun oluşturur.
    """
    clear_screen()
    print("=" * SCREEN_WIDTH)
    print("  AĞ İZLEME SİSTEMİ (Network Monitor) - Hafta 1".center(SCREEN_WIDTH))
    print("=" * SCREEN_WIDTH)

    # (Ekranda görünecek etiket, veri sözlüğündeki anahtar) çiftleri.
    # Yeni haftalarda bu listeye satır eklemek yeterli olacak.
    rows = [
        ("Zaman Damgası",    "timestamp"),
        ("Arayüz Adı",       "interface_name"),
        ("Arayüz Durumu",    "interface_status"),
        ("IPv4 Adresi",      "ipv4_address"),
        ("MAC Adresi",       "mac_address"),
    ]
    for label, key in rows:
        value = data.get(key)
        # None değerleri ekranda "-" olarak göster (daha okunaklı)
        print(f"  {label:<22}: {value if value is not None else '-'}")

    print("-" * SCREEN_WIDTH)
    print(f"  {'Ölçüm Döngüsü':<22}: {cycle}")
    print(f"  {'Veritabanı Kayıt':<22}: {total_records}  ({db_manager.DB_FILE})")
    print("-" * SCREEN_WIDTH)
    print("  Durdurmak için Ctrl + C".center(SCREEN_WIDTH))


# ---------------------------------------------------------------------------
# ANA DÖNGÜ
# ---------------------------------------------------------------------------

def run(max_cycles=None):
    """
    İzleme döngüsünü başlatır.

    Parametre:
        max_cycles (int veya None): Kaç ölçüm yapılacağı. None ise sonsuza kadar
            (Ctrl+C'ye basılana kadar) çalışır. Test için sınırlı sayı verilebilir.

    Hata yönetimi (try-except) iki katmanlıdır:
      - İÇ katman: Tek bir ölçümde oluşan hata (ör. ağ kartı o an kapandı) programı
        çökertmez. Hata ekrana yazılır ve bir sonraki döngüye geçilir.
      - DIŞ katman: Kullanıcı Ctrl+C'ye bastığında Python KeyboardInterrupt
        istisnası fırlatır. Bunu yakalayıp programı düzgün bir mesajla kapatırız.
    """
    # Program başlarken tabloyu hazırla (yoksa oluştur, eksik sütunları ekle)
    db_manager.initialize_database()

    cycle = 0
    try:
        while max_cycles is None or cycle < max_cycles:
            # Döngünün başladığı an. time.monotonic() sistem saati değiştirilse
            # bile geriye gitmeyen bir sayaçtır; süre ölçümü için en güvenilir yöntemdir.
            loop_start = time.monotonic()
            cycle += 1

            try:
                # 1) Topla
                data = interface_collector.collect_interface_data()
                # 2) Kaydet
                db_manager.insert_metrics(data)
                # 3) Göster
                display_summary(data, cycle, db_manager.count_records())
            except Exception as error:
                # Beklenmeyen bir hata olursa program durmaz, sadece bildirir.
                print(f"[HATA] Döngü {cycle} sırasında hata oluştu: {error}")

            # 4) Bekle: Toplama + kaydetme işlemi de zaman aldığı için sabit 1 sn
            #    beklemek yerine kalan süre kadar bekliyoruz. Böylece ölçümler
            #    gerçekten ~1 saniye aralıklarla yapılır (zaman kayması önlenir).
            elapsed = time.monotonic() - loop_start
            time.sleep(max(0.0, INTERVAL_SECONDS - elapsed))

    except KeyboardInterrupt:
        # Ctrl+C basıldı: düzgün çıkış
        print("\n[BİLGİ] İzleme kullanıcı tarafından durduruldu.")

    print(f"[BİLGİ] Toplam {cycle} ölçüm yapıldı. "
          f"Veriler '{db_manager.DB_FILE}' dosyasına kaydedildi.")


# Dosya doğrudan çalıştırıldığında ana döngüyü başlat.
# (Başka bir dosyadan "import main" yapılırsa otomatik başlamaz.)
if __name__ == "__main__":
    run()
