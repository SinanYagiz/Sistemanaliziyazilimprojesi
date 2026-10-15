"""
interface_collector.py - Ağ Arayüzü ve Sistem Toplayıcısı (Modül 2)
===================================================================

Bu modülün TEK sorumluluğu: İşletim sisteminden ağ arayüzü bilgilerini okumak
ve bir sözlük (dict) olarak döndürmek. Veritabanını bilmez, ekrana tablo basmaz.

Kullanılan kütüphaneler:
  - psutil  : İşletim sisteminden ağ kartı, CPU, bellek gibi bilgileri okur.
              Windows, Linux ve macOS'ta aynı kodla çalışır (platform bağımsız).
  - socket  : İnternete çıkışta hangi yerel IP'nin kullanıldığını bulmak için.
  - datetime: Ölçüm zaman damgasını üretmek için.

Hafta 1 kapsamı (5 değişken):
  timestamp, interface_name, interface_status, ipv4_address, mac_address
"""

import socket
from datetime import datetime

import psutil  # Harici kütüphane: pip install psutil


# ---------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------------------------

def get_timestamp():
    """
    (23) timestamp: Şu anki tarih ve saati "YYYY-MM-DD HH:MM:SS" biçiminde döndürür.

    strftime biçim kodları:
      %Y = 4 haneli yıl, %m = ay, %d = gün, %H = saat (24 saat), %M = dakika, %S = saniye

    Bu biçim SQLite'ta metin olarak saklandığında alfabetik sıralama ile
    zamansal sıralama aynı sonucu verir. Bu yüzden ORDER BY timestamp doğru çalışır.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_default_local_ip():
    """
    Bilgisayarın internete çıkarken kullandığı yerel IPv4 adresini bulur.

    Yöntem (UDP "connect" hilesi):
      - Bir UDP soketi açılır ve 8.8.8.8 adresine "connect" yapılır.
      - UDP bağlantısız (connectionless) bir protokoldür. connect() çağrısı ağa
        HİÇBİR PAKET GÖNDERMEZ; işletim sistemi sadece yönlendirme tablosuna bakıp
        bu hedefe hangi yerel IP üzerinden gidileceğine karar verir.
      - getsockname() bu kararı, yani kullanılan yerel IP'yi döndürür.

    Neden gerekli? Bilgisayarda birden fazla arayüz olabilir (Wi-Fi, Ethernet,
    VirtualBox, VPN...). Bu yöntemle "asıl internete çıkan" arayüzü buluruz.

    Döndürür:
        str veya None: Ör. "192.168.1.35". İnternet/ağ yoksa None.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # AF_INET=IPv4, SOCK_DGRAM=UDP
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]  # (ip, port) demetinin ilk elemanı = IP
    except OSError:
        return None  # Ağ bağlantısı yoksa hata oluşur; None döndürüyoruz
    finally:
        sock.close()  # Hata olsa da olmasa da soketi kapat (kaynak sızıntısını önler)


def find_active_interface():
    """
    İzlenecek ağ arayüzünün adını seçer.

    Seçim sırası:
      1) IPv4 adresi, get_default_local_ip() ile eşleşen arayüz (internete çıkan arayüz).
      2) Bulunamazsa: durumu UP olan, IPv4 adresi olan ve loopback olmayan ilk arayüz.
      3) O da yoksa: None.

    psutil fonksiyonları:
      - net_if_addrs(): {arayüz_adı: [adres listesi]} döndürür. Her adresin
        family (tür), address (adres), netmask gibi alanları vardır.
      - net_if_stats(): {arayüz_adı: istatistik} döndürür. isup alanı arayüzün
        açık olup olmadığını gösterir.

    Loopback nedir? 127.0.0.1 adresli sanal arayüzdür. Bilgisayar kendi kendine
    veri gönderir; gerçek ağ trafiğini temsil etmediği için izlemeye almıyoruz.
    """
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    default_ip = get_default_local_ip()

    # 1. öncelik: internete çıkan IP'ye sahip arayüz
    if default_ip:
        for name, addr_list in addrs.items():
            for addr in addr_list:
                if addr.family == socket.AF_INET and addr.address == default_ip:
                    return name

    # 2. öncelik (yedek yöntem): UP + IPv4 sahibi + loopback değil
    for name, addr_list in addrs.items():
        is_up = name in stats and stats[name].isup
        for addr in addr_list:
            if (is_up
                    and addr.family == socket.AF_INET
                    and not addr.address.startswith("127.")):
                return name

    return None


# ---------------------------------------------------------------------------
# ANA TOPLAMA FONKSİYONU
# ---------------------------------------------------------------------------

def collect_interface_data(interface_name=None):
    """
    Seçilen ağ arayüzünün Hafta 1 değişkenlerini toplar.

    Parametre:
        interface_name (str, isteğe bağlı): İzlenecek arayüz. Verilmezse
            find_active_interface() ile otomatik seçilir.

    Döndürür:
        dict: db_manager.SCHEMA ile aynı anahtarlara sahip sözlük.
              Bulunamayan değerler None olur (veritabanına NULL yazılır).
    """
    if interface_name is None:
        interface_name = find_active_interface()

    # Varsayılan değerler: bir bilgi okunamazsa None kalır.
    data = {
        "timestamp": get_timestamp(),
        "interface_name": interface_name,
        "interface_status": "DOWN",
        "ipv4_address": None,
        "mac_address": None,
    }

    # Hiç uygun arayüz yoksa (ör. tüm ağ kartları kapalı) mevcut haliyle döndür.
    if interface_name is None:
        return data

    # (2) interface_status: net_if_stats() içindeki isup alanı True ise "UP"
    stats = psutil.net_if_stats()
    if interface_name in stats and stats[interface_name].isup:
        data["interface_status"] = "UP"

    # Arayüzün adres listesini dolaşıp türüne göre ilgili alana yerleştiriyoruz.
    # Bir arayüzün birden fazla adresi olabilir (IPv4, IPv6, MAC).
    for addr in psutil.net_if_addrs().get(interface_name, []):
        # (3) ipv4_address: family == AF_INET olan adres
        if addr.family == socket.AF_INET and data["ipv4_address"] is None:
            data["ipv4_address"] = addr.address

        # (5) mac_address: family == psutil.AF_LINK olan adres.
        #     AF_LINK, psutil'in "fiziksel katman (Katman 2) adresi" için kullandığı sabittir.
        #     Windows MAC adresini "A4-B1-C2-D3-E4-F5" biçiminde verir; Linux ise ":" kullanır.
        #     Tutarlılık için "-" işaretlerini ":" ile değiştirip büyük harfe çeviriyoruz.
        elif addr.family == psutil.AF_LINK:
            data["mac_address"] = addr.address.replace("-", ":").upper()

    return data


# ---------------------------------------------------------------------------
# MODÜL TESTİ:  python interface_collector.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== interface_collector.py modül testi ===")
    print(f"İnternete çıkan yerel IP : {get_default_local_ip()}")
    print(f"Seçilen arayüz           : {find_active_interface()}")
    print("-" * 45)
    for key, value in collect_interface_data().items():
        # :<18 -> anahtarı 18 karakterlik alana sola yaslayarak yazar (hizalı görünüm)
        print(f"{key:<18}: {value}")
