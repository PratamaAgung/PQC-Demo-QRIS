"""
QRIS Quantum Threat Demo - Main Flask Application
Simulasi arsitektur Man-in-the-Middle & Quantum Forge
untuk awareness Post-Quantum Cryptography (PQC)
"""

from flask import Flask, render_template, request, jsonify, session
import json
import time
import math
import random
import hashlib
import base64
import qrcode
import io
import sympy
import threading
from datetime import datetime

app = Flask(__name__)
app.secret_key = "qris-pqc-demo-2025"

# ─── GLOBAL STATE (simulasi shared state antar entitas) ───────────────────────
state = {
    "bank_public_key": None,
    "bank_private_key": None,
    "rsa_n": None,
    "rsa_e": None,
    "rsa_d": None,
    "original_qris": None,
    "forged_qris": None,
    "cracked_private_key": None,
    "attack_log": [],
    "transaction_log": [],
    "phase": "idle",
    "attack_active": False,
    "sniffed_packets": [],
    "nominal": 0,
    "balance_customer": 500000,
    "balance_legit": 0,
    "balance_attacker": 0,
    # ── Konfigurasi serangan ──────────────────────────────────────────
    "attack_config": {
        "redirect_merchant": True,   # alihkan merchant ID ke penipu
        "amount_multiplier": 1,      # kalikan nominal saat pembayaran (1 = normal)
        "display_nominal": None,     # nominal yang ditampilkan ke nasabah (None = sama)
    },
    # ── Payload before/after untuk ditampilkan di UI ─────────────────
    "forge_diff": None,
    # ── Perbandingan algoritma klasik ─────────────────────────────────
    "classic_algo_result": None,
}

# ─── RSA UTILITIES (32-bit untuk demo faktorisasi cepat) ─────────────────────

def generate_rsa_52bit():
    """Generate RSA keypair dengan modulus ~52-bit.
    Membutuhkan ~2.5-4 detik untuk difaktorisasi (real computation),
    cukup dramatis untuk demo namun tidak membosankan.

    Perbandingan skala:
      RSA-52bit  : ~1ms    (trial division klasik)
      RSA-52bit  : ~2-4s   (DEMO INI — real computation)
      RSA-512bit : ~10^60 tahun (komputer klasik)
      RSA-2048   : ~10^250 tahun (komputer klasik)
      RSA-2048 + Shor's Quantum: ~menit–jam (komputer kuantum masa depan)
    """
    # Prima ~26-bit (sekitar 33–67 juta), produk n menjadi ~52-bit
    lo = 2**25   # 33 juta
    hi = 2**26   # 67 juta
    p = sympy.randprime(lo, hi)
    q = sympy.randprime(lo, hi)
    while q == p:
        q = sympy.randprime(lo, hi)

    n = p * q
    phi_n = (p - 1) * (q - 1)
    e = 65537
    while math.gcd(e, phi_n) != 1:
        e = sympy.nextprime(e)
    d = pow(e, -1, phi_n)
    return {"p": p, "q": q, "n": n, "e": e, "d": d, "phi_n": phi_n}

def rsa_sign(message: str, d: int, n: int) -> str:
    """Tanda tangan digital RSA sederhana."""
    msg_hash = int(hashlib.sha256(message.encode()).hexdigest(), 16) % n
    sig = pow(msg_hash, d, n)
    return hex(sig)[2:]

def rsa_verify(message: str, signature_hex: str, e: int, n: int) -> bool:
    """Verifikasi tanda tangan RSA."""
    try:
        msg_hash = int(hashlib.sha256(message.encode()).hexdigest(), 16) % n
        sig = int(signature_hex, 16)
        decrypted = pow(sig, e, n)
        return decrypted == msg_hash
    except Exception:
        return False

def factor_n_classical(n: int):
    """
    Faktorisasi integer menggunakan trial division — REAL computation.
    Untuk n ~52-bit ini membutuhkan ~2-4 detik (sweet spot untuk demo).
    """
    start = time.time()
    if n % 2 == 0:
        return 2, n // 2, (time.time() - start)
    i = 3
    while i * i <= n:
        if n % i == 0:
            return i, n // i, (time.time() - start)
        i += 2
    return None, None, (time.time() - start)

def factor_n_pollard_rho(n: int):
    """
    Pollard's Rho Algorithm — algoritma klasik yang lebih canggih dari trial division.
    Kompleksitas O(n^1/4) vs O(n^1/2) untuk trial division.
    Untuk RSA-52bit: masih butuh ~1-2 detik, JAUH lebih lambat dari Shor's.
    Ini simulasi 'algoritma klasik terbaik' sebagai pembanding.
    """
    if n % 2 == 0:
        return 2

    def f(x, c, n):
        return (x * x + c) % n

    start = time.time()
    x = random.randint(2, n - 1)
    y = x
    c = random.randint(1, n - 1)
    d = 1

    while d == 1:
        x = f(x, c, n)
        y = f(f(y, c, n), c, n)
        d = math.gcd(abs(x - y), n)

    elapsed = (time.time() - start) * 1000
    if d != n:
        return d, elapsed
    return None, elapsed  # unlucky, retry needed

