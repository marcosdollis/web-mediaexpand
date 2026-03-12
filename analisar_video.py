"""
Analisa metadados completos de um vídeo.
Tenta ffprobe primeiro; se não disponível, usa parser MP4 puro em Python.
Mostra todas as informações relevantes para compatibilidade Fire TV Stick.
"""
import subprocess
import json
import sys
import os
import struct


# ═══════════════════════════════════════════════════════════════════════════════
#  MP4 BOX PARSER (puro Python, sem dependências externas)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_mp4_boxes(f, end, depth=0):
    """Recursivamente parseia boxes MP4."""
    boxes = []
    while f.tell() < end:
        box_start = f.tell()
        header = f.read(8)
        if len(header) < 8:
            break
        size, box_type = struct.unpack('>I4s', header)
        box_type = box_type.decode('latin-1', errors='replace')
        if size == 1:  # extended size
            ext = f.read(8)
            if len(ext) < 8:
                break
            size = struct.unpack('>Q', ext)[0]
        elif size == 0:
            size = end - box_start

        box_end = box_start + size
        if box_end > end:
            box_end = end

        box = {'type': box_type, 'offset': box_start, 'size': size}

        container_boxes = ('moov', 'trak', 'mdia', 'minf', 'stbl', 'dinf',
                           'edts', 'udta', 'meta', 'ilst', 'sinf', 'schi')

        if box_type in container_boxes:
            # Containers: parse children
            if box_type == 'meta':
                f.read(4)  # skip version+flags
                box['children'] = parse_mp4_boxes(f, box_end, depth + 1)
            else:
                box['children'] = parse_mp4_boxes(f, box_end, depth + 1)
        elif box_type == 'mvhd':
            box['data'] = parse_mvhd(f, box_end)
        elif box_type == 'tkhd':
            box['data'] = parse_tkhd(f, box_end)
        elif box_type == 'hdlr':
            box['data'] = parse_hdlr(f, box_end)
        elif box_type == 'stsd':
            box['data'] = parse_stsd(f, box_end)
        elif box_type == 'avcC':
            box['data'] = parse_avcc(f, box_end)
        elif box_type == 'esds':
            box['data'] = parse_esds(f, box_end)
        elif box_type == 'mdhd':
            box['data'] = parse_mdhd(f, box_end)
        elif box_type == 'stts':
            box['data'] = parse_stts(f, box_end)
        elif box_type == 'colr':
            box['data'] = parse_colr(f, box_end)

        boxes.append(box)
        f.seek(box_end)
    return boxes


def parse_mvhd(f, end):
    ver = struct.unpack('>B', f.read(1))[0]
    f.read(3)  # flags
    if ver == 0:
        ctime, mtime, timescale, duration = struct.unpack('>IIII', f.read(16))
    else:
        ctime, mtime = struct.unpack('>QQ', f.read(16))
        timescale, duration = struct.unpack('>IQ', f.read(12))
    return {'version': ver, 'timescale': timescale, 'duration': duration,
            'duration_seconds': duration / timescale if timescale else 0}


def parse_tkhd(f, end):
    ver = struct.unpack('>B', f.read(1))[0]
    flags = f.read(3)
    if ver == 0:
        f.read(8)  # ctime, mtime
        track_id = struct.unpack('>I', f.read(4))[0]
        f.read(4)  # reserved
        duration = struct.unpack('>I', f.read(4))[0]
    else:
        f.read(16)
        track_id = struct.unpack('>I', f.read(4))[0]
        f.read(4)
        duration = struct.unpack('>Q', f.read(8))[0]
    f.read(8)  # reserved
    layer, alt_group = struct.unpack('>hh', f.read(4))
    volume = struct.unpack('>h', f.read(2))[0]
    f.read(2)  # reserved
    matrix = struct.unpack('>9i', f.read(36))
    width_fixed, height_fixed = struct.unpack('>II', f.read(8))
    width = width_fixed >> 16
    height = height_fixed >> 16
    # Extract rotation from matrix
    a, b = matrix[0] / 65536.0, matrix[1] / 65536.0
    c, d = matrix[3] / 65536.0, matrix[4] / 65536.0
    import math
    rotation = round(math.degrees(math.atan2(b, a))) % 360
    return {'track_id': track_id, 'duration': duration,
            'width': width, 'height': height, 'rotation': rotation,
            'volume': volume / 256.0}


