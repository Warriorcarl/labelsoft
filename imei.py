import subprocess
import pandas as pd
import os
import time
import sys
import json

# Warna untuk console
GREEN = '\033[92m'
BOLD = '\033[1m'
RESET = '\033[0m'
YELLOW = '\033[93m'

# Mapping ProductType ke nama produk (tetap diperlukan)
PRODUCT_MAPPING = {
    "iPhone7,2": "iPhone 6",
    "iPhone7,1": "iPhone 6 Plus",
    "iPhone8,1": "iPhone 6s",
    "iPhone8,2": "iPhone 6s Plus",
    "iPhone8,4": "iPhone SE (1st generation)",
    "iPhone9,1": "iPhone 7",
    "iPhone9,2": "iPhone 7 Plus",
    "iPhone9,3": "iPhone 7",
    "iPhone9,4": "iPhone 7 Plus",
    "iPhone10,1": "iPhone 8",
    "iPhone10,2": "iPhone 8 Plus",
    "iPhone10,3": "iPhone X",
    "iPhone10,4": "iPhone 8",
    "iPhone10,5": "iPhone 8 Plus",
    "iPhone10,6": "iPhone X",
    "iPhone11,8": "iPhone XR",
    "iPhone11,2": "iPhone XS",
    "iPhone11,6": "iPhone XS Max",
    "iPhone12,1": "iPhone 11",
    "iPhone12,3": "iPhone 11 Pro",
    "iPhone12,5": "iPhone 11 Pro Max",
    "iPhone12,8": "iPhone SE (2nd generation)",
    "iPhone13,1": "iPhone 12 mini",
    "iPhone13,2": "iPhone 12",
    "iPhone13,3": "iPhone 12 Pro",
    "iPhone13,4": "iPhone 12 Pro Max",
    "iPhone14,4": "iPhone 13 mini",
    "iPhone14,5": "iPhone 13",
    "iPhone14,2": "iPhone 13 Pro",
    "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,6": "iPhone SE (3rd generation)",
    "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus",
    "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max",
    "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus",
    "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max",
    "iPhone17,1": "iPhone 16",
    "iPhone17,2": "iPhone 16 Plus",
    "iPhone17,3": "iPhone 16 Pro",
    "iPhone17,4": "iPhone 16 Pro Max",
}

# Load mapping model Axxxx dari file JSON (dibuat oleh build_mapping.py)
MODEL_MAPPING_FILE = 'model_mapping.json'
MODEL_A_MAPPING = {}
if os.path.exists(MODEL_MAPPING_FILE):
    with open(MODEL_MAPPING_FILE, 'r') as f:
        MODEL_A_MAPPING = json.load(f)
    print(f"[STARTUP] Model mapping loaded: {len(MODEL_A_MAPPING)} produk dari {MODEL_MAPPING_FILE}")
else:
    print(f"[WARNING] {MODEL_MAPPING_FILE} tidak ditemukan. ModelID akan N/A. Jalankan build_mapping.py dulu!")

def get_model_ids_for_product(product_name):
    """Kembalikan string ModelID (Axxxx) dari mapping JSON."""
    models = MODEL_A_MAPPING.get(product_name, [])
    return ", ".join(models) if models else "N/A"

def append_to_excel(excel_file, sheet_name, new_data):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Log: Menyiapkan penyimpanan ke {excel_file} sheet {sheet_name}...")
    start_save = time.time()

    headers = ['IMEI1', 'IMEI2', 'Serial', 'Part', 'Product', 'Storage', 'ModelID']
    df_new = pd.DataFrame([new_data], columns=headers)

    if os.path.exists(excel_file):
        try:
            df_existing = pd.read_excel(excel_file, sheet_name=sheet_name)
            df = pd.concat([df_existing, df_new], ignore_index=True)
        except ValueError:
            df = df_new
    else:
        df = df_new

    mode = 'a' if os.path.exists(excel_file) else 'w'
    with pd.ExcelWriter(excel_file, engine='openpyxl', mode=mode) as writer:
        if os.path.exists(excel_file) and sheet_name in writer.book.sheetnames:
            writer.book.remove(writer.book[sheet_name])
        df.to_excel(writer, sheet_name=sheet_name, index=False)

    durasi_save = time.time() - start_save
    print(f"[{timestamp}] Log: Data berhasil ditambahkan ke {excel_file}. Durasi: {durasi_save:.2f}s")

def get_udids():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        udids_output = subprocess.check_output(['idevice_id', '-l']).decode().strip()
        udids = set(udids_output.splitlines()) if udids_output else set()
        print(f"[{timestamp}] Log: {len(udids)} perangkat terdeteksi.")
        return udids
    except subprocess.CalledProcessError:
        print(f"[{timestamp}] Error: idevice_id tidak ditemukan/tidak ada device.")
        return set()

