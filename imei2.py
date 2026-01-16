import subprocess
import pandas as pd
import os
import time
import sys
import json

GREEN = '\033[92m'
BOLD = '\033[1m'
RESET = '\033[0m'
YELLOW = '\033[93m'

PRODUCT_MAPPING = {
    "iPhone7,2": "iPhone 6", "iPhone7,1": "iPhone 6 Plus", "iPhone8,1": "iPhone 6s",
    "iPhone8,2": "iPhone 6s Plus", "iPhone8,4": "iPhone SE (1st generation)",
    "iPhone9,1": "iPhone 7", "iPhone9,2": "iPhone 7 Plus", "iPhone9,3": "iPhone 7",
    "iPhone9,4": "iPhone 7 Plus", "iPhone10,1": "iPhone 8", "iPhone10,2": "iPhone 8 Plus",
    "iPhone10,3": "iPhone X", "iPhone10,4": "iPhone 8", "iPhone10,5": "iPhone 8 Plus",
    "iPhone10,6": "iPhone X", "iPhone11,8": "iPhone XR", "iPhone11,2": "iPhone XS",
    "iPhone11,6": "iPhone XS Max", "iPhone12,1": "iPhone 11", "iPhone12,3": "iPhone 11 Pro",
    "iPhone12,5": "iPhone 11 Pro Max", "iPhone12,8": "iPhone SE (2nd generation)",
    "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12", "iPhone13,3": "iPhone 12 Pro",
    "iPhone13,4": "iPhone 12 Pro Max", "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13",
    "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,6": "iPhone SE (3rd generation)", "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus", "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max", "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus", "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max", "iPhone17,1": "iPhone 16",
    "iPhone17,2": "iPhone 16 Plus", "iPhone17,3": "iPhone 16 Pro",
    "iPhone17,4": "iPhone 16 Pro Max",
}

MODEL_MAPPING_FILE = 'model_mapping.json'
UPC_MAPPING_FILE = 'upc_mapping.json'

MODEL_A_MAPPING = {}
if os.path.exists(MODEL_MAPPING_FILE):
    with open(MODEL_MAPPING_FILE, 'r') as f:
        MODEL_A_MAPPING = json.load(f)
    print(f"Loaded {len(MODEL_A_MAPPING)} model mappings")

UPC_MAPPING = {}
if os.path.exists(UPC_MAPPING_FILE):
    with open(UPC_MAPPING_FILE, 'r') as f:
        UPC_MAPPING = json.load(f)
    print(f"Loaded {len(UPC_MAPPING)} UPC mappings")

def get_model_ids(product_name):
    models = MODEL_A_MAPPING.get(product_name, [])
    return ", ".join(models) if models else "N/A"

def get_upc(product_name, storage, part):
    upc_data = UPC_MAPPING.get(product_name, {})
    storage_key = storage.split()[0] + " GB"
    region = "Global"
    if "US" in part.upper(): 
        region = "US"
    return upc_data.get(storage_key, {}).get(region, "N/A")

def append_to_excel(excel_file, sheet_name, new_data):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()  # ✅ FIX 1
    print(f"[{timestamp}] Saving to {excel_file}...")

    headers = ['IMEI1', 'IMEI2', 'Serial', 'Part', 'Product', 'Storage', 'ModelID', 'UPC']
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
    
    durasi = time.time() - start_time  # ✅ FIX 1
    print(f"[{timestamp}] ✅ Saved! ({durasi:.2f}s)")

def get_udids():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        udids_output = subprocess.check_output(['idevice_id', '-l']).decode().strip()
        udids = set(udids_output.splitlines()) if udids_output else set()
        print(f"[{timestamp}] {len(udids)} devices detected.")
        return udids
    except:
        print(f"[{timestamp}] No idevice_id or no devices.")
        return set()

