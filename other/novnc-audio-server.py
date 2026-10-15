#!/usr/bin/env python3
"""
==============================================================================
noVNC Audio Streamer for Termux Desktop
Streams PulseAudio desktop sound to any web browser with HTML5 Audio
Compatible with Chrome, Firefox, Safari, Edge on Laptop/PC/Tablet/Mobile
==============================================================================
"""

import os
import sys
import time
import socket
import struct
import threading
import argparse
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

AUDIO_PORT = 6081
PULSE_TCP_PORT = 4714
SAMPLE_RATE = 44100
CHANNELS = 2
BITS_PER_SAMPLE = 16

# Broadcast queue management
clients_lock = threading.Lock()
connected_clients = set()
broadcaster_running = True

def get_wav_header():
    """Build a 44-byte PCM WAV header for continuous live streaming"""
    byte_rate = SAMPLE_RATE * CHANNELS * (BITS_PER_SAMPLE // 8)
    block_align = CHANNELS * (BITS_PER_SAMPLE // 8)
    max_size = 0x7fffffff  # Max 32-bit signed int for live stream

    header = bytearray()
    header.extend(b'RIFF')
    header.extend(struct.pack('<I', max_size))
    header.extend(b'WAVE')
    header.extend(b'fmt ')
    header.extend(struct.pack('<I', 16))          # Subchunk1Size
    header.extend(struct.pack('<H', 1))           # AudioFormat (1 = PCM)
    header.extend(struct.pack('<H', CHANNELS))    # NumChannels
    header.extend(struct.pack('<I', SAMPLE_RATE)) # SampleRate
    header.extend(struct.pack('<I', byte_rate))   # ByteRate
    header.extend(struct.pack('<H', block_align)) # BlockAlign
    header.extend(struct.pack('<H', BITS_PER_SAMPLE)) # BitsPerSample
    header.extend(b'data')
    header.extend(struct.pack('<I', max_size))    # Subchunk2Size
    return bytes(header)

def audio_broadcaster():
    """Reads raw PCM from PulseAudio simple-protocol socket and broadcasts to HTTP clients"""
    global broadcaster_running
    while broadcaster_running:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', PULSE_TCP_PORT))
            s.settimeout(2.0)
            while broadcaster_running:
                try:
                    data = s.recv(4096)
                    if not data:
                        break
                    with clients_lock:
                        for q in list(connected_clients):
                            try:
                                q.put_nowait(data)
                            except Exception:
                                pass
                except socket.timeout:
                    continue
                except Exception:
                    break
            s.close()
        except Exception:
            time.sleep(1.0)

PLAYER_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Termux Desktop Audio Stream</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #181926;
            color: #cad3f5;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .card {
            background: #24273a;
            border: 1px solid #363a4f;
            border-radius: 16px;
            padding: 32px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
            text-align: center;
        }
        h1 { font-size: 20px; margin-bottom: 6px; color: #8aadf4; font-weight: 600; }
        p.subtitle { font-size: 13px; color: #a5adcb; margin-bottom: 24px; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            padding: 6px 14px;
            border-radius: 20px;
            background: #1e2030;
            border: 1px solid #363a4f;
            margin-bottom: 24px;
        }
        .dot { width: 10px; height: 10px; border-radius: 50%; background: #ed8796; }
        .dot.live { background: #a6da95; box-shadow: 0 0 10px #a6da95; }
        canvas {
            width: 100%;
            height: 90px;
            background: #1e2030;
            border-radius: 10px;
            margin-bottom: 24px;
            border: 1px solid #363a4f;
        }
        .controls { display: flex; flex-direction: column; gap: 18px; }
        .play-btn {
            background: linear-gradient(135deg, #8aadf4, #c6a0f6);
            color: #181926;
            border: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.2s;
        }
        .play-btn:active { transform: scale(0.98); }
        .play-btn:hover { opacity: 0.95; }
        .volume-box {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
            color: #a5adcb;
        }
        .volume-box input[type="range"] {
            flex: 1;
            accent-color: #8aadf4;
        }
        .tip { font-size: 12px; color: #6e738d; margin-top: 20px; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔊 Termux Desktop Audio</h1>
        <p class="subtitle">Live PulseAudio Stream ke Browser</p>
        
        <div class="status-badge">
            <span class="dot" id="dot"></span>
            <span id="status-text">Siap Diputar</span>
        </div>

        <canvas id="visualizer"></canvas>

        <div class="controls">
            <button class="play-btn" id="playBtn" onclick="togglePlay()">▶ Mulai Suara</button>
            <div class="volume-box">
                <span>🔈</span>
                <input type="range" id="volumeSlider" min="0" max="1" step="0.05" value="1" oninput="setVolume(this.value)">
                <span>🔊</span>
            </div>
        </div>

        <p class="tip">Biarkan tab ini tetap terbuka di latar belakang saat menggunakan noVNC agar suara desktop terus terdengar di laptop.</p>
    </div>

    <script>
        let audio = null;
        let isPlaying = false;
        let audioCtx = null;
        let analyser = null;
        let source = null;

        const playBtn = document.getElementById('playBtn');
        const statusText = document.getElementById('status-text');
        const dot = document.getElementById('dot');
        const canvas = document.getElementById('visualizer');
        const canvasCtx = canvas.getContext('2d');

        function setupVisualizer() {
            if (audioCtx) return;
            try {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                analyser = audioCtx.createAnalyser();
                analyser.fftSize = 64;
                source = audioCtx.createMediaElementSource(audio);
                source.connect(analyser);
                analyser.connect(audioCtx.destination);
                draw();
            } catch (e) {
                console.log("Visualizer:", e);
            }
        }

        function draw() {
            requestAnimationFrame(draw);
            if (!analyser) return;
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            analyser.getByteFrequencyData(dataArray);

            canvasCtx.fillStyle = '#1e2030';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);

            const barWidth = (canvas.width / bufferLength) * 1.5;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                const barHeight = (dataArray[i] / 255) * canvas.height;
                canvasCtx.fillStyle = '#8aadf4';
                canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                x += barWidth + 2;
            }
        }

        function togglePlay() {
            if (!audio) {
                audio = new Audio('/audio.wav?t=' + Date.now());
                audio.crossOrigin = "anonymous";
                setupVisualizer();
            }

            if (!isPlaying) {
                if (audioCtx && audioCtx.state === 'suspended') {
                    audioCtx.resume();
                }
                audio.play().then(() => {
                    isPlaying = true;
                    playBtn.textContent = '⏸ Jeda Suara';
                    statusText.textContent = 'Streaming Aktif';
                    dot.classList.add('live');
                }).catch(err => {
                    alert("Gagal memutar audio: " + err);
                });
            } else {
                audio.pause();
                audio = null;
                isPlaying = false;
                playBtn.textContent = '▶ Mulai Suara';
                statusText.textContent = 'Dijeda';
                dot.classList.remove('live');
            }
        }

        function setVolume(val) {
            if (audio) audio.volume = val;
        }

        window.addEventListener('resize', () => {
            canvas.width = canvas.clientWidth;
            canvas.height = canvas.clientHeight;
        });
        canvas.width = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class AudioHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path.startswith('/audio.wav'):
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()

    def do_GET(self):
        if self.path.startswith('/audio.wav'):
            self.send_response(200)
            self.send_header('Content-Type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            import queue
            client_q = queue.Queue(maxsize=50)
            with clients_lock:
                connected_clients.add(client_q)

            try:
                # Send WAV Header
                self.wfile.write(get_wav_header())
                self.wfile.flush()

                # Stream audio chunks continuously
                while broadcaster_running:
                    try:
                        chunk = client_q.get(timeout=2.0)
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except queue.Empty:
                        continue
                    except (BrokenPipeError, ConnectionResetError):
                        break
            except Exception:
                pass
            finally:
                with clients_lock:
                    connected_clients.discard(client_q)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(PLAYER_HTML.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(PLAYER_HTML.encode('utf-8'))

    def log_message(self, format, *args):
        # Silence routine access logs
        return

def main():
    global AUDIO_PORT, PULSE_TCP_PORT
    parser = argparse.ArgumentParser(description="noVNC Audio Streamer")
    parser.add_argument("--port", type=int, default=AUDIO_PORT, help="Port to listen on (default: 6081)")
    parser.add_argument("--pulse-port", type=int, default=PULSE_TCP_PORT, help="PulseAudio TCP port (default: 4714)")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS/TLS encryption")
    parser.add_argument("--cert", type=str, default="", help="Path to SSL certificate PEM file")
    args = parser.parse_args()

    AUDIO_PORT = args.port
    PULSE_TCP_PORT = args.pulse_port

    t = threading.Thread(target=audio_broadcaster, daemon=True)
    t.start()

    server = ThreadedHTTPServer(('0.0.0.0', AUDIO_PORT), AudioHandler)

    if args.ssl and args.cert and os.path.exists(args.cert):
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=args.cert)
            server.socket = ctx.wrap_socket(server.socket, server_side=True)
        except Exception as e:
            sys.stderr.write(f"[!] Gagal mengaktifkan SSL audio server: {e}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        global broadcaster_running
        broadcaster_running = False
        server.server_close()

if __name__ == '__main__':
    main()
