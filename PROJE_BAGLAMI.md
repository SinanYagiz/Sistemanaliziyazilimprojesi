# PROJE BAĞLAMI: Python ile Ağ İzleme (Network Monitoring)

> **Bu dosya yapay zeka asistanları için hazırlanmıştır.** Bu projede çalışmaya başlamadan önce dosyanın tamamını oku ve buradaki kurallara uy. Her hafta sonunda **"Güncel Durum"** bölümünü güncelle.

---

## 1. Proje Özeti
- **Ne:** Üniversite *Sistem Analizi ve Tasarımı* dersi vize ödevi. Terminal (CLI) tabanlı bir ağ izleme programı.
- **İşlev:** Her saniye ağ ve sistem değişkenlerini toplar, SQLite'a (`network_monitor.db`) kaydeder ve terminalde canlı özet tablo gösterir. Verileri CSV'ye de aktarabilir.
- **Dil ve kütüphaneler:** Python 3.12, `psutil` (tek harici bağımlılık), `socket`, `subprocess`, `time`, `datetime`, `sqlite3`, `csv`, `os`.
- **Platform:** Windows (Türkçe dil ayarı). Kod platformdan bağımsız yazılmalıdır.
- **GUI YOK.** Sadece terminal.

## 2. ⚠️ Kesin Çalışma Kuralları
Ödev kuralları gereği yapay zekanın projeyi tek seferde yazması **yasaktır**.

1. **Hiçbir zaman tüm kodu tek yanıtta yazma.** Her yanıtta yalnızca **tek bir modül veya mantık bloğu** üret.
2. Her adımın başında **"📌 Rapora Eklenecek Öğrenci Promptu"** başlığı altında, öğrencinin bu modülü istemek için yazmış olabileceği profesyonel bir prompt metni ver.
3. Bu promptu [`docs/yapay_zeka_kullanim_gunlugu.txt`](docs/yapay_zeka_kullanim_gunlugu.txt) dosyasına ilgili haftanın altına ekle. Biçim: `[Hafta N - Modül X] Başlık` + `Üretilen dosya:` satırı.
4. Kodda her fonksiyonu, değişkeni ve hesaplama yöntemini **çok detaylı Türkçe yorum ve docstring** ile açıkla. Öğrenci sözlü sınavda bu kodu anlatacak.
5. Her adımın sonunda dur ve sor: **"Bu modülü test ettin mi? Bir sonraki adıma geçelim mi?"** Onay gelmeden devam etme.
6. Her hafta **sadece 5 değişken** eklenir. Gelecek haftaların değişkenlerini önceden ekleme.
7. Yanıtlar Türkçe olmalıdır. Her modülün sonunda bir **"💡 Sözlü sınav için"** notu ekle.

## 3. Mimari
```
sistemanaliziyazilim/
├── main.py                  # Orkestratör: topla → kaydet → göster → bekle (1 sn)
├── db_manager.py            # SQLite: tablo, otomatik migration, INSERT, (CSV)
├── interface_collector.py   # psutil: arayüz (A) + sistem (E) değişkenleri
├── network_tester.py        # (Hafta 4) ping, kayıp, jitter, DNS, bağlantılar
├── rate_calculator.py       # (Hafta 3) iki ölçüm farkından hız hesapları
├── requirements.txt         # psutil
├── PROJE_BAGLAMI.md         # Bu dosya
├── docs/
│   └── yapay_zeka_kullanim_gunlugu.txt   # Rapor için prompt günlüğü
└── network_monitor.db       # Çalışınca oluşur (git'e eklenmemeli)
```

**Tasarım kuralları:**
- Toplayıcı modüller yalnızca bir `dict` döndürür. Veritabanını veya ekranı bilmezler. Modülleri sadece `main.py` birleştirir (gevşek bağlılık).
- Dict anahtarları `db_manager.SCHEMA` içindeki sütun adlarıyla **birebir aynı** olmalıdır.
- **Tek tablo:** `network_metrics` (`id INTEGER PRIMARY KEY AUTOINCREMENT` + ölçüm sütunları).
- **Migration:** Yeni sütun eklemek için sadece `db_manager.SCHEMA` sözlüğüne satır eklenir. `initialize_database()`, `PRAGMA table_info` ile eksik sütunları bulup `ALTER TABLE ADD COLUMN` ile ekler. Eski veriler korunur.
- `insert_metrics()` parametreli sorgu (`?`) kullanır.
- Her modülün sonunda bir `if __name__ == "__main__":` test bloğu bulunur.
- `main.run(max_cycles=N)` ile sınırlı test yapılabilir. Bekleme süresi `time.monotonic()` ile ölçülür ve işlem süresi düşülür.
- Yeni değişkenler ekranda görünsün diye `main.display_summary()` içindeki `rows` listesine eklenir.
- Arayüz seçimi: UDP connect yöntemiyle (8.8.8.8) internete çıkan yerel IP bulunur, bu IP'ye sahip arayüz seçilir. Yedek kural: UP + IPv4 sahibi + loopback olmayan ilk arayüz.
- MAC biçimi: `AA:BB:CC:DD:EE:FF` (büyük harf, `:` ayraçlı).

## 4. 25 Değişken ve Haftalık Plan

