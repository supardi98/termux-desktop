#!/usr/bin/env python3
"""
patch-novnc-clipboard.py
Enables automatic two-way clipboard synchronization between Laptop OS and X11 Desktop
in noVNC without requiring manual side drawer interaction.
"""

import os
import sys

CLIPBOARD_SCRIPT_SNIPPET = """
    <!-- noVNC Auto Two-Way Clipboard Sync -->
    <script>
    (function() {
        let lastReceived = "";
        let lastSent = "";
        let isSyncing = false;

        function showClipboardToast(msg) {
            let toast = document.getElementById('noVNC_clipboard_toast');
            if (!toast) {
                toast = document.createElement('div');
                toast.id = 'noVNC_clipboard_toast';
                toast.style.cssText = 'position:fixed; bottom:20px; right:20px; background:rgba(30,30,46,0.92); color:#cdd6f4; padding:8px 16px; border-radius:8px; font-family:sans-serif; font-size:12px; z-index:99999; box-shadow:0 4px 14px rgba(0,0,0,0.45); border:1px solid #45475a; transition:opacity 0.25s ease; pointer-events:none; opacity:0; display:flex; align-items:center; gap:8px;';
                document.body.appendChild(toast);
            }
            toast.textContent = msg;
            toast.style.opacity = '1';
            clearTimeout(toast._timer);
            toast._timer = setTimeout(function() { toast.style.opacity = '0'; }, 2200);
        }

        function syncLaptopToDesktop() {
            if (isSyncing || !navigator.clipboard || !navigator.clipboard.readText) return;
            if (!window.UI || !window.UI.rfb || !window.UI.rfb.clipboardPasteFrom) return;

            isSyncing = true;
            navigator.clipboard.readText().then(function(text) {
                isSyncing = false;
                if (!text || text === lastSent || text === lastReceived) return;
                lastSent = text;
                window.UI.rfb.clipboardPasteFrom(text);
                const preview = text.trim().substring(0, 24) + (text.length > 24 ? '...' : '');
                showClipboardToast('📋 Laptop → Desktop: ' + preview);
            }).catch(function() {
                isSyncing = false;
            });
        }

        function initClipboardSync() {
            // 1. Sync on window focus and tab visibility change
            window.addEventListener('focus', syncLaptopToDesktop);
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden) syncLaptopToDesktop();
            });

            // 2. Sync on canvas click/interaction
            const canvas = document.getElementById('noVNC_canvas') || document.body;
            canvas.addEventListener('pointerdown', syncLaptopToDesktop, { passive: true });

            // 3. Direct Paste (Ctrl+V) handler
            window.addEventListener('paste', function(e) {
                if (!window.UI || !window.UI.rfb || !window.UI.rfb.clipboardPasteFrom) return;
                const text = (e.clipboardData || window.clipboardData).getData('text');
                if (text && text !== lastSent) {
                    lastSent = text;
                    window.UI.rfb.clipboardPasteFrom(text);
                    const preview = text.trim().substring(0, 24) + (text.length > 24 ? '...' : '');
                    showClipboardToast('📋 Ditempelkan: ' + preview);
                }
            });

            // 4. Hook UI.clipboardReceive to sync Desktop -> Laptop
            function hookUIReceive() {
                if (!window.UI || !window.UI.clipboardReceive) {
                    setTimeout(hookUIReceive, 200);
                    return;
                }
                const originalReceive = window.UI.clipboardReceive;
                window.UI.clipboardReceive = function(e) {
                    if (originalReceive) originalReceive.call(this, e);
                    if (e && e.detail && e.detail.text) {
                        const text = e.detail.text;
                        if (text && text !== lastSent && text !== lastReceived) {
                            lastReceived = text;
                            if (navigator.clipboard && navigator.clipboard.writeText) {
                                navigator.clipboard.writeText(text).then(function() {
                                    const preview = text.trim().substring(0, 24) + (text.length > 24 ? '...' : '');
                                    showClipboardToast('📋 Desktop → Laptop: ' + preview);
                                }).catch(function() {});
                            }
                        }
                    }
                };
            }
            hookUIReceive();
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initClipboardSync);
        } else {
            initClipboardSync();
        }
    })();
    </script>
"""

def patch_vnc_file(vnc_html):
    if not os.path.isfile(vnc_html):
        return False

    try:
        with open(vnc_html, "r", encoding="utf-8") as f:
            content = f.read()

        if "noVNC Auto Two-Way Clipboard Sync" in content:
            print(f"[i] Already patched: {vnc_html}")
            return True

        if "</body>" in content:
            content = content.replace("</body>", CLIPBOARD_SCRIPT_SNIPPET.strip() + "\n</body>")
        else:
            content = content + "\n" + CLIPBOARD_SCRIPT_SNIPPET.strip()

        with open(vnc_html, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[✓] Successfully integrated Auto Clipboard Sync into {vnc_html}")
        return True
    except Exception as e:
        print(f"[!] Error patching {vnc_html}: {e}")
        return False

def main():
    candidate_files = [
        "/data/data/com.termux/files/usr/share/novnc/vnc.html",
        "/usr/share/novnc/vnc.html"
    ]
    for f in candidate_files:
        patch_vnc_file(f)

if __name__ == "__main__":
    main()
