"""
db_manager.py - Veritabanı Katmanı (Modül 1)
=============================================

Bu modülün TEK sorumluluğu: SQLite veritabanı ile konuşmaktır.
  - Tabloyu oluşturur.
  - Haftalar ilerledikçe eksik sütunları otomatik ekler (şema genişletme / migration).
  - Toplanan ölçüm verilerini tabloya kaydeder (INSERT).

Diğer modüller (veri toplayıcılar) veritabanını hiç bilmez; sadece bir sözlük (dict)
üretirler. Bu sözlüğü veritabanına yazmak bu modülün işidir. Buna "katmanlı mimari"
denir: veri toplama katmanı ile veri saklama katmanı birbirinden ayrıdır.

Hafta 1 kapsamı: 5 sütun
  timestamp, interface_name, interface_status, ipv4_address, mac_address
"""

import sqlite3  # Python'un standart kütüphanesindeki SQLite sürücüsü (ek kurulum gerekmez)

# ---------------------------------------------------------------------------
# SABİTLER (Sabit değerler büyük harfle yazılır - Python geleneği / PEP 8)
# ---------------------------------------------------------------------------

# Veritabanı dosyasının adı. SQLite tek bir dosyada çalışır; sunucu gerektirmez.
# Dosya yoksa sqlite3.connect() onu otomatik olarak oluşturur.
DB_FILE = "network_monitor.db"

# Ölçümlerin saklanacağı tablonun adı.
TABLE_NAME = "network_metrics"

# Tablo şeması: {sütun_adı: SQLite_veri_tipi}
# Her hafta yeni değişkenler BU SÖZLÜĞE eklenecek. Başka hiçbir yeri değiştirmeye
# gerek kalmayacak; migration fonksiyonu eksik sütunları kendisi ekleyecek.
#
# SQLite veri tipleri:
#   TEXT    -> metin (string)
#   INTEGER -> tam sayı
#   REAL    -> ondalıklı sayı (float)
SCHEMA = {
    # --- Hafta 1 değişkenleri ---
    "timestamp":        "TEXT",  # (23) Ölçüm zamanı, "YYYY-MM-DD HH:MM:SS" biçiminde
    "interface_name":   "TEXT",  # (1)  Ağ arayüzünün adı, ör. "Wi-Fi", "Ethernet"
    "interface_status": "TEXT",  # (2)  Arayüz durumu: "UP" (açık) veya "DOWN" (kapalı)
    "ipv4_address":     "TEXT",  # (3)  Yerel IPv4 adresi, ör. "192.168.1.35"
    "mac_address":      "TEXT",  # (5)  Fiziksel (donanım) adresi, ör. "A4-B1-C2-..."
}


# ---------------------------------------------------------------------------
# FONKSİYONLAR
# ---------------------------------------------------------------------------

def get_connection(db_file=DB_FILE):
    """
    Veritabanına bir bağlantı (connection) açar ve döndürür.

    Parametre:
        db_file (str): Veritabanı dosyasının yolu. Varsayılan: network_monitor.db

    Döndürür:
        sqlite3.Connection: Açık veritabanı bağlantısı.

    Not: Bağlantıyı kullanan kod, işi bitince bağlantıyı kapatmalıdır (conn.close()).
    """
    return sqlite3.connect(db_file)