| Hafta | Tema | Değişkenler | Dosyalar | Durum |
|---|---|---|---|---|
| 1 | Temel iskelet | `timestamp`, `interface_name`, `interface_status`, `ipv4_address`, `mac_address` | db_manager, interface_collector, main | ✅ Tamamlandı |
| 2 | Kümülatif sayaçlar | `bytes_received`, `bytes_sent`, `packets_received`, `packets_sent`, `incoming_errors` | interface_collector genişler, db_manager'a **CSV aktarımı** eklenir | ⏳ Sıradaki |
| 3 | Trafik hızı | `download_rate_mbps`, `upload_rate_mbps`, `incoming_packet_rate_pps`, `avg_packet_size_bytes`, `dropped_packets` | `rate_calculator.py` (yeni) | ⬜ |
| 4 | Performans testleri | `ping_latency_ms`, `packet_loss_pct`, `jitter_ms`, `dns_resolution_ms`, `active_connections` | `network_tester.py` (yeni) | ⬜ |
| 5 | Tamamlama | `listening_ports`, `ipv6_address`, `interface_speed_mbps`, `cpu_utilization_pct`, `memory_usage_mb` | Son terminal tablosu + akademik dokümantasyon (SWOT, BPMN, DFD Mermaid, ERD, sözlü sınav soru-cevap anahtarı) | ⬜ |

### Değişken tanımları ve hesaplama yöntemleri
| Değişken | Tip | Kaynak / Formül |
|---|---|---|
| `timestamp` | TEXT | `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` |
| `interface_name` | TEXT | Seçilen arayüz adı (ör. `Wi-Fi`) |
| `interface_status` | TEXT | `net_if_stats()[ad].isup` → `"UP"` / `"DOWN"` |
| `ipv4_address` | TEXT | `net_if_addrs()` içinde `AF_INET` |
| `ipv6_address` | TEXT | `AF_INET6` (yoksa NULL) |
| `mac_address` | TEXT | `psutil.AF_LINK` |
| `interface_speed_mbps` | REAL | `net_if_stats()[ad].speed` (Wi-Fi'de 0 olabilir) |
| `bytes_received` / `bytes_sent` | INTEGER | `net_io_counters(pernic=True)[ad].bytes_recv / bytes_sent` |
| `packets_received` / `packets_sent` | INTEGER | `.packets_recv / .packets_sent` |
| `incoming_errors` | INTEGER | `.errin` |
| `dropped_packets` | INTEGER | `.dropin + .dropout` |
| `ping_latency_ms` | REAL | `subprocess` ile `ping 8.8.8.8` (4 paket), ortalama RTT |
| `packet_loss_pct` | REAL | (kayıp / gönderilen) × 100 |
| `jitter_ms` | REAL | Ardışık RTT farklarının mutlak değerlerinin ortalaması |
| `dns_resolution_ms` | REAL | `socket.gethostbyname("google.com")` süresi |
| `active_connections` | INTEGER | `net_connections()` içinde `ESTABLISHED` sayısı |
| `listening_ports` | INTEGER | `LISTEN` sayısı |
| `download_rate_mbps` | REAL | (Δbytes_recv × 8) / Δt / 1 000 000 |
| `upload_rate_mbps` | REAL | (Δbytes_sent × 8) / Δt / 1 000 000 |
| `incoming_packet_rate_pps` | REAL | Δpackets_recv / Δt |
| `avg_packet_size_bytes` | REAL | (Δbytes_recv + Δbytes_sent) / (Δpackets_recv + Δpackets_sent); payda 0 ise 0 |
| `cpu_utilization_pct` | REAL | `psutil.cpu_percent()` |
| `memory_usage_mb` | REAL | Karar Hafta 5'te verilecek: sistem RAM'i mi, sürecin RAM'i mi |

## 5. Bilinen Teknik Notlar
- **Ping çıktısı** Windows'ta Türkçe olabilir (`süre=12ms`, `Ortalama`). Dile bağlı kelimeler yerine regex ile `(süre|time)[=<](\d+)` gibi sayısal kalıplar yakalanmalı. Windows'ta `-n`, Linux/macOS'ta `-c` parametresi kullanılır.
- **Ping/DNS yavaştır** (1–3 sn). Her döngüde değil, örneğin **her 5 döngüde bir** ölçülmeli. Aradaki kayıtlara son ölçülen değer yazılmalı.
- `psutil.net_connections()` macOS'ta yönetici yetkisi gerektirebilir. Windows'ta genelde sorun çıkmaz. `AccessDenied` hatası yakalanmalı.
- Sayaçlar sıfırlanabilir (ör. arayüz yeniden başlatılırsa). Bu durumda Δ < 0 olur ve hız 0 kabul edilmeli.
- Terminal çıktısında kutu çizim karakterleri yerine `=` ve `-` kullanılıyor (kodlama sorunlarını önlemek için).
- Gereksinim belgesinde A kategorisi "9 adet" yazıyor ama aslında 12 değişken var. Toplam yine 25 ediyor.

## 6. Güncel Durum
- **Son tamamlanan:** Hafta 1 (3 modül yazıldı ve test edildi).
- **Sıradaki adım:** Hafta 2 → Modül 1: `interface_collector.py`'ye 5 kümülatif sayacın eklenmesi. Ardından `db_manager.py`'ye `SCHEMA` güncellemesi ve `export_to_csv()` fonksiyonu, son olarak `main.py`'de `rows` listesinin güncellenmesi.
- **Açık kararlar:** `memory_usage_mb` kapsamı (Hafta 5).
- **Öneri:** Her hafta sonunda git commit atılsın (ör. `Hafta 2: kumulatif sayaclar`).
