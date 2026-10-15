#!/usr/bin/env python3
"""
patch-novnc-audio.py
Ensures noVNC web interface includes single-tab Audio streaming controls and SVG icon.
"""

import os
import sys

AUDIO_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="25" height="25" viewBox="0 0 25 25">
  <path fill="#ffffff" d="M3 9v7h4l5 5V4L7 9H3zm13.5 3.5c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
</svg>
"""

AUDIO_HTML_SNIPPET = """
            <!-- Audio (Suara Desktop) -->
            <input type="image" alt="Audio" src="app/images/audio.svg"
                id="noVNC_audio_button" class="noVNC_button"
                title="Desktop Audio (Suara)">
            <div class="noVNC_vcenter">
            <div id="noVNC_audio" class="noVNC_panel">
                <div class="noVNC_heading">
                    <img alt="" src="app/images/audio.svg"> Desktop Audio
                </div>
                <div style="padding: 12px; min-width: 210px; color:#ddd; font-family:sans-serif;">
                    <button id="noVNC_audio_toggle_btn" type="button" style="width:100%; padding:9px 12px; margin-bottom:12px; background:#2e7d32; color:#fff; border:none; border-radius:6px; cursor:pointer; font-weight:600; font-size:13px; display:flex; align-items:center; justify-content:center; gap:6px;">
                        <span id="noVNC_audio_btn_icon">▶</span> <span id="noVNC_audio_btn_label">Mulai Suara</span>
                    </button>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; font-size:12px; color:#bbb;">
                        <span>Volume:</span>
                        <span id="noVNC_audio_volume_label">100%</span>
                    </div>
                    <input type="range" id="noVNC_audio_volume_slider" min="0" max="1" step="0.05" value="1" style="width:100%; margin-bottom:10px; cursor:pointer;">
                    <div id="noVNC_audio_status_text" style="font-size:11px; text-align:center; color:#888;">
                        Status: Siap (Port 6081)
                    </div>
                </div>
            </div>
            </div>
"""

AUDIO_SCRIPT_SNIPPET = """
    <!-- noVNC Audio Stream Controller (Single-Tab Integration) -->
    <script>
    (function() {
        let audio = null;
        let isPlaying = false;
        function initAudioUI() {
            const btn = document.getElementById('noVNC_audio_button');
            const panel = document.getElementById('noVNC_audio');
            const toggleBtn = document.getElementById('noVNC_audio_toggle_btn');
            const btnIcon = document.getElementById('noVNC_audio_btn_icon');
            const btnLabel = document.getElementById('noVNC_audio_btn_label');
            const volSlider = document.getElementById('noVNC_audio_volume_slider');
            const volLabel = document.getElementById('noVNC_audio_volume_label');
            const statusText = document.getElementById('noVNC_audio_status_text');

            if (!btn || !panel || !toggleBtn) return;

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const isOpen = panel.classList.contains('noVNC_open');
                document.querySelectorAll('.noVNC_panel').forEach(p => p.classList.remove('noVNC_open'));
                document.querySelectorAll('.noVNC_button').forEach(b => b.classList.remove('noVNC_selected'));
                if (!isOpen) {
                    panel.classList.add('noVNC_open');
                    btn.classList.add('noVNC_selected');
                }
            });

            document.addEventListener('click', function(e) {
                if (!panel.contains(e.target) && !btn.contains(e.target)) {
                    panel.classList.remove('noVNC_open');
                    btn.classList.remove('noVNC_selected');
                }
            });

            toggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (!isPlaying) {
                    startAudio();
                } else {
                    stopAudio();
                }
            });

            if (volSlider && volLabel) {
                volSlider.addEventListener('input', function() {
                    const v = parseFloat(this.value);
                    volLabel.textContent = Math.round(v * 100) + '%';
                    if (audio) audio.volume = v;
                });
            }

            function startAudio() {
                statusText.textContent = 'Menghubungkan ke server audio...';
                statusText.style.color = '#e0af68';
                const proto = window.location.protocol;
                const host = window.location.hostname;
                const audioUrl = `${proto}//${host}:6081/audio.wav?t=` + Date.now();

                if (audio) {
                    audio.pause();
                    audio = null;
                }

                audio = new Audio(audioUrl);
                audio.crossOrigin = 'anonymous';
                if (volSlider) audio.volume = parseFloat(volSlider.value);

                audio.play().then(() => {
                    isPlaying = true;
                    btnIcon.textContent = '⏸';
                    btnLabel.textContent = 'Jeda Suara';
                    toggleBtn.style.background = '#c53b3b';
                    statusText.textContent = '● Suara Aktif (Live)';
                    statusText.style.color = '#9ece6a';
                    btn.style.filter = 'drop-shadow(0 0 5px #9ece6a)';
                }).catch(err => {
                    isPlaying = false;
                    btnIcon.textContent = '▶';
                    btnLabel.textContent = 'Mulai Suara';
                    toggleBtn.style.background = '#2e7d32';
                    statusText.textContent = 'Gagal memutar (Pastikan port 6081 aktif)';
                    statusText.style.color = '#f7768e';
                    console.error('Audio play error:', err);
                });

                audio.onerror = function() {
                    isPlaying = false;
                    btnIcon.textContent = '▶';
                    btnLabel.textContent = 'Mulai Suara';
                    toggleBtn.style.background = '#2e7d32';
                    statusText.textContent = 'Koneksi audio terputus';
                    statusText.style.color = '#f7768e';
                    btn.style.filter = 'none';
                };
            }

            function stopAudio() {
                if (audio) {
                    audio.pause();
                    audio = null;
                }
                isPlaying = false;
                btnIcon.textContent = '▶';
                btnLabel.textContent = 'Mulai Suara';
                toggleBtn.style.background = '#2e7d32';
                statusText.textContent = 'Status: Dijeda';
                statusText.style.color = '#888';
                btn.style.filter = 'none';
            }
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initAudioUI);
        } else {
            initAudioUI();
        }
    })();
    </script>