def initialize_database(db_file=DB_FILE):
    """
    Veritabanını kullanıma hazırlar. Program her açıldığında bir kez çağrılır.

    Yaptığı iki iş:
      1) Tablo yoksa, sadece 'id' sütunuyla tabloyu oluşturur.
      2) SCHEMA sözlüğünde olup tabloda olmayan sütunları ALTER TABLE ile ekler.

    Neden böyle? Proje haftalık geliştiriliyor. Geçen hafta 5 sütunlu tablo
    oluşturulduysa, bu hafta yeni 5 sütun eklendiğinde tabloyu silip yeniden
    oluşturmak eski verileri kaybettirir. Bu yöntemle eski veriler korunur,
    eski satırlarda yeni sütunların değeri NULL (boş) olur.
    """
    conn = get_connection(db_file)
    cursor = conn.cursor()  # cursor: SQL komutlarını çalıştıran nesne

    # 1) Tabloyu oluştur. "IF NOT EXISTS" sayesinde tablo zaten varsa hata vermez.
    #    id: Her satıra otomatik artan benzersiz numara verir (birincil anahtar, PK).
    #    Bu sütun 25 ölçüm değişkenine dahil değildir; sadece kayıtları ayırt eder.
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    # 2) Tabloda şu an hangi sütunlar var? Bunu öğrenmek için PRAGMA table_info kullanılır.
    #    Her satır şu yapıdadır: (sıra_no, sütun_adı, tip, notnull, varsayılan, pk)
    #    row[1] sütun adını verir. Hızlı arama için bir küme (set) içinde topluyoruz.
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # 3) SCHEMA'daki her sütun için: tabloda yoksa ekle.
    for column_name, column_type in SCHEMA.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column_name} {column_type}"
            )
            print(f"[DB] Yeni sütun eklendi: {column_name} ({column_type})")

    conn.commit()  # Değişiklikleri kalıcı olarak diske yaz
    conn.close()   # Bağlantıyı kapat


def insert_metrics(data, db_file=DB_FILE):
    """
    Bir ölçüm döngüsünde toplanan verileri tabloya tek satır olarak ekler.

    Parametre:
        data (dict): {sütun_adı: değer} sözlüğü.
                     Ör: {"timestamp": "2026-10-15 12:50:00", "interface_name": "Wi-Fi", ...}

    Çalışma mantığı:
      - Sadece SCHEMA'da tanımlı anahtarlar alınır. Sözlükte fazladan bir anahtar
        varsa yok sayılır; böylece hatalı bir sütun adı SQL hatasına yol açmaz.
      - Sözlükte olmayan sütunlar NULL olarak kaydedilir.

    Güvenlik (SQL Injection önlemi):
      Değerler SQL metninin içine doğrudan yazılmaz. Bunun yerine "?" yer tutucuları
      kullanılır ve değerler ayrı bir liste olarak verilir. SQLite bu değerleri
      güvenli şekilde yerleştirir (parametreli sorgu).
    """
    # SCHEMA sırasına göre sütun adları ve karşılık gelen değerler
    columns = list(SCHEMA.keys())
    values = [data.get(col) for col in columns]  # .get(): anahtar yoksa None (NULL) döner

    # Örnek sonuç: "timestamp, interface_name, interface_status, ipv4_address, mac_address"
    column_list = ", ".join(columns)
    # Sütun sayısı kadar "?" üretir. Örnek sonuç: "?, ?, ?, ?, ?"
    placeholders = ", ".join(["?"] * len(columns))

    sql = f"INSERT INTO {TABLE_NAME} ({column_list}) VALUES ({placeholders})"

    conn = get_connection(db_file)
    conn.execute(sql, values)
    conn.commit()
    conn.close()


def count_records(db_file=DB_FILE):
    """
    Tablodaki toplam kayıt (satır) sayısını döndürür.
    Terminal ekranında "Kaydedilen ölçüm sayısı" bilgisini göstermek için kullanılır.
    """
    conn = get_connection(db_file)
    # COUNT(*): tablodaki satırları sayar. fetchone() tek satırı (tuple) döndürür, [0] ilk değerdir.
    total = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    conn.close()
    return total


# ---------------------------------------------------------------------------
# MODÜL TESTİ
# Bu blok sadece dosya doğrudan çalıştırıldığında devreye girer:
#     python db_manager.py
# Başka bir dosya "import db_manager" yaptığında bu kısım ÇALIŞMAZ.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import datetime

    print("=== db_manager.py modül testi ===")
    initialize_database()

    # Örnek (sahte) bir ölçüm satırı. Gerçek veriler Modül 2'den gelecek.
    sample = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "interface_name": "Test-Arayuzu",
        "interface_status": "UP",
        "ipv4_address": "192.168.1.100",
        "mac_address": "AA-BB-CC-DD-EE-FF",
    }
    insert_metrics(sample)

    print(f"Örnek kayıt eklendi. Toplam kayıt sayısı: {count_records()}")
