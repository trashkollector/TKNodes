
import numpy as np
import cv2
import math
import json
import torch
import math


################  Mainly used for V2V scenarios..  when source video and target video use differnt FPS ##############################
class TKAudioToFPSMatcher:
    DESCRIPTION = "Aligns and pads an original audio track to perfectly match the duration of a target FPS video timeline, preventing VHS truncation.  Mainly needed for V2V"
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO", {"tooltip": "Original master audio"}),
                "video": ("IMAGE", {"tooltip": "Your newly generated video tensor"}),
                "video_fps": ("FLOAT", {"default": 16.0, "min": 1.0, "max": 60.0, "step": 0.01, "tooltip": "The FPS of your generated video (e.g., 16.0)"}),
            },
        }

    RETURN_TYPES = ("AUDIO", "FLOAT",)
    RETURN_NAMES = ("matched_audio", "exact_duration_seconds",)
    FUNCTION = "match_audio_to_video"
    CATEGORY = "TKNodes"

    def match_audio_to_video(self, audio, video, video_fps):
        if audio is None or video is None:
            return (audio, 0.0)

        waveform = audio.get("waveform")  # Shape: [channels, samples]
        sample_rate = audio.get("sample_rate")
        
        if waveform is None or sample_rate is None:
            return (audio, 0.0)

        # 1. Calculate exactly how long the video container is at 16 FPS
        total_video_frames = video.shape[0]
        video_duration_seconds = total_video_frames / video_fps

        # 2. Calculate the exact number of audio samples needed for this duration
        required_audio_samples = math.ceil(video_duration_seconds * sample_rate)
        current_audio_samples = waveform.shape[-1]

        # 3. Match the audio length to the video length perfectly
        if current_audio_samples > required_audio_samples:
            # Audio is too long: Trim it cleanly so VHS Combine doesn't force-chop it
            clean_waveform = waveform[..., :required_audio_samples]
        elif current_audio_samples < required_audio_samples:
            # Audio is too short: Pad with absolute silence to fill the microsecond gap
            padding_size = required_audio_samples - current_audio_samples
            padding = torch.zeros((*waveform.shape[:-1], padding_size), dtype=waveform.dtype, device=waveform.device)
            clean_waveform = torch.cat([waveform, padding], dim=-1)
        else:
            clean_waveform = waveform

        matched_audio = {"waveform": clean_waveform, "sample_rate": sample_rate}
        return (matched_audio, video_duration_seconds)