"""

def patch_web_dir(web_dir):
    if not os.path.isdir(web_dir):
        return False

    # 1. Ensure audio.svg exists in app/images/
    img_dir = os.path.join(web_dir, "app", "images")
    if os.path.isdir(img_dir):
        svg_path = os.path.join(img_dir, "audio.svg")
        if not os.path.isfile(svg_path):
            try:
                with open(svg_path, "w", encoding="utf-8") as f:
                    f.write(AUDIO_SVG.strip() + "\n")
                print(f"[✓] Created audio.svg in {img_dir}")
            except Exception as e:
                print(f"[!] Warning: Cannot write {svg_path}: {e}")

    # 2. Patch vnc.html
    vnc_html = os.path.join(web_dir, "vnc.html")
    if not os.path.isfile(vnc_html):
        return False

    try:
        with open(vnc_html, "r", encoding="utf-8") as f:
            content = f.read()

        if "id=\"noVNC_audio_button\"" in content:
            return True  # Already patched

        # Insert button before settings button
        target_marker = "<!-- Settings -->"
        if target_marker in content:
            content = content.replace(target_marker, AUDIO_HTML_SNIPPET.strip() + "\n\n            " + target_marker)
        elif "id=\"noVNC_settings_button\"" in content:
            idx = content.find("id=\"noVNC_settings_button\"")
            # find previous input tag
            input_start = content.rfind("<input", 0, idx)
            content = content[:input_start] + AUDIO_HTML_SNIPPET.strip() + "\n\n            " + content[input_start:]

        # Insert script before </body>
        if "</body>" in content:
            content = content.replace("</body>", AUDIO_SCRIPT_SNIPPET.strip() + "\n</body>")

        with open(vnc_html, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[✓] Successfully integrated Single-Tab Audio Player into {vnc_html}")
        return True
    except Exception as e:
        print(f"[!] Warning: Failed to patch {vnc_html}: {e}")
        return False

def main():
    candidate_dirs = [
        "/data/data/com.termux/files/usr/share/novnc",
        "/usr/share/novnc"
    ]
    for d in candidate_dirs:
        patch_web_dir(d)

if __name__ == "__main__":
    main()
