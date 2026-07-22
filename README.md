# QRIS Quantum Threat Demo 🔐⚛️

Demo interaktif simulasi serangan **Man-in-the-Middle + Quantum Forge** terhadap sistem QRIS Dinamis berbasis RSA, untuk keperluan awareness **Post-Quantum Cryptography (PQC)**.

## Cara Menjalankan

```bash
# Install dependensi (sekali saja)
pip3 install flask qrcode Pillow sympy

# Jalankan aplikasi
python3 app.py
```

Buka browser dan akses:
- **Dashboard** : https://0.0.0.0:5050
- **Kasir**     : https://0.0.0.0:5050/kasir
- **Attacker**  : https://0.0.0.0:5050/attacker
- **M-Banking** : https://0.0.0.0:5050/mbanking

> ⚠️ **Self-signed certificate**: Browser akan menampilkan warning "Not Secure".
> Klik **Advanced → Proceed** (Chrome/Android) atau **Show Details → visit this website** (Safari iOS).
> Untuk Safari iOS agar kamera bisa digunakan, akses via IP komputer (contoh: `https://192.168.x.x:5050/mbanking`).

## Alur Demo (Step by Step)

### Tab Kasir
1. Klik **"Generate Keypair RSA Bank"** — lihat n, e, d, p, q
2. Masukkan nominal (contoh: 150.000) lalu klik **"Generate QRIS"**
3. QR Code muncul di layar kasir

### Tab Attacker (buka di tab baru)
1. Klik **"Intercept QRIS (The Harvest)"** — paket QRIS dicuri
2. Klik **"Simulate Shor's Algorithm"** — kunci privat bocor dalam ~1ms
3. Klik **"Forge QRIS Palsu"** — QR Code di kasir otomatis diganti

### Tab Kasir (refresh)
- QR Code sekarang menampilkan versi PALSU dari penyerang (ada label merah)

### Tab M-Banking
1. Klik **"Scan QRIS dari Kasir"** — verifikasi RSA berjalan
2. Lihat hasil: **"KONEKSI AMAN & VALID"** — padahal QRIS sudah dipalsukan!
3. Klik **"Konfirmasi Bayar"** — dana mengalir ke rekening penipu

## Struktur File

```
├── app.py              # Backend Flask + logika RSA + API
├── requirements.txt    # Dependensi Python
└── templates/
    ├── base.html       # Layout + tema Livin Mandiri
    ├── index.html      # Dashboard + flow diagram
    ├── kasir.html      # Entitas 1: Server Bank & Kasir
    ├── attacker.html   # Entitas 2: MitM Attacker
    └── mbanking.html   # Entitas 3: M-Banking Customer
```