def parse_hdlr(f, end):
    f.read(4)  # version + flags
    f.read(4)  # pre_defined
    handler_type = f.read(4).decode('latin-1', errors='replace')
    f.read(12)  # reserved
    remaining = end - f.tell()
    name = f.read(remaining).decode('utf-8', errors='replace').strip('\x00') if remaining > 0 else ''
    return {'handler_type': handler_type, 'name': name}


def parse_stsd(f, end):
    f.read(4)  # version + flags
    entry_count = struct.unpack('>I', f.read(4))[0]
    entries = []
    for _ in range(entry_count):
        if f.tell() >= end:
            break
        estart = f.tell()
        edata = f.read(8)
        if len(edata) < 8:
            break
        esize, etype = struct.unpack('>I4s', edata)
        etype = etype.decode('latin-1', errors='replace')
        entry = {'type': etype, 'size': esize}

        # Video sample entry (avc1, hvc1, etc.)
        if etype in ('avc1', 'avc3', 'hvc1', 'hev1', 'mp4v', 'encv'):
            f.read(6)  # reserved
            f.read(2)  # data_ref_index
            f.read(2)  # pre_defined
            f.read(2)  # reserved
            f.read(12) # pre_defined
            w, h = struct.unpack('>HH', f.read(4))
            hres, vres = struct.unpack('>II', f.read(8))
            f.read(4)  # reserved
            frame_count = struct.unpack('>H', f.read(2))[0]
            compressor = f.read(32)
            depth = struct.unpack('>H', f.read(2))[0]
            f.read(2)  # pre_defined
            entry['width'] = w
            entry['height'] = h
            entry['h_resolution'] = hres >> 16
            entry['v_resolution'] = vres >> 16
            entry['depth'] = depth
            # Parse child boxes (avcC, hvcC, colr, etc.)
            eend = estart + esize
            entry['children'] = parse_mp4_boxes(f, eend, depth=3)

        # Audio sample entry (mp4a, etc.)
        elif etype in ('mp4a', 'enca', 'ac-3', 'ec-3'):
            f.read(6)  # reserved
            f.read(2)  # data_ref_index
            f.read(8)  # reserved
            channels = struct.unpack('>H', f.read(2))[0]
            sample_size = struct.unpack('>H', f.read(2))[0]
            f.read(4)  # pre_defined + reserved
            sample_rate_fixed = struct.unpack('>I', f.read(4))[0]
            sample_rate = sample_rate_fixed >> 16
            entry['channels'] = channels
            entry['sample_size'] = sample_size
            entry['sample_rate'] = sample_rate
            eend = estart + esize
            entry['children'] = parse_mp4_boxes(f, eend, depth=3)
        else:
            f.seek(estart + esize)

        entries.append(entry)
    return {'entry_count': entry_count, 'entries': entries}


def parse_avcc(f, end):
    """Parse AVC Decoder Configuration Record."""
    f.read(4)  # skip if fullbox style (version+flags) — some have it, some don't
    pos = f.tell()
    remaining = end - pos
    if remaining < 4:
        return {}
    # Actually, avcC is NOT a fullbox. Let me re-read from the right position.
    f.seek(pos - 4)
    remaining = end - f.tell()
    if remaining < 7:
        return {}
    data = f.read(min(remaining, 64))
    config_version = data[0]
    avc_profile = data[1]
    profile_compat = data[2]
    avc_level = data[3]

    profile_names = {
        66: 'Baseline', 77: 'Main', 88: 'Extended',
        100: 'High', 110: 'High 10', 122: 'High 4:2:2',
        244: 'High 4:4:4 Predictive', 44: 'CAVLC 4:4:4 Intra'
    }

    return {
        'config_version': config_version,
        'avc_profile_idc': avc_profile,
        'profile_name': profile_names.get(avc_profile, f'Unknown ({avc_profile})'),
        'profile_compatibility': profile_compat,
        'avc_level_idc': avc_level,
        'level': f'{avc_level / 10:.1f}'
    }