################################ Snap frames for WAN or LTX #############################################
class TKSnapFrames:
    DESCRIPTION = "Snap Frames - Rounds num_frames UP to the nearest valid (multiple*n + 1) frame count for the target model"

    MODEL_MULTIPLES = {
        "WAN": 4,
        "LTX": 8,
    }

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": (list(s.MODEL_MULTIPLES.keys()), {"default": "WAN", "tooltip": "Target model - determines the valid frame-count multiple (n+1)"}),
                "num_frames": ("INT", {"default": 17, "min": 1, "max": 9999, "tooltip": "Requested frame count before snapping"}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("snapped_frames",)
    FUNCTION = "snap"
    CATEGORY = "TKNodes"

    def snap(self, model, num_frames):
        multiple = self.MODEL_MULTIPLES[model]
        snapped_frames = math.ceil((num_frames - 1) / multiple) * multiple + 1
        return (snapped_frames,)


#################### SCENE DETECTION ###########################################################

### Used for detecting Scene changes in Video  (similiar to what you find in Davinci)
def _tensor_batch_to_gray_small(images, analysis_width: int = 160):
    """
    images: torch tensor [N, H, W, C], float 0-1 (standard ComfyUI IMAGE type)
    Returns: list of small grayscale uint8 numpy frames, resized to analysis_width.
    Downscaling is purely for speed - detection doesn't need full resolution.
    torch is only needed here (inside the ComfyUI node path), not for
    detect_boundaries() itself, which is pure numpy/opencv and testable standalone.
    """
    import torch  # local import: only required when running inside ComfyUI
    n, h, w, c = images.shape
    scale = analysis_width / float(w)
    new_w = analysis_width
    new_h = max(1, int(round(h * scale)))

    frames_np = (images.clamp(0, 1) * 255.0).to(torch.uint8).cpu().numpy()  # [N,H,W,C]

    gray_frames = []
    for i in range(n):
        frame = frames_np[i]
        if c == 4:
            frame = frame[:, :, :3]
        if c == 1:
            gray = cv2.resize(frame[:, :, 0], (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            small = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        gray_frames.append(gray)
    return gray_frames


def _hist_distance(a: np.ndarray, b: np.ndarray) -> float:
    """1 - histogram correlation. 0 = identical, ~1-2 = very different."""
    hist_a = cv2.calcHist([a], [0], None, [64], [0, 256])
    hist_b = cv2.calcHist([b], [0], None, [64], [0, 256])
    cv2.normalize(hist_a, hist_a)
    cv2.normalize(hist_b, hist_b)
    corr = cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)
    return 1.0 - corr


def _edge_density(frame: np.ndarray) -> float:
    """Fraction of pixels that are Canny edges. Dips during dissolves."""
    edges = cv2.Canny(frame, 60, 150)
    return float(np.count_nonzero(edges)) / edges.size


def _causal_baseline(arr: np.ndarray, window: int, lag: int) -> np.ndarray:
    """
    Backward-looking median: baseline[i] = median(arr[i-lag-window : i-lag]).
    Deliberately does NOT look at recent frames (within `lag`), so that if a
    dip/dissolve is currently happening at frame i, the baseline still
    reflects the stable shot *before* the dip started, rather than being
    dragged down by the dip itself (a centered window would straddle the
    dip and dilute the drop we're trying to detect).
    """
    n = len(arr)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        hi = max(1, i - lag)
        lo = max(0, hi - window)
        if lo >= hi:
            out[i] = arr[i]
        else:
            out[i] = np.median(arr[lo:hi])
    return out


def detect_boundaries(
    gray_frames,
    fps: float,
    max_segment_seconds: float,
    cut_z_thresh: float,
    dissolve_dip_ratio: float,
    dissolve_min_len: int,
    baseline_window: int,
    return_debug: bool = False,
):
    """
    Always returns a (boundaries, debug_rows) tuple - debug_rows is simply
    an empty list when return_debug is False. Keeping the return shape
    constant (rather than sometimes a bare list, sometimes a tuple) avoids
    static-type ambiguity in callers.
    """
    n = len(gray_frames)
    if n < 2:
        result = [{"frame": n - 1, "time": (n - 1) / fps, "type": "end"}]
        return result, []

    # --- per-frame signals ---
    hist_dist = np.zeros(n)
    edge_dens = np.zeros(n)
    edge_dens[0] = _edge_density(gray_frames[0])
    for i in range(1, n):
        hist_dist[i] = _hist_distance(gray_frames[i - 1], gray_frames[i])
        edge_dens[i] = _edge_density(gray_frames[i])

    # --- hard cut detection: rolling z-score over hist_dist ---
    mean = np.mean(hist_dist[1:])
    std = np.std(hist_dist[1:]) + 1e-6
    z = (hist_dist - mean) / std

    # A hard cut is an ISOLATED spike: frame i is very different from i-1,
    # but frame i's neighbors are NOT also spiking. A dissolve instead shows
    # a sustained run of moderately-elevated distance across many frames -
    # that run gets handled by the edge-density dip logic below, not here.
    cut_frames = set()
    for i in range(1, n):
        if z[i] <= cut_z_thresh:
            continue
        neighbor_lo = max(1, i - 2)
        neighbor_hi = min(n, i + 3)
        neighborhood = np.delete(z[neighbor_lo:neighbor_hi], np.where(np.arange(neighbor_lo, neighbor_hi) == i))
        if neighborhood.size == 0 or np.max(neighborhood) < (cut_z_thresh * 0.5):
            cut_frames.add(i)

    # --- dissolve detection: edge density dip vs pre-dip baseline ---
    # lag must be >= the longest dip we expect, so the baseline window never
    # includes frames from inside the dip itself.
    baseline_lag = max(dissolve_min_len * 3, 15)
    baseline = _causal_baseline(edge_dens, baseline_window, baseline_lag)
    dip_mask = edge_dens < (baseline * dissolve_dip_ratio)

    dissolve_end_frames = set()
    i = 1
    while i < n:
        if dip_mask[i] and i not in cut_frames:
            start = i
            while i < n and dip_mask[i]:
                i += 1
            end = i  # first frame after the dip = dissolve considered finished
            if (end - start) >= dissolve_min_len:
                dissolve_end_frames.add(min(end, n - 1))
        else:
            i += 1

    # --- merge cuts + dissolve ends into one boundary list ---
    boundaries = []
    for f in sorted(cut_frames):
        boundaries.append({"frame": f, "time": f / fps, "type": "cut"})
    for f in sorted(dissolve_end_frames):
        boundaries.append({"frame": f, "time": f / fps, "type": "dissolve_end"})
    boundaries.sort(key=lambda b: b["frame"])

    # de-dupe boundaries that land within a few frames of each other
    deduped = []
    for b in boundaries:
        if deduped and (b["frame"] - deduped[-1]["frame"]) <= 3:
            continue
        deduped.append(b)
    boundaries = deduped

    # --- enforce max_segment_seconds: insert forced boundaries into gaps ---
    max_frames = int(round(max_segment_seconds * fps))
    final = []
    last = 0
    for b in boundaries:
        while (b["frame"] - last) > max_frames:
            forced_frame = last + max_frames
            final.append({"frame": forced_frame, "time": forced_frame / fps, "type": "forced"})
            last = forced_frame
        final.append(b)
        last = b["frame"]

    # tail: from last boundary to end of video
    last_frame_idx = n - 1
    while (last_frame_idx - last) > max_frames:
        forced_frame = last + max_frames
        final.append({"frame": forced_frame, "time": forced_frame / fps, "type": "forced"})
        last = forced_frame

    if not final or final[-1]["frame"] != last_frame_idx:
        final.append({"frame": last_frame_idx, "time": last_frame_idx / fps, "type": "end"})

    debug_rows = []
    if return_debug:
        edge_ratio = edge_dens / np.maximum(baseline, 1e-9)
        for i in range(n):
            debug_rows.append({
                "frame": i,
                "time": round(i / fps, 3),
                "hist_dist": round(float(hist_dist[i]), 5),
                "z_score": round(float(z[i]), 3),
                "edge_density": round(float(edge_dens[i]), 5),
                "edge_baseline": round(float(baseline[i]), 5),
                "edge_ratio": round(float(edge_ratio[i]), 3),
                "flagged_cut": i in cut_frames,
                "flagged_dip": bool(dip_mask[i]),
            })

    return final, debug_rows

"""
TKTransitionDetector - ComfyUI custom node

Scans a video (IMAGE batch) and returns a list of "segment boundary" frames:
  - hard cut frames
  - the frame where a dissolve/cross-fade FINISHES (not the whole range)
  - a synthetic "forced" boundary if more than `max_segment_seconds` passes
    with no real transition (since downstream rendering is capped at 10s)

This is a prep tool, not a broadcast-grade scene detector. It optimizes for
"mostly correct, fast, no manual threshold babysitting" rather than
frame-perfect precision.

Drop this .py file into ComfyUI's custom_nodes folder (or your TKNodes package).
"""

class TKTransitionDetector:
    """
    Inputs an IMAGE batch (e.g. from VHS Load Video), outputs segment
    boundary frames: hard cuts, dissolve-finish frames, and forced
    boundaries wherever a segment would otherwise exceed max_segment_seconds.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "fps": ("FLOAT", {"default": 25.0, "min": 1.0, "max": 240.0, "step": 0.01}),
                "max_segment_seconds": ("FLOAT", {"default": 10.0, "min": 1.0, "max": 120.0, "step": 0.5}),
                "cut_z_thresh": ("FLOAT", {"default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1}),
                "dissolve_dip_ratio": ("FLOAT", {"default": 0.70, "min": 0.1, "max": 0.95, "step": 0.01}),
                "dissolve_min_len": ("INT", {"default": 5, "min": 2, "max": 60}),
                "analysis_width": ("INT", {"default": 160, "min": 64, "max": 640}),
                "debug_mode": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("STRING", "INT", "STRING", "INT", "STRING")
    RETURN_NAMES = ("boundaries_json", "boundary_count", "report", "boundary_frames", "debug_csv")
    OUTPUT_IS_LIST = (False, False, False, True, False)
    FUNCTION = "run"
    CATEGORY = "TKNodes/video"

    def run(
        self,
        images,
        fps,
        max_segment_seconds,
        cut_z_thresh,
        dissolve_dip_ratio,
        dissolve_min_len,
        analysis_width,
        debug_mode,
    ):
        gray_frames = _tensor_batch_to_gray_small(images, analysis_width=analysis_width)
        baseline_window = max(11, dissolve_min_len * 4 + 1)  # odd window, scales with dip length

        boundaries, debug_rows = detect_boundaries(
            gray_frames=gray_frames,
            fps=fps,
            max_segment_seconds=max_segment_seconds,
            cut_z_thresh=cut_z_thresh,
            dissolve_dip_ratio=dissolve_dip_ratio,
            dissolve_min_len=dissolve_min_len,
            baseline_window=baseline_window,
            return_debug=debug_mode,
        )

        boundaries_json = json.dumps(boundaries, indent=2)

        lines = [f"{len(boundaries)} boundaries detected (fps={fps}):"]
        for b in boundaries:
            lines.append(f"  frame {b['frame']:>6}  t={b['time']:.2f}s  [{b['type']}]")
        report = "\n".join(lines)

        boundary_frames = [b["frame"] for b in boundaries if b["type"] != "end"]
        if not boundary_frames:
            boundary_frames = [b["frame"] for b in boundaries]  # fallback: nothing but 'end'

        if debug_mode and debug_rows:
            cols = ["frame", "time", "hist_dist", "z_score", "edge_density", "edge_baseline", "edge_ratio", "flagged_cut", "flagged_dip"]
            csv_lines = [",".join(cols)]
            for r in debug_rows:
                csv_lines.append(",".join(str(r[c]) for c in cols))
            debug_csv = "\n".join(csv_lines)
        else:
            debug_csv = "debug_mode is off - enable it to get per-frame z_score/edge_ratio values"

        return (boundaries_json, len(boundaries), report, boundary_frames, debug_csv)