def extract_device_info(udid):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Log: Ekstrak {udid}...")
    start_extract = time.time()
    try:
        output = subprocess.check_output(['ideviceinfo', '-u', udid]).decode()
        lines = output.splitlines()
        device_info = {}
        for line in lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                device_info[key] = value

        storage_output = subprocess.check_output(['ideviceinfo', '-u', udid, '-q', 'com.apple.disk_usage']).decode()
        storage_lines = storage_output.splitlines()
        for line in storage_lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                device_info[key] = value

        imei1 = device_info.get('InternationalMobileEquipmentIdentity', 'N/A')
        imei2 = device_info.get('InternationalMobileEquipmentIdentity2', 'N/A')
        serial = device_info.get('SerialNumber', 'N/A')
        model_number = device_info.get('ModelNumber', '')
        region_info = device_info.get('RegionInfo', '')
        part = model_number + region_info if model_number or region_info else 'N/A'

        product_type = device_info.get('ProductType', 'N/A')
        product_name = PRODUCT_MAPPING.get(product_type, f'Tidak Dikenal ({product_type})')

        # ModelID dari JSON mapping
        model_id = get_model_ids_for_product(product_name)

        total_capacity_bytes = device_info.get('TotalDataCapacity', 'N/A')
        if total_capacity_bytes != 'N/A' and total_capacity_bytes.isdigit():
            total_gb = int(total_capacity_bytes) / (1024 ** 3)
            storage = f"{round(total_gb / 128) * 128} GB" if total_gb > 0 else 'N/A'
        else:
            storage = 'N/A'

        durasi_extract = time.time() - start_extract
        print(f"[{timestamp}] Data: IMEI1:{imei1} Product:{product_name} ModelID:{model_id} ({durasi_extract:.2f}s)")

        return [imei1, imei2, serial, part, product_name, storage, model_id]
    except subprocess.CalledProcessError as e:
        error_msg = str(e)
        if "-19" in error_msg or "Pairing dialog response pending" in error_msg:
            print(f"{YELLOW}[{timestamp}] Warning: {udid} belum di-trust. Tap 'Trust' di iPhone.{RESET}")
        else:
            print(f"[{timestamp}] Error {udid}: {error_msg}")
        return None

def shutdown_device(udid):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Log: Shutdown {udid}...")
    try:
        subprocess.check_output(['idevicediagnostics', '-u', udid, 'shutdown'])
        print(f"[{timestamp}] {udid} dimatikan.")
    except subprocess.CalledProcessError as e:
        print(f"[{timestamp}] Error shutdown {udid}: {str(e)}")

# Load seen IMEI
seen_file = 'seen_imei.json'
if os.path.exists(seen_file):
    with open(seen_file, 'r') as f:
        seen_imei = set(json.load(f))
else:
    seen_imei = set()

print("Menu:")
print("1. Pemantauan (ekstrak + simpan)")
print("2. Pemantauan (ekstrak + simpan + shutdown)")
print("3. Keluar")
choice = input("Pilih (1/2/3): ")

if choice == '3':
    sys.exit(0)
elif choice not in ['1', '2']:
    print("Invalid. Keluar.")
    sys.exit(0)

auto_shutdown = (choice == '2')

timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
print(f"[{timestamp}] Mulai monitoring. Hubungkan device baru. Ctrl+C stop.")
print(f"[{timestamp}] Seen IMEI: {len(seen_imei)}")

previous_udids = get_udids()
standby_dots = 0
excel_file = 'iphone_data.xlsx'
sheet_name = 'Data'

try:
    while True:
        current_udids = get_udids()

        disconnected = previous_udids - current_udids
        for disc in disconnected:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {disc} dicabut. Standby...")

        processed_new = False
        for udid in current_udids:
            info = extract_device_info(udid)
            if info is None:
                continue

            imei1, imei2, serial, part, product_name, storage, model_id = info
            if imei1 == 'N/A':
                continue

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if imei1 in seen_imei:
                print(f"{YELLOW}[{timestamp}] IMEI {imei1} sudah ada. Skip.{RESET}")
                continue

            append_to_excel(excel_file, sheet_name, [imei1, imei2, serial, part, product_name, storage, model_id])
            print(f"{GREEN}{BOLD}[{timestamp}] {udid} SAVED! Cabut & ganti device.{RESET}")

            seen_imei.add(imei1)
            with open(seen_file, 'w') as f:
                json.dump(list(seen_imei), f)

            processed_new = True
            if auto_shutdown:
                shutdown_device(udid)

        if processed_new:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Batch selesai.")

        standby_dots = (standby_dots + 1) % 4
        sys.stdout.write(f"\r[{time.strftime('%Y-%m-%d %H:%M:%S')}] Standby{'.' * standby_dots}   ")
        sys.stdout.flush()

        previous_udids = current_udids
        time.sleep(5)
except KeyboardInterrupt:
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Stopped.")
    sys.exit(0)