def parse_esds(f, end):
    """Parse elementary stream descriptor — mainly for audio codec info."""
    f.read(4)  # version + flags
    # Just note that it exists
    return {'present': True}


def parse_mdhd(f, end):
    ver = struct.unpack('>B', f.read(1))[0]
    f.read(3)
    if ver == 0:
        f.read(8)  # ctime, mtime
        timescale, duration = struct.unpack('>II', f.read(8))
    else:
        f.read(16)
        timescale = struct.unpack('>I', f.read(4))[0]
        duration = struct.unpack('>Q', f.read(8))[0]
    lang = struct.unpack('>H', f.read(2))[0]
    return {'timescale': timescale, 'duration': duration,
            'duration_seconds': duration / timescale if timescale else 0}


def parse_stts(f, end):
    """Time-to-sample box — useful for detecting VFR."""
    f.read(4)  # version + flags
    entry_count = struct.unpack('>I', f.read(4))[0]
    entries = []
    for _ in range(min(entry_count, 50)):  # limit
        if f.tell() + 8 > end:
            break
        count, delta = struct.unpack('>II', f.read(8))
        entries.append({'sample_count': count, 'sample_delta': delta})
    return {'entry_count': entry_count, 'entries': entries}


def parse_colr(f, end):
    """Color information box."""
    remaining = end - f.tell()
    if remaining < 4:
        return {}
    color_type = f.read(4).decode('latin-1', errors='replace')
    result = {'color_type': color_type}
    if color_type == 'nclx' and remaining >= 11:
        primaries, transfer, matrix = struct.unpack('>HHH', f.read(6))
        color_names = {1: 'bt709', 5: 'bt601-625', 6: 'bt601-525', 9: 'bt2020'}
        result['color_primaries'] = color_names.get(primaries, f'({primaries})')
        result['transfer'] = color_names.get(transfer, f'({transfer})')
        result['matrix'] = color_names.get(matrix, f'({matrix})')
    return result


def find_box(boxes, box_type):
    """Recursively find a box by type."""
    for box in boxes:
        if box['type'] == box_type:
            return box
        if 'children' in box:
            found = find_box(box['children'], box_type)
            if found:
                return found
        if 'data' in box and isinstance(box['data'], dict) and 'entries' in box.get('data', {}):
            for entry in box['data']['entries']:
                if 'children' in entry:
                    found = find_box(entry['children'], box_type)
                    if found:
                        return found
    return None


def find_all_boxes(boxes, box_type):
    """Recursively find all boxes of a type."""
    result = []
    for box in boxes:
        if box['type'] == box_type:
            result.append(box)
        if 'children' in box:
            result.extend(find_all_boxes(box['children'], box_type))
        if 'data' in box and isinstance(box['data'], dict) and 'entries' in box.get('data', {}):
            for entry in box['data']['entries']:
                if 'children' in entry:
                    result.extend(find_all_boxes(entry['children'], box_type))
    return result


def find_tracks(boxes):
    """Extract track info from parsed boxes."""
    tracks = []
    moov = find_box(boxes, 'moov')
    if not moov or 'children' not in moov:
        return tracks

    for box in moov['children']:
        if box['type'] != 'trak':
            continue
        track = {}

        # tkhd
        tkhd = find_box([box], 'tkhd')
        if tkhd and 'data' in tkhd:
            track['tkhd'] = tkhd['data']

        # hdlr
        hdlr = find_box([box], 'hdlr')
        if hdlr and 'data' in hdlr:
            track['handler'] = hdlr['data']['handler_type']

        # mdhd
        mdhd = find_box([box], 'mdhd')
        if mdhd and 'data' in mdhd:
            track['mdhd'] = mdhd['data']

        # stsd
        stsd = find_box([box], 'stsd')
        if stsd and 'data' in stsd:
            track['stsd'] = stsd['data']

        # stts
        stts = find_box([box], 'stts')
        if stts and 'data' in stts:
            track['stts'] = stts['data']

        # avcC
        avcc = find_box([box], 'avcC')
        if avcc and 'data' in avcc:
            track['avcC'] = avcc['data']

        # colr
        colr = find_box([box], 'colr')
        if colr and 'data' in colr:
            track['colr'] = colr['data']

        tracks.append(track)
    return tracks