def extract_device_info(udid):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Extracting {udid}...")
    start = time.time()
    try:
        output = subprocess.check_output(['ideviceinfo', '-u', udid]).decode()
        device_info = {}
        for line in output.splitlines():
            if ': ' in line:
                key, value = line.split(': ', 1)
                device_info[key] = value  # ✅ FIX 2: pakai loop manual

        # Storage domain
        storage_output = subprocess.check_output(['ideviceinfo', '-u', udid, '-q', 'com.apple.disk_usage']).decode()
        for line in storage_output.splitlines():
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
        product_name = PRODUCT_MAPPING.get(product_type, f'Unknown ({product_type})')

        model_id = get_model_ids(product_name)
        
        # ✅ FIX 3: Storage calculation
        storage_bytes = device_info.get('TotalDataCapacity')
        if storage_bytes and str(storage_bytes).isdigit() and int(storage_bytes) > 0:
            total_gb = int(storage_bytes) / (1024 ** 3)
            storage = f"{round(total_gb / 128) * 128} GB"
        else:
            storage = 'N/A'
        
        upc = get_upc(product_name, storage, part)

        durasi = time.time() - start
        print(f"[{timestamp}] IMEI:{imei1[:8]}... {product_name} {storage} | ModelID:{model_id} | UPC:{upc} ({durasi:.2f}s)")

        return [imei1, imei2, serial, part, product_name, storage, model_id, upc]
    except subprocess.CalledProcessError as e:
        error_str = str(e)
        if "-19" in error_str or "Pairing" in error_str or "Trust" in error_str:
            print(f"{YELLOW}[{timestamp}] ⚠️ {udid} not trusted. Tap 'Trust' on iPhone.{RESET}")
        else:
            print(f"{YELLOW}[{timestamp}] ❌ Extract failed {udid}: {error_str}{RESET}")
        return None

def shutdown_device(udid):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Shutting down {udid}...")
    try:
        subprocess.check_output(['idevicediagnostics', '-u', udid, 'shutdown'], timeout=10)
        print(f"[{timestamp}] ✅ {udid} shutdown OK.")
    except:
        print(f"[{timestamp}] ⚠️ Shutdown failed (normal if already off).")

# Load seen IMEI
seen_file = 'seen_imei.json'
seen_imei = set()
if os.path.exists(seen_file):
    with open(seen_file, 'r') as f:
        seen_imei = set(json.load(f))
    print(f"Loaded {len(seen_imei)} seen IMEIs")

print("\n" + "="*50)
print("🚀 iPhone IMEI Extractor + ModelID + UPC")
print("="*50)
print("1. Monitor (extract+save)")
print("2. Monitor (extract+save+shutdown)")
print("3. Exit")
choice = input("\nChoice (1/2/3): ")

if choice == '3':
    sys.exit(0)
if choice not in ['1', '2']:
    print("❌ Invalid choice.")
    sys.exit(1)

auto_shutdown = (choice == '2')

print(f"\n[🚀 START] Monitoring mode {'+SHUTDOWN' if auto_shutdown else ''}")
print("📱 Connect NEW device via USB. Ctrl+C to stop.")
print(f"📊 Seen IMEIs: {len(seen_imei)} | Excel: iphone_data.xlsx")

previous_udids = get_udids()
standby_dots = 0
excel_file = 'iphone_data.xlsx'
sheet_name = 'Data'

try:
    while True:
        current_udids = get_udids()
        
        # Detect disconnect
        disconnected = previous_udids - current_udids
        for disc in disconnected:
            print(f"\n[🔌] {disc} disconnected.")

        processed_new = False
        for udid in current_udids:
            info = extract_device_info(udid)
            if not info:
                continue

            imei1, *_ = info
            if imei1 == 'N/A':
                print(f"{YELLOW}[SKIP] No IMEI for {udid}{RESET}")
                continue

            if imei1 in seen_imei:
                print(f"{YELLOW}[SKIP] IMEI {imei1[:8]}... already saved.{RESET}")
                continue

            # ✅ SAVE TO EXCEL
            append_to_excel(excel_file, sheet_name, info)
            print(f"{GREEN}{BOLD}🎉 SAVED {udid}! Disconnect & connect NEXT device.{RESET}\n")

            seen_imei.add(imei1)
            with open(seen_file, 'w') as f:
                json.dump(list(seen_imei), f)

            processed_new = True
            if auto_shutdown:
                shutdown_device(udid)

        if processed_new:
            print(f"\n[✅ BATCH COMPLETE]")

        # Standby animation
        standby_dots = (standby_dots + 1) % 4
        sys.stdout.write(f"\r[{time.strftime('%H:%M:%S')}] ⏳ Standby{'.' * standby_dots}   ")
        sys.stdout.flush()

        previous_udids = current_udids
        time.sleep(5)

except KeyboardInterrupt:
    print(f"\n\n[🛑 STOPPED by user]")
    sys.exit(0)