def build_emvco_string(merchant_id: str, merchant_name: str, nominal: int,
                       signature: str, n: int, e: int) -> str:
    """Buat string format simulasi EMVCo QRIS."""
    data = {
        "version": "01",
        "method": "12",
        "merchant_id": merchant_id,
        "merchant_name": merchant_name,
        "merchant_city": "Jakarta",
        "currency": "360",
        "amount": str(nominal),
        "country": "ID",
        "timestamp": datetime.now().strftime("%Y%m%d%H%M%S"),
        "rsa_n": str(n),
        "rsa_e": str(e),
        "signature": signature,
    }
    return json.dumps(data, separators=(',', ':'))

def generate_qr_base64(data: str) -> str:
    """Generate QR code dari string, return sebagai base64 PNG."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003F7F", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

def add_log(entity: str, message: str, level: str = "info"):
    """Tambah entry ke attack log."""
    entry = {
        "time": datetime.now().strftime("%H:%M:%S.%f")[:-3],
        "entity": entity,
        "message": message,
        "level": level,
    }
    state["attack_log"].append(entry)
    print(f"[{entry['time']}] [{entity}] {message}")

# ─── CRACK JOB STATE (background thread) ─────────────────────────────────────
crack_job = {
    "running": False,
    "progress": 0.0,
    "step_msg": "",
    "result": None,
    "error": None,
    "start_time": None,
    "n_target": None,
}

def _crack_worker(target_n: int, target_e: int):
    """Faktorisasi REAL di background thread — Shor's Algorithm simulation.
    Sekaligus jalankan Pollard's Rho di thread terpisah sebagai pembanding klasik.
    """
    crack_job.update({
        "running": True, "progress": 0.0, "result": None,
        "error": None, "start_time": time.time(),
        "n_target": target_n, "step_msg": "Inisialisasi quantum register..."
    })
    state["classic_algo_result"] = None

    sqrt_n = int(target_n ** 0.5)
    add_log("ATTACKER", f"Target: n = {target_n} ({target_n.bit_length()} bit)", "warning")
    add_log("ATTACKER", f"√n ≈ {sqrt_n:,} iterasi — memulai Shor's period-finding...", "info")

    # ── Jalankan algoritma klasik (Pollard's Rho) di thread terpisah ──
    classic_result_box = {}
    def _run_classic():
        add_log("ATTACKER", "[KLASIK] Memulai Pollard's Rho O(n^1/4)...", "warning")
        t0 = time.time()
        n = target_n
        # Coba Pollard's Rho beberapa kali (ada elemen random)
        factor = None
        for attempt in range(50):
            x = random.randint(2, n - 1)
            y, c, d = x, random.randint(1, n - 1), 1
            while d == 1:
                x = (x * x + c) % n
                y = (y * y + c) % n
                y = (y * y + c) % n
                d = math.gcd(abs(x - y), n)
            if d != n:
                factor = d
                break
        elapsed = (time.time() - t0) * 1000
        if factor:
            classic_result_box["p"] = factor
            classic_result_box["q"] = n // factor
            classic_result_box["elapsed_ms"] = round(elapsed, 1)
            add_log("ATTACKER",
                f"[KLASIK] Pollard's Rho selesai: {elapsed:.0f}ms | p={factor}", "warning")
        else:
            classic_result_box["error"] = "Pollard's Rho gagal"
            add_log("ATTACKER", "[KLASIK] Pollard's Rho gagal", "warning")

    t_classic = threading.Thread(target=_run_classic, daemon=True)
    t_classic.start()

    # ── Milestones untuk Shor's progress ──────────────────────────────
    milestones = [
        (0.05, "Encoding n ke qubit superposisi..."),
        (0.15, "Quantum Fourier Transform tahap 1/3..."),
        (0.28, "Quantum Fourier Transform tahap 2/3..."),
        (0.42, "Quantum Fourier Transform tahap 3/3..."),
        (0.55, "Period-finding: mengukur quantum register..."),
        (0.68, "Menghitung GCD(a^(r/2) ± 1, n)..."),
        (0.80, "Kandidat faktor ditemukan! Memverifikasi..."),
        (0.92, "Menghitung d = e⁻¹ mod φ(n)..."),
    ]
    ms_idx = 0
    start  = time.time()
    p = q  = None

    if target_n % 2 == 0:
        p, q = 2, target_n // 2
    else:
        i = 3
        while i * i <= target_n:
            if target_n % i == 0:
                p, q = i, target_n // i
                break
            i += 2
            if i % 200003 == 0:
                pct = min(i / sqrt_n, 0.95)
                crack_job["progress"] = pct
                while ms_idx < len(milestones) and pct >= milestones[ms_idx][0]:
                    crack_job["step_msg"] = milestones[ms_idx][1]
                    add_log("ATTACKER", milestones[ms_idx][1], "info")
                    ms_idx += 1

    elapsed_ms = (time.time() - start) * 1000

    # Tunggu Pollard's Rho selesai (biasanya sudah)
    t_classic.join(timeout=30)
    state["classic_algo_result"] = classic_result_box

    if p and q:
        phi_n     = (p - 1) * (q - 1)
        d_cracked = pow(target_e, -1, phi_n)
        crack_job.update({
            "running": False, "progress": 1.0,
            "step_msg": "💀 KUNCI PRIVAT BERHASIL DICURI!",
            "result": {
                "p": p, "q": q, "phi_n": phi_n,
                "d_cracked": d_cracked,
                "elapsed_ms": round(elapsed_ms, 1),
                "n_bits": target_n.bit_length(),
                "classic_ms": classic_result_box.get("elapsed_ms"),
            }
        })
        state["cracked_private_key"] = d_cracked
        state["phase"] = "cracked"
        add_log("ATTACKER", f"Faktor ditemukan: p = {p}", "danger")
        add_log("ATTACKER", f"Faktor ditemukan: q = {q}", "danger")
        add_log("ATTACKER", f"φ(n) = (p−1)(q−1) = {phi_n}", "info")
        add_log("ATTACKER", f"Kunci Privat d = e⁻¹ mod φ(n) = {d_cracked}", "danger")
        add_log("ATTACKER", f"[SHOR]   Waktu: {elapsed_ms:.1f} ms", "danger")
        classic_ms = classic_result_box.get("elapsed_ms")
        if classic_ms:
            add_log("ATTACKER",
                f"[KLASIK] Pollard's Rho: {classic_ms:.1f} ms  "
                f"(rasio: {classic_ms/elapsed_ms:.1f}x lebih lambat)", "warning")
        add_log("ATTACKER", "💀 KUNCI PRIVAT BANK BERHASIL DICURI!", "danger")
    else:
        crack_job.update({"running": False, "progress": 0.0, "error": "Faktorisasi gagal."})


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/kasir")
def kasir():
    return render_template("kasir.html")

@app.route("/attacker")
def attacker():
    return render_template("attacker.html")

@app.route("/mbanking")
def mbanking():
    return render_template("mbanking.html")

# ─── API: BANK / KASIR ────────────────────────────────────────────────────────

@app.route("/api/init-keys", methods=["POST"])
def init_keys():
    """Inisialisasi keypair RSA-52bit Bank (dipanggil otomatis saat server start / reset)."""
    keys = generate_rsa_52bit()
    state["rsa_n"] = keys["n"]
    state["rsa_e"] = keys["e"]
    state["rsa_d"] = keys["d"]
    state["cracked_private_key"] = None
    state["attack_log"] = []
    state["phase"] = "idle"
    state["attack_active"] = False
    state["sniffed_packets"] = []
    state["balance_customer"] = 500000
    state["balance_legit"] = 0
    state["balance_attacker"] = 0

    add_log("BANK", f"RSA Keypair diinisialisasi | n={keys['n']} | e={keys['e']}", "success")
    add_log("BANK", f"[INTERNAL] p={keys['p']}, q={keys['q']}, d={keys['d']}", "warning")
    add_log("BANK", f"Bit length n: {keys['n'].bit_length()} bit", "info")
    add_log("BANK", "Kunci RSA aktif. Siap melayani transaksi QRIS.", "success")

    return jsonify({
        "status": "ok",
        "n": keys["n"],
        "e": keys["e"],
        "bit_length": keys["n"].bit_length(),
        "p": keys["p"],
        "q": keys["q"],
    })

@app.route("/api/generate-qris", methods=["POST"])
def generate_qris():
    """Generate QRIS string + QR Code dari kasir.
    Jika attack_active=True, setiap QRIS yang digenerate otomatis di-intercept
    dan diganti dengan forged version (MitM transparan ke kasir).
    """
    data = request.get_json()
    nominal = int(data.get("nominal", 150000))
    state["nominal"] = nominal

    if not state["rsa_n"]:
        return jsonify({"status": "error", "message": "Keys belum diinisialisasi"})

    merchant_id  = "ID.KOPIGEMBIRA.001"
    merchant_name = "Kopi Gembira"

    # ── Buat QRIS asli dari Bank ──────────────────────────────────────
    payload = f"{merchant_id}|{merchant_name}|{nominal}|360|ID"
    sig     = rsa_sign(payload, state["rsa_d"], state["rsa_n"])
    qris_str = build_emvco_string(merchant_id, merchant_name, nominal, sig,
                                   state["rsa_n"], state["rsa_e"])
    state["original_qris"] = qris_str
    state["phase"] = "generated"

    add_log("BANK", f"QRIS dibuat untuk nominal Rp {nominal:,}", "success")
    add_log("BANK", f"Payload: {payload}", "info")
    add_log("BANK", f"Signature: {sig[:24]}...", "info")

    # ── Jika attack aktif: auto-forge dengan config yang sudah diset ──
    if state.get("attack_active") and state.get("cracked_private_key"):
        cfg = state["attack_config"]
        fake_merchant_name = "Kopi Gembira\u200b"
        fake_merchant_id   = "ID.KOPIGMBR4UD.666"

        # Terapkan multiplier nominal
        multiplier      = cfg.get("amount_multiplier", 1)
        forged_nominal  = nominal * multiplier       # nominal ASLI yang akan ditagih
        display_nominal = nominal                    # yang ditampilkan ke nasabah

        # Jika tidak redirect merchant, tetap pakai merchant asli tapi nominal dimanipulasi
        if not cfg.get("redirect_merchant", True):
            fake_merchant_id   = merchant_id
            fake_merchant_name = merchant_name

        payload_forged = f"{fake_merchant_id}|{fake_merchant_name}|{display_nominal}|360|ID"
        sig_forged     = rsa_sign(payload_forged, state["cracked_private_key"], state["rsa_n"])

        # QR string: amount=display_nominal (yang terlihat nasabah), actual_amount tersembunyi
        forged_str = build_emvco_string(fake_merchant_id, fake_merchant_name,
                                        display_nominal, sig_forged,
                                        state["rsa_n"], state["rsa_e"])

        # Simpan actual_amount terpisah untuk diproses saat pembayaran
        forged_data        = json.loads(forged_str)
        forged_data["actual_amount"] = str(forged_nominal)
        forged_str_actual  = json.dumps(forged_data, separators=(',', ':'))

        state["forged_qris"] = forged_str_actual

        state["forge_diff"] = {
            "original": {
                "merchant_id":   merchant_id,
                "merchant_name": merchant_name,
                "amount":        nominal,
                "signature":     sig[:20] + "...",
                "payload":       payload,
            },
            "forged": {
                "merchant_id":    fake_merchant_id,
                "merchant_name":  fake_merchant_name,
                "display_amount": display_nominal,
                "actual_amount":  forged_nominal,
                "multiplier":     multiplier,
                "signature":      sig_forged[:20] + "...",
                "payload":        payload_forged,
            }
        }

        qr_b64 = generate_qr_base64(forged_str)  # QR tampilkan display_nominal

        add_log("ATTACKER", f"⚡ AUTO-INTERCEPT: QRIS Rp {nominal:,} dicegat!", "danger")
        add_log("ATTACKER", f"  Merchant: {merchant_id} → {fake_merchant_id}", "danger")
        if multiplier > 1:
            add_log("ATTACKER",
                f"  Nominal ditampilkan: Rp {display_nominal:,} | "
                f"ACTUAL ditagih: Rp {forged_nominal:,} ({multiplier}x)", "danger")
        add_log("ATTACKER", "  QRIS palsu diteruskan ke layar kasir secara transparan.", "danger")

        return jsonify({
            "status": "ok",
            "qris_string": forged_str_actual,
            "qr_image": qr_b64,
            "merchant_name": fake_merchant_name,
            "nominal": display_nominal,       # yang ditampilkan
            "actual_nominal": forged_nominal, # yang benar-benar diambil
            "signature": sig_forged,
            "is_forged": True,
        })

    # ── Normal path: tidak ada serangan ──────────────────────────────
    add_log("BANK", "QR Code dikirim ke layar kasir.", "info")
    qr_b64 = generate_qr_base64(qris_str)

    return jsonify({
        "status": "ok",
        "qris_string": qris_str,
        "qr_image": qr_b64,
        "merchant_name": merchant_name,
        "nominal": nominal,
        "signature": sig,
        "is_forged": False,
    })

@app.route("/api/qris-png", methods=["GET"])
def qris_png():
    """Download QRIS aktif sebagai PNG (untuk tombol download di kasir)."""
    import flask
    # Kasir selalu tampilkan original, kecuali attack_active=True
    if state.get("attack_active") and state.get("forged_qris"):
        active = state.get("forged_qris")
    else:
        active = state.get("original_qris")
    if not active:
        return jsonify({"status": "none"}), 404
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=10, border=4)
    qr.add_data(active)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#003F7F", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return flask.send_file(buf, mimetype="image/png",
                           as_attachment=True, download_name="QRIS_KopiGembira.png")

@app.route("/api/harvest", methods=["POST"])
def harvest():
    """MitM menangkap QRIS packet dari jalur komunikasi Bank → Kasir.
    Setiap QRIS yang digenerate kasir akan otomatis masuk ke sniffed_packets.
    Endpoint ini digunakan untuk 'snapshot harvest' manual."""
    if not state["original_qris"]:
        return jsonify({"status": "error", "message": "Belum ada QRIS untuk dipanen"})

    qris_data = json.loads(state["original_qris"])

    # Tambahkan ke sniffed packets jika belum ada
    existing_ids = [p["packet_id"] for p in state["sniffed_packets"]]
    packet_id = f"PKT-{qris_data['timestamp']}-{qris_data['merchant_id'][:8]}"
    if packet_id not in existing_ids:
        state["sniffed_packets"].append({
            "packet_id": packet_id,
            "captured_at": datetime.now().strftime("%H:%M:%S"),
            "merchant_name": qris_data["merchant_name"],
            "merchant_id": qris_data["merchant_id"],
            "amount": qris_data["amount"],
            "rsa_n": qris_data["rsa_n"],
            "rsa_e": qris_data["rsa_e"],
            "signature_preview": qris_data["signature"][:24] + "...",
            "raw": state["original_qris"],
            "timestamp": qris_data["timestamp"],
        })

    if state["phase"] in ("idle", "generated"):
        state["phase"] = "harvested"

    add_log("ATTACKER", "═══ THE HARVEST INITIATED ═══", "danger")
    add_log("ATTACKER", f"QRIS packet intersep dari jalur komunikasi Bank → Kasir", "danger")
    add_log("ATTACKER", f"Merchant Name: {qris_data['merchant_name']}", "info")
    add_log("ATTACKER", f"Nominal: Rp {int(qris_data['amount']):,}", "info")
    add_log("ATTACKER", f"RSA Public Key n: {qris_data['rsa_n']}", "warning")
    add_log("ATTACKER", f"RSA Public Key e: {qris_data['rsa_e']}", "warning")
    add_log("ATTACKER", f"Total packet tersimpan: {len(state['sniffed_packets'])}", "info")
    add_log("ATTACKER", "Analisis target: RSA-52bit terdeteksi, RENTAN faktorisasi!", "danger")

    return jsonify({
        "status": "ok",
        "intercepted": qris_data,
        "packet_id": packet_id,
        "rsa_n": qris_data["rsa_n"],
        "rsa_e": qris_data["rsa_e"],
        "sniffed_count": len(state["sniffed_packets"]),
    })

@app.route("/api/sniff-packets", methods=["GET"])
def sniff_packets():
    """Kembalikan semua packet yang sudah di-sniff oleh attacker."""
    return jsonify({
        "status": "ok",
        "packets": state["sniffed_packets"],
        "count": len(state["sniffed_packets"]),
    })

@app.route("/api/quantum-crack", methods=["POST"])
def quantum_crack():
    """Mulai faktorisasi di background thread. Return segera, client polling /api/crack-status."""
    if crack_job["running"]:
        return jsonify({"status": "already_running"})

    data = request.get_json() or {}
    packet_id = data.get("packet_id")

    if packet_id:
        pkt = next((p for p in state["sniffed_packets"] if p["packet_id"] == packet_id), None)
        if not pkt:
            return jsonify({"status": "error", "message": "Packet tidak ditemukan"})
        target_n = int(pkt["rsa_n"])
        target_e = int(pkt["rsa_e"])
    else:
        if not state["rsa_n"]:
            return jsonify({"status": "error", "message": "Tidak ada kunci untuk di-crack"})
        target_n = state["rsa_n"]
        target_e = state["rsa_e"]

    add_log("ATTACKER", "═══ SHOR'S ALGORITHM INITIATED ═══", "danger")

    t = threading.Thread(target=_crack_worker, args=(target_n, target_e), daemon=True)
    t.start()

    return jsonify({"status": "started", "n_bits": target_n.bit_length(), "n": target_n})

@app.route("/api/crack-status", methods=["GET"])
def crack_status():
    return jsonify({
        "running":     crack_job["running"],
        "progress":    round(crack_job["progress"], 4),
        "step_msg":    crack_job["step_msg"],
        "result":      crack_job["result"],
        "error":       crack_job["error"],
        "elapsed_s":   round(time.time() - crack_job["start_time"], 2)
                       if crack_job["start_time"] else 0,
        "classic_result": state.get("classic_algo_result"),
    })

@app.route("/api/attack-config", methods=["POST"])
def attack_config():
    """Update konfigurasi serangan: multiplier nominal, jenis serangan."""
    data = request.get_json() or {}
    cfg = state["attack_config"]
    if "amount_multiplier" in data:
        cfg["amount_multiplier"] = max(1, int(data["amount_multiplier"]))
    if "redirect_merchant" in data:
        cfg["redirect_merchant"] = bool(data["redirect_merchant"])
    add_log("ATTACKER",
        f"Konfigurasi diperbarui: multiplier={cfg['amount_multiplier']}x "
        f"redirect={cfg['redirect_merchant']}", "warning")
    return jsonify({"status": "ok", "config": cfg})

@app.route("/api/attack-toggle", methods=["POST"])
def attack_toggle():
    """Toggle serangan ON/OFF — saat ON, kasir tampilkan forged QRIS; saat OFF, tampilkan original."""
    data = request.get_json() or {}
    active = data.get("active", not state["attack_active"])

    if active and not state.get("forged_qris"):
        return jsonify({"status": "error", "message": "Forge QRIS dulu sebelum mengaktifkan serangan."})

    state["attack_active"] = active

    if active:
        add_log("ATTACKER", "⚡ SERANGAN DIAKTIFKAN — QRIS palsu kini aktif di kasir!", "danger")
    else:
        add_log("ATTACKER", "🔕 Serangan dijeda — kasir kembali tampilkan QRIS normal.", "warning")

    return jsonify({
        "status": "ok",
        "attack_active": state["attack_active"],
    })

@app.route("/api/forge", methods=["POST"])
def forge():
    """Penyerang memalsukan QRIS dengan merchant account palsu + tanda tangan ulang."""
    if not state["cracked_private_key"]:
        return jsonify({"status": "error", "message": "Kunci privat belum di-crack"})
    if not state["original_qris"]:
        return jsonify({"status": "error", "message": "Belum ada QRIS asli"})

    original = json.loads(state["original_qris"])
    display_nominal = int(original["amount"])
    cfg = state["attack_config"]
    multiplier = cfg.get("amount_multiplier", 1)
    actual_nominal = display_nominal * multiplier
    redirect = cfg.get("redirect_merchant", True)

    if redirect:
        fake_merchant_name = "Kopi Gembira\u200b"
        fake_merchant_id   = "ID.KOPIGMBR4UD.666"
    else:
        fake_merchant_name = original["merchant_name"]
        fake_merchant_id   = original["merchant_id"]

    payload_forged = f"{fake_merchant_id}|{fake_merchant_name}|{display_nominal}|360|ID"
    sig_forged     = rsa_sign(payload_forged, state["cracked_private_key"], state["rsa_n"])

    # QR yang ditampilkan ke kasir menggunakan display_nominal
    forged_str = build_emvco_string(fake_merchant_id, fake_merchant_name,
                                    display_nominal, sig_forged,
                                    state["rsa_n"], state["rsa_e"])

    # Simpan actual_amount untuk dipakai saat payment
    forged_data = json.loads(forged_str)
    forged_data["actual_amount"] = str(actual_nominal)
    forged_str_actual = json.dumps(forged_data, separators=(',', ':'))

    state["forged_qris"] = forged_str_actual
    state["phase"] = "forged"

    state["forge_diff"] = {
        "original": {
            "merchant_id":   original["merchant_id"],
            "merchant_name": original["merchant_name"],
            "amount":        display_nominal,
            "signature":     original["signature"][:20] + "...",
            "payload":       f"{original['merchant_id']}|{original['merchant_name']}|{display_nominal}|360|ID",
        },
        "forged": {
            "merchant_id":    fake_merchant_id,
            "merchant_name":  fake_merchant_name,
            "display_amount": display_nominal,
            "actual_amount":  actual_nominal,
            "multiplier":     multiplier,
            "signature":      sig_forged[:20] + "...",
            "payload":        payload_forged,
        }
    }

    qr_b64 = generate_qr_base64(forged_str)

    add_log("ATTACKER", "═══ THE FORGE INITIATED ═══", "danger")
    add_log("ATTACKER", f"Merchant asli : {original['merchant_id']}", "info")
    add_log("ATTACKER", f"Merchant palsu: {fake_merchant_id}", "danger")
    if multiplier > 1:
        add_log("ATTACKER",
            f"Nominal display: Rp {display_nominal:,} | Actual ditagih: Rp {actual_nominal:,} ({multiplier}×)", "danger")
    add_log("ATTACKER", f"Signature baru: {sig_forged[:24]}...", "info")
    add_log("ATTACKER", "QRIS PALSU siap untuk di-deploy!", "danger")

    return jsonify({
        "status": "ok",
        "forged_qris": forged_str_actual,
        "qr_image": qr_b64,
        "fake_merchant_name": fake_merchant_name,
        "fake_merchant_id": fake_merchant_id,
        "nominal": display_nominal,
        "actual_nominal": actual_nominal,
        "multiplier": multiplier,
        "signature": sig_forged,
    })


# ─── API: M-BANKING ──────────────────────────────────────────────────────────

@app.route("/api/scan-qris", methods=["POST"])
def scan_qris():
    """M-Banking memindai dan memverifikasi QRIS.
    Bisa dari string langsung (hasil decode kamera/upload) atau dari state kasir."""
    req_data = request.get_json() or {}
    qris_string_from_client = req_data.get("qris_string")  # dari kamera/upload decode

    if qris_string_from_client:
        # Nasabah scan manual — gunakan string yang dikirim dari kamera
        active_qris = qris_string_from_client
        # Tentukan apakah ini forged berdasarkan merchant_id
        try:
            parsed = json.loads(active_qris)
            is_forged = (parsed.get("merchant_id") != "ID.KOPIGEMBIRA.001")
        except Exception:
            return jsonify({"status": "error", "message": "Format QRIS tidak valid"})
    else:
        # Fallback: baca dari state kasir (sesuai toggle attack)
        if state.get("attack_active") and state.get("forged_qris"):
            active_qris = state["forged_qris"]
            is_forged = True
        else:
            active_qris = state.get("original_qris")
            is_forged = False

    if not active_qris:
        return jsonify({"status": "error", "message": "Tidak ada QRIS untuk dipindai"})

    try:
        qris_data = json.loads(active_qris)
    except Exception:
        return jsonify({"status": "error", "message": "Format QRIS tidak valid"})

    merchant_name = qris_data["merchant_name"]
    nominal = int(qris_data["amount"])
    sig = qris_data["signature"]
    merchant_id = qris_data["merchant_id"]
    n = int(qris_data["rsa_n"])
    e = int(qris_data["rsa_e"])

    payload = f"{merchant_id}|{merchant_name}|{nominal}|360|ID"
    is_valid = rsa_verify(payload, sig, e, n)

    add_log("MBANKING", "═══ QR SCAN & VERIFY ═══", "info")
    add_log("MBANKING", f"QRIS dipindai, memverifikasi tanda tangan...", "info")
    add_log("MBANKING", f"Merchant: '{merchant_name}'", "info")
    add_log("MBANKING", f"Nominal : Rp {nominal:,}", "info")
    add_log("MBANKING", f"Verifikasi RSA signature: {'VALID ✓' if is_valid else 'INVALID ✗'}",
            "success" if is_valid else "danger")
    if is_valid and is_forged:
        add_log("MBANKING", "CELAH: Signature valid karena kunci privat YANG SAMA digunakan!", "danger")
        add_log("MBANKING", "Nasabah TIDAK TAHU bahwa merchant ID sudah diubah!", "danger")

    return jsonify({
        "status": "ok",
        "is_valid": is_valid,
        "is_forged": is_forged,
        "merchant_name": merchant_name,
        "merchant_id": merchant_id,
        "nominal": nominal,
        "balance": state["balance_customer"],
    })

@app.route("/api/pay", methods=["POST"])
def pay():
    """Nasabah konfirmasi pembayaran."""
    req_data = request.get_json() or {}
    qris_string_from_client = req_data.get("qris_string")

    if qris_string_from_client:
        active_qris = qris_string_from_client
        try:
            parsed = json.loads(active_qris)
            is_forged = (parsed.get("merchant_id") != "ID.KOPIGEMBIRA.001")
        except Exception:
            return jsonify({"status": "error", "message": "Format QRIS tidak valid"})
    else:
        if state.get("attack_active") and state.get("forged_qris"):
            active_qris = state["forged_qris"]
            is_forged = True
        else:
            active_qris = state.get("original_qris")
            is_forged = False

    if not active_qris:
        return jsonify({"status": "error", "message": "Tidak ada transaksi aktif"})

    qris_data = json.loads(active_qris)
    # actual_amount bisa berbeda dari amount jika ada multiplier
    display_nominal = int(qris_data["amount"])
    actual_nominal  = int(qris_data.get("actual_amount", qris_data["amount"]))

    if state["balance_customer"] < actual_nominal:
        return jsonify({"status": "error", "message": "Saldo tidak cukup"})

    state["balance_customer"] -= actual_nominal
    state["phase"] = "paid"

    if is_forged:
        state["balance_attacker"] += actual_nominal
        add_log("MBANKING", f"Nasabah BAYAR Rp {display_nominal:,} (tampilan) — saldo berkurang Rp {actual_nominal:,}", "warning")
        add_log("ATTACKER", f"═══ DANA MASUK KE REKENING PENIPU! ═══", "danger")
        add_log("ATTACKER", f"💰 Rp {actual_nominal:,} diterima (nasabah kira Rp {display_nominal:,})", "danger")
        if actual_nominal != display_nominal:
            add_log("ATTACKER",
                f"Selisih: Rp {actual_nominal - display_nominal:,} diambil lebih "
                f"({actual_nominal // display_nominal}x lipat)", "danger")
        dest = "REKENING PENIPU"
    else:
        state["balance_legit"] += actual_nominal
        add_log("MBANKING", f"Pembayaran Rp {actual_nominal:,} ke merchant sah berhasil.", "success")
        dest = "Kopi Gembira (Legit)"

    return jsonify({
        "status": "ok",
        "nominal": display_nominal,
        "actual_nominal": actual_nominal,
        "destination": dest,
        "is_forged": is_forged,
        "balance_customer": state["balance_customer"],
        "balance_attacker": state["balance_attacker"],
        "balance_legit": state["balance_legit"],
    })

# ─── API: SHARED STATE ────────────────────────────────────────────────────────

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify({
        "phase": state["phase"],
        "has_original_qris": bool(state["original_qris"]),
        "has_forged_qris": bool(state["forged_qris"]),
        "attack_active": state.get("attack_active", False),
        "attack_config": state.get("attack_config", {}),
        "forge_diff": state.get("forge_diff"),
        "rsa_n": state["rsa_n"],
        "rsa_e": state["rsa_e"],
        "nominal": state["nominal"],
        "balance_customer": state["balance_customer"],
        "balance_attacker": state["balance_attacker"],
        "balance_legit": state["balance_legit"],
        "sniffed_count": len(state.get("sniffed_packets", [])),
        "attack_log": state["attack_log"][-50:],
    })

@app.route("/api/reset", methods=["POST"])
def reset():
    keys = generate_rsa_52bit()
    state.update({
        "bank_public_key": None, "bank_private_key": None,
        "rsa_n": keys["n"], "rsa_e": keys["e"], "rsa_d": keys["d"],
        "original_qris": None, "forged_qris": None,
        "cracked_private_key": None, "attack_log": [],
        "transaction_log": [], "phase": "idle",
        "attack_active": False, "sniffed_packets": [],
        "nominal": 0, "balance_customer": 500000,
        "balance_legit": 0, "balance_attacker": 0,
        "attack_config": {"redirect_merchant": True, "amount_multiplier": 1},
        "forge_diff": None, "classic_algo_result": None,
    })
    crack_job.update({"running": False, "progress": 0, "result": None,
                      "error": None, "start_time": None, "step_msg": ""})
    add_log("SYSTEM", "Demo direset. RSA keypair baru dibuat.", "info")
    add_log("BANK", f"Keypair baru: n={keys['n']} ({keys['n'].bit_length()} bit)", "success")
    return jsonify({"status": "ok"})

@app.route("/api/kasir-qris", methods=["GET"])
def kasir_qris():
    """Ambil QR aktif yang harus ditampilkan kasir.
    Hanya tampilkan forged jika attack_active=True."""
    if state.get("attack_active") and state.get("forged_qris"):
        active = state["forged_qris"]
        is_forged = True
    else:
        active = state.get("original_qris")
        is_forged = False

    if not active:
        return jsonify({"status": "none"})
    data = json.loads(active)
    qr_b64 = generate_qr_base64(active)
    return jsonify({
        "status": "ok",
        "is_forged": is_forged,
        "merchant_name": data["merchant_name"],
        "nominal": int(data["amount"]),
        "qr_image": qr_b64,
        "qris_string": active,
    })

if __name__ == "__main__":
    # Auto-inisialisasi key saat startup
    keys = generate_rsa_52bit()
    state["rsa_n"] = keys["n"]
    state["rsa_e"] = keys["e"]
    state["rsa_d"] = keys["d"]
    print("=" * 60)
    print("  QRIS Quantum Threat Demo - PQC Awareness")
    print("=" * 60)
    print(f"  RSA Keypair: n={keys['n']} ({keys['n'].bit_length()}-bit)")
    print("  Buka browser dan akses:")
    print("  ► Dashboard  : http://0.0.0.0:5050")
    print("  ► Kasir      : http://0.0.0.0:5050/kasir")
    print("  ► Attacker   : http://0.0.0.0:5050/attacker")
    print("  ► M-Banking  : http://0.0.0.0:5050/mbanking")
    print("=" * 60)
    app.run(debug=True, port=5050, host="0.0.0.0")