# ═══════════════════════════════════════════════════════════════════════════════
#  DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════

def analisar_video_python(caminho):
    """Pure Python MP4 analysis — no ffprobe needed."""
    tamanho = os.path.getsize(caminho)

    with open(caminho, 'rb') as f:
        f.seek(0, 2)
        fsize = f.tell()
        f.seek(0)
        boxes = parse_mp4_boxes(f, fsize)

    mvhd = find_box(boxes, 'mvhd')
    tracks = find_tracks(boxes)

    print(f"\n{'─' * 40}")
    print("  CONTAINER")
    print(f"{'─' * 40}")
    print(f"  Formato:      MP4 (ISO Base Media)")
    if mvhd and 'data' in mvhd:
        d = mvhd['data']
        print(f"  Duração:      {d['duration_seconds']:.2f}s")
        print(f"  Timescale:    {d['timescale']}")
    print(f"  Tracks:       {len(tracks)}")
    bitrate_total = int(tamanho * 8 / mvhd['data']['duration_seconds']) if mvhd and mvhd['data']['duration_seconds'] > 0 else 0
    print(f"  Bitrate total:{bitrate_total / 1000:.0f} kbps")

    for i, t in enumerate(tracks):
        handler = t.get('handler', '????')
        is_video = handler == 'vide'
        is_audio = handler == 'soun'

        print(f"\n{'─' * 40}")
        print(f"  TRACK #{i} — {'VIDEO' if is_video else 'AUDIO' if is_audio else handler.upper()}")
        print(f"{'─' * 40}")

        if is_video:
            stsd = t.get('stsd', {})
            entries = stsd.get('entries', [])
            codec_type = entries[0]['type'] if entries else '?'
            w = entries[0].get('width', '?') if entries else '?'
            h = entries[0].get('height', '?') if entries else '?'

            tkhd = t.get('tkhd', {})
            rotation = tkhd.get('rotation', 0)
            tkhd_w = tkhd.get('width', 0)
            tkhd_h = tkhd.get('height', 0)

            codec_names = {
                'avc1': 'H.264 / AVC', 'avc3': 'H.264 / AVC',
                'hvc1': 'H.265 / HEVC', 'hev1': 'H.265 / HEVC',
                'mp4v': 'MPEG-4 Part 2', 'vp09': 'VP9', 'av01': 'AV1'
            }

            avcc = t.get('avcC', {})
            profile_name = avcc.get('profile_name', '?')
            level = avcc.get('level', '?')
            profile_idc = avcc.get('avc_profile_idc', '?')

            print(f"  Codec:        {codec_type} ({codec_names.get(codec_type, '?')})")
            if avcc:
                print(f"  Profile:      {profile_name} (idc={profile_idc})")
                print(f"  Level:        {level}")
            print(f"  Resolução:    {w}x{h}  (stsd)")
            print(f"  Track size:   {tkhd_w}x{tkhd_h}  (tkhd)")
            print(f"  Rotação:      {rotation}°")

            # Depth
            depth = entries[0].get('depth', '?') if entries else '?'
            print(f"  Bit depth:    {depth}")

            # FPS from stts
            stts = t.get('stts', {})
            mdhd = t.get('mdhd', {})
            timescale = mdhd.get('timescale', 0)
            stts_entries = stts.get('entries', [])
            stts_count = stts.get('entry_count', 0)

            if timescale > 0 and stts_entries:
                # CFR vs VFR
                unique_deltas = set(e['sample_delta'] for e in stts_entries)
                total_samples = sum(e['sample_count'] for e in stts_entries)
                total_ticks = sum(e['sample_count'] * e['sample_delta'] for e in stts_entries)
                avg_fps = total_samples * timescale / total_ticks if total_ticks > 0 else 0

                if len(unique_deltas) == 1:
                    delta = stts_entries[0]['sample_delta']
                    fps = timescale / delta if delta > 0 else 0
                    print(f"  FPS:          {fps:.3f}  (CFR - constant)")
                else:
                    fps_values = [timescale / e['sample_delta'] for e in stts_entries if e['sample_delta'] > 0]
                    min_fps = min(fps_values) if fps_values else 0
                    max_fps = max(fps_values) if fps_values else 0
                    print(f"  FPS (avg):    {avg_fps:.3f}  (VFR - VARIABLE!)")
                    print(f"  FPS range:    {min_fps:.1f} – {max_fps:.1f}")
                    print(f"  stts entries: {stts_count} (>1 = variable frame rate)")
                print(f"  Total frames: {total_samples}")
            else:
                print(f"  FPS:          ? (no stts/mdhd)")

            # Color
            colr = t.get('colr', {})
            if colr:
                print(f"  Color type:   {colr.get('color_type', '?')}")
                if 'color_primaries' in colr:
                    print(f"  Primaries:    {colr['color_primaries']}")
                    print(f"  Transfer:     {colr['transfer']}")
                    print(f"  Matrix:       {colr['matrix']}")

            # Orientação final
            # Considerar rotação: se rotation=90 ou 270, w e h do vídeo real estão invertidos
            real_w, real_h = int(w), int(h)
            if rotation in (90, 270):
                real_w, real_h = real_h, real_w
            orient = "VERTICAL (retrato)" if real_h > real_w else "HORIZONTAL (paisagem)"
            print(f"\n  >>> Resolução real (com rotação): {real_w}x{real_h}")
            print(f"  >>> Orientação detectada: {orient}")

        elif is_audio:
            stsd = t.get('stsd', {})
            entries = stsd.get('entries', [])
            codec_type = entries[0]['type'] if entries else '?'
            channels = entries[0].get('channels', '?') if entries else '?'
            sample_rate = entries[0].get('sample_rate', '?') if entries else '?'
            sample_size = entries[0].get('sample_size', '?') if entries else '?'

            codec_names = {'mp4a': 'AAC', 'ac-3': 'AC-3', 'ec-3': 'E-AC-3'}
            print(f"  Codec:        {codec_type} ({codec_names.get(codec_type, '?')})")
            print(f"  Sample rate:  {sample_rate} Hz")
            print(f"  Channels:     {channels}")
            print(f"  Sample size:  {sample_size} bits")

    return mvhd, tracks, bitrate_total


