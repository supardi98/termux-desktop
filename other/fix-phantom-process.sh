#!/system/bin/sh
# ==============================================================================
# Script: fix-phantom-process.sh
# Description: Disable Android Phantom Process Killer and child process limits
# Compatible: Android 12, 12L, 13, 14, 15, 16+ (including ColorOS / OxygenOS / HyperOS)
# ==============================================================================

# If running as standard user, try elevating with su
if [ "$(id -u 2>/dev/null)" != "0" ]; then
    if command -v su >/dev/null 2>&1 || [ -x /system/bin/su ]; then
        echo "[i] Meminta akses root (Superuser)..."
        exec su -c "sh $0 $@"
    else
        echo "[!] Akses root tidak ditemukan."
        echo "[i] Jalankan perintah berikut melalui ADB di komputer atau Wireless Debugging:"
        echo "    adb shell settings put global settings_enable_monitor_phantom_procs false"
        echo "    adb shell /system/bin/device_config set_sync_disabled_for_tests persistent"
        echo "    adb shell /system/bin/device_config put activity_manager max_phantom_processes 2147483647"
        exit 1
    fi
fi

echo "======================================================"
echo " Menerapkan konfigurasi Anti Phantom Process Killer..."
echo "======================================================"

# 1. Matikan monitor proses hantu Android (AOSP)
settings put global settings_enable_monitor_phantom_procs false 2>/dev/null

# 2. Kunci konfigurasi agar tidak di-override oleh cloud/system sync
/system/bin/device_config set_sync_disabled_for_tests persistent 2>/dev/null

# 3. Naikkan batas child processes ke kapasitas maksimal (2147483647)
/system/bin/device_config put activity_manager max_phantom_processes 2147483647 2>/dev/null

# 4. Set persistent system property flag override (Android 14+)
setprop persist.sys.fflag.override.settings_enable_monitor_phantom_procs false 2>/dev/null

echo ""
echo "=== HASIL VERIFIKASI ==="
echo -n "Status monitor phantom procs : "
settings get global settings_enable_monitor_phantom_procs 2>/dev/null || echo "Unknown"

echo -n "Batas max phantom processes  : "
/system/bin/device_config get activity_manager max_phantom_processes 2>/dev/null || echo "Unknown"
echo "========================"
echo ""
echo "[✓] Sukses! Phantom process killer berhasil dimatikan secara permanen."