def comparar_pipeline(tracks, bitrate_total, mvhd):
    """Compare with ideal Fire TV Stick pipeline."""
    print(f"\n{'═' * 80}")
    print("  COMPARAÇÃO COM PIPELINE IDEAL (Fire TV Stick)")
    print(f"{'═' * 80}")

    video_track = next((t for t in tracks if t.get('handler') == 'vide'), None)
    audio_track = next((t for t in tracks if t.get('handler') == 'soun'), None)

    if not video_track:
        print("  Nenhuma track de vídeo encontrada!")
        return

    checks = []

    def check(name, actual, expected, ok):
        status = "OK" if ok else "!!"
        checks.append((status, name, actual, expected))

    stsd = video_track.get('stsd', {})
    entries = stsd.get('entries', [])
    codec = entries[0]['type'] if entries else '?'
    w = int(entries[0].get('width', 0)) if entries else 0
    h = int(entries[0].get('height', 0)) if entries else 0
    tkhd = video_track.get('tkhd', {})
    rotation = tkhd.get('rotation', 0)
    avcc = video_track.get('avcC', {})
    profile = avcc.get('profile_name', '?')

    # Real resolution accounting for rotation
    real_w, real_h = w, h
    if rotation in (90, 270):
        real_w, real_h = real_h, real_w

    check("Codec", codec, "avc1 (H.264)", codec in ('avc1', 'avc3'))
    check("Profile", profile, "High", 'High' in str(profile))

    is_horizontal = real_w >= real_h
    if is_horizontal:
        check("Resolução", f"{real_w}x{real_h}", "1920x1080", real_w == 1920 and real_h == 1080)
    else:
        check("Resolução", f"{real_w}x{real_h}", "1080x1920", real_w == 1080 and real_h == 1920)

    check("Rotação", f"{rotation}°", "0°", rotation == 0)

    # FPS
    stts = video_track.get('stts', {})
    mdhd = video_track.get('mdhd', {})
    timescale = mdhd.get('timescale', 0)
    stts_entries = stts.get('entries', [])
    unique_deltas = set(e['sample_delta'] for e in stts_entries) if stts_entries else set()

    if timescale > 0 and stts_entries:
        total_samples = sum(e['sample_count'] for e in stts_entries)
        total_ticks = sum(e['sample_count'] * e['sample_delta'] for e in stts_entries)
        avg_fps = total_samples * timescale / total_ticks if total_ticks > 0 else 0
        is_cfr = len(unique_deltas) == 1
        check("Frame Rate", f"{avg_fps:.1f} fps", "30.0 fps", abs(avg_fps - 30.0) < 1.5)
        check("CFR/VFR", "CFR" if is_cfr else f"VFR ({len(unique_deltas)} deltas)", "CFR", is_cfr)

    check("Bitrate", f"{bitrate_total / 1000:.0f} kbps", "~5000 kbps",
          2000000 < bitrate_total < 8000000 if bitrate_total else False)

    # Color
    colr = video_track.get('colr', {})
    if colr and 'color_primaries' in colr:
        check("Color Space", colr['color_primaries'], "bt709",
              colr['color_primaries'] in ('bt709', '(1)'))

    # Audio
    if audio_track:
        a_stsd = audio_track.get('stsd', {})
        a_entries = a_stsd.get('entries', [])
        if a_entries:
            a_codec = a_entries[0].get('type', '?')
            a_rate = a_entries[0].get('sample_rate', 0)
            check("Audio Codec", a_codec, "mp4a (AAC)", a_codec == 'mp4a')
            check("Audio Rate", f"{a_rate} Hz", "44100 Hz", a_rate == 44100)

    print()
    all_ok = True
    for status, name, actual, expected in checks:
        icon = "  ✓" if status == "OK" else "  ✗"
        print(f"  {icon} {name:20s}  atual: {str(actual):25s}  ideal: {expected}")
        if status != "OK":
            all_ok = False

    if all_ok:
        print(f"\n  >>> VÍDEO JÁ ESTÁ NO FORMATO IDEAL! Nenhuma conversão necessária.")
    else:
        print(f"\n  >>> VÍDEO PRECISA DE CONVERSÃO para compatibilidade com Fire TV Stick.")

    print(f"\n{'═' * 80}")


def analisar_video_ffprobe(caminho):
    """Analisa usando ffprobe (se disponível)."""
    r = subprocess.run([
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', '-show_streams', caminho
    ], capture_output=True, text=True, timeout=30)

    if r.returncode != 0:
        return None

    data = json.loads(r.stdout)
    print(f"\n--- ffprobe JSON ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return data


if __name__ == '__main__':
    if len(sys.argv) > 1:
        caminho = sys.argv[1]
    else:
        # Arquivo padrão
        caminho = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "WhatsApp Video 2026-03-06 at 21.56.19.mp4"
        )

    if not os.path.exists(caminho):
        print(f"ERRO: Arquivo não encontrado: {caminho}")
        sys.exit(1)

    tamanho = os.path.getsize(caminho)
    print("=" * 80)
    print(f"  ANÁLISE DE VÍDEO: {os.path.basename(caminho)}")
    print("=" * 80)
    print(f"\nArquivo: {caminho}")
    print(f"Tamanho: {tamanho:,} bytes ({tamanho / 1024 / 1024:.2f} MB)")

    # Tenta ffprobe primeiro
    import shutil
    if shutil.which('ffprobe'):
        print("\n[Usando ffprobe]")
        analisar_video_ffprobe(caminho)
    else:
        print("\n[ffprobe não disponível — usando parser MP4 puro em Python]")

    # Sempre faz análise Python (funciona sem dependências)
    mvhd, tracks, bitrate = analisar_video_python(caminho)
    comparar_pipeline(tracks, bitrate, mvhd)
