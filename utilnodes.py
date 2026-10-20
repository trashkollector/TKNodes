import numpy as np
import cv2
import math
import json
import torch
import math


###############  Mainly used for V2V scenarios..  when source video and target video use differnt FPS ##############################
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

    # --- FUNCTION 1: DROP FRAMES (STRICTLY VIDEO AND TARGET FPS INPUTS) ---
    def drop_video_frames(self, video, video_fps):
        # 1. Total frame sequence count coming directly from the image tensor link
        total_source_frames = video.shape[0]
        
        # 2. Extract the physical layout length (seconds) directly from the tensor's native indices
        # This determines the runtime boundaries natively, removing the hardcoded 30.0
        calculated_source_fps = total_source_frames / (total_source_frames / video_fps)

        # 3. Calculate exactly how many frames to keep for your 16fps target container limit
        # Example: (300 total frames * 16fps target) / 30fps dynamic source = 160 frames
        required_frame_count = math.ceil((total_source_frames * video_fps) / calculated_source_fps)

        if total_source_frames > required_frame_count:
            # Drops frames mathematically across the tensor index layout to match the container target
            indices = torch.linspace(0, total_source_frames - 1, steps=required_frame_count, dtype=torch.long, device=video.device)
            return video[indices]
        return video
    
    def match_audio_to_video(self, audio, video, video_fps):
        if audio is None or video is None:
            return (audio, 0.0)


        newvideo  = self.drop_video_frames(  video, video_fps)

        waveform = audio.get("waveform")  # Shape: [channels, samples]
        sample_rate = audio.get("sample_rate")
        
        if waveform is None or sample_rate is None:
            return (audio, 0.0)

        # 1. Calculate exactly how long the video container is at 16 FPS
        total_video_frames = newvideo.shape[0]
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





"""
Drop-in replacements for TKTransitionDetector and detect_boundaries.

Replace ONLY these two items in your file. Everything else stays as is:
_tensor_batch_to_gray_small, _edge_density, _hist_distance, _causal_baseline
and your imports (json, numpy as np). Add `import math` at the top.

What changed
  Pass 1: real scene boundaries only (cuts + dissolve ends), ignoring scenes
          shorter than min_scene_seconds.
  Pass 2: each scene longer than chunk_secs is split EVENLY into n parts
          (n = ceil or round of length / chunk_secs, see split_mode).
          max_segment_seconds was REMOVED: chunk_secs is the only length
          control. With split_mode="ceil" no segment is longer than chunk_secs.
  Outputs simplified to: segment_images (middle frame of every segment, IMAGE
          list for the Gemma describe node), boundary_frames (segment start
          frames, INT list, same as before), report, debug_csv.
          NOTE: output order changed, so re-wire boundary_frames (it was the
          4th output, now the 2nd). boundaries_json and boundary_count are gone.
  New inputs were added AFTER debug_mode so existing widget order is unchanged.
  Boundary types are unchanged: "cut", "dissolve_end", "forced", "end".
  A "forced" boundary now means "even split inside a long scene".
"""


class TKTransitionDetector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "chunk_secs": ("FLOAT", {"default": 5.0, "min": 0.5, "max": 120.0, "step": 0.1}),
                "min_scene_seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 30.0, "step": 0.1}),
                "fps": ("FLOAT", {"default": 25.0, "min": 1.0, "max": 240.0, "step": 0.01}),
                "cut_z_thresh": ("FLOAT", {"default": 3.0, "min": 1.0, "max": 10.0, "step": 0.1}),
                "dissolve_dip_ratio": ("FLOAT", {"default": 0.70, "min": 0.1, "max": 0.95, "step": 0.01}),
                "dissolve_min_len": ("INT", {"default": 5, "min": 2, "max": 60}),
                "analysis_width": ("INT", {"default": 160, "min": 64, "max": 640}),
                "debug_mode": ("BOOLEAN", {"default": False}),
                # --- new (kept last so old workflows keep their widget values) ---
                "split_mode": (["ceil", "round"], {"default": "ceil"}),
                
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE",  "INT", "STRING", "STRING", )
    RETURN_NAMES = ("segment_images", "listImages", "boundary_frames", "report", "debug_csv", )
    OUTPUT_IS_LIST = (False, True, True, False, False, True)
    FUNCTION = "run"
    CATEGORY = "TKNodes/video"

    def run(
        self,
        images,
        fps,
        cut_z_thresh,
        dissolve_dip_ratio,
        dissolve_min_len,
        analysis_width,
        debug_mode,
        chunk_secs=5.0,
        split_mode="ceil",
        min_scene_seconds=1.0,
    ):
        gray_frames = _tensor_batch_to_gray_small(images, analysis_width=analysis_width)
        baseline_window = max(11, dissolve_min_len * 4 + 1)

        boundaries, debug_rows = detect_boundaries_2(
            gray_frames=gray_frames,
            fps=fps,
            cut_z_thresh=cut_z_thresh,
            dissolve_dip_ratio=dissolve_dip_ratio,
            dissolve_min_len=dissolve_min_len,
            baseline_window=baseline_window,
            return_debug=debug_mode,
            chunk_secs=chunk_secs,
            split_mode=split_mode,
            min_scene_seconds=min_scene_seconds,
        )

        # segments: start frames are frame 0 + every non-"end" boundary
        n = int(images.shape[0])
        starts = [0] + [b["frame"] for b in boundaries if b["type"] != "end"]
        ends = starts[1:] + [n]
        mids = [min(n - 1, (s + e) // 2) for s, e in zip(starts, ends)]
        list_segment_images = [images[m:m + 1] for m in mids]
        segment_batch = torch.cat([images[m:m + 1] for m in mids], dim=0)


        lines = [f"{len(boundaries)} boundaries, {len(starts)} segments "
                 f"(fps={fps}, chunk_secs={chunk_secs}, split_mode={split_mode}):"]
        for b in boundaries:
            lines.append(f"  frame {b['frame']:>6}  t={b['time']:.2f}s  [{b['type']}]")
        lines.append("segments (start-end, secs, describe-frame):")
        for s, e, m in zip(starts, ends, mids):
            lines.append(f"  {s:>6}-{e:<6} {(e - s) / fps:5.2f}s  frame {m}")
        report = "\n".join(lines)

        boundary_frames = [b["frame"] for b in boundaries if b["type"] != "end"]
        if not boundary_frames:
            boundary_frames = [b["frame"] for b in boundaries]

        if debug_mode and debug_rows:
            cols = ["frame", "time", "hist_dist", "z_score", "edge_density",
                    "edge_baseline", "edge_ratio", "flagged_cut", "flagged_dip"]
            csv_lines = [",".join(cols)]
            for r in debug_rows:
                csv_lines.append(",".join(str(r[c]) for c in cols))
            debug_csv = "\n".join(csv_lines)
        else:
            debug_csv = "debug_mode is off - enable it to get per-frame z_score/edge_ratio values"

        non_end = [b for b in boundaries if b["type"] != "end"]
        used = non_end if non_end else boundaries
        boundary_frames = [b["frame"] for b in used]
        boundary_is_cut = [b["type"] != "forced" for b in used]

        return (segment_batch, list_segment_images, boundary_frames, report, debug_csv, boundary_is_cut)



def detect_boundaries_2(
    gray_frames,
    fps: float,
    cut_z_thresh: float,
    dissolve_dip_ratio: float,
    dissolve_min_len: int,
    baseline_window: int,
    return_debug: bool = False,
    chunk_secs: float = 5.0,
    split_mode: str = "ceil",
    min_scene_seconds: float = 1.0,
):
    n = len(gray_frames)
    if n < 2:
        result = [{"frame": n - 1, "time": (n - 1) / fps, "type": "end"}]
        return result, []

    # --- per-frame signals (unchanged) ---
    hist_dist = np.zeros(n)
    edge_dens = np.zeros(n)
    edge_dens[0] = _edge_density(gray_frames[0])
    for i in range(1, n):
        hist_dist[i] = _hist_distance(gray_frames[i - 1], gray_frames[i])
        edge_dens[i] = _edge_density(gray_frames[i])

    # --- hard cut detection (unchanged) ---
    mean = np.mean(hist_dist[1:])
    std = np.std(hist_dist[1:]) + 1e-6
    z = (hist_dist - mean) / std

    cut_frames = set()
    for i in range(1, n):
        if z[i] <= cut_z_thresh:
            continue
        neighbor_lo = max(1, i - 2)
        neighbor_hi = min(n, i + 3)
        neighborhood = np.delete(z[neighbor_lo:neighbor_hi],
                                 np.where(np.arange(neighbor_lo, neighbor_hi) == i))
        if neighborhood.size == 0 or np.max(neighborhood) < (cut_z_thresh * 0.5):
            cut_frames.add(i)

    # --- dissolve detection (unchanged) ---
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
            end = i
            if (end - start) >= dissolve_min_len:
                dissolve_end_frames.add(min(end, n - 1))
        else:
            i += 1

    # --- merge cuts + dissolve ends (unchanged) ---
    boundaries = []
    for f in sorted(cut_frames):
        boundaries.append({"frame": f, "time": f / fps, "type": "cut"})
    for f in sorted(dissolve_end_frames):
        boundaries.append({"frame": f, "time": f / fps, "type": "dissolve_end"})
    boundaries.sort(key=lambda b: b["frame"])

    deduped = []
    for b in boundaries:
        if deduped and (b["frame"] - deduped[-1]["frame"]) <= 3:
            continue
        deduped.append(b)
    boundaries = deduped

    # ===== PASS 1: keep real scene boundaries, drop scenes shorter than min =====
    min_f = max(1, int(round(min_scene_seconds * fps)))
    kept = []
    last = 0
    for b in boundaries:
        if b["frame"] - last < min_f:
            continue
        kept.append(b)
        last = b["frame"]
    if kept and (n - kept[-1]["frame"]) < min_f:
        kept.pop()                       # merge a tiny tail into the previous scene

    # ===== PASS 2: split long scenes evenly toward chunk_secs =====
    target_f = max(1.0, chunk_secs * fps)
    starts = [0] + [b["frame"] for b in kept]
    ends = starts[1:] + [n]
    kept_by_frame = {b["frame"]: b for b in kept}

    final = []
    for s, e in zip(starts, ends):
        if s in kept_by_frame:
            final.append(kept_by_frame[s])
        length = e - s
        ratio = length / target_f
        if split_mode == "ceil":
            parts = math.ceil(ratio - 1e-6)
        else:
            parts = int(ratio + 0.5)
        parts = max(1, parts)
        for k in range(1, parts):
            f = s + int(round(k * length / parts))
            final.append({"frame": f, "time": f / fps, "type": "forced"})

    last_frame_idx = n - 1
    final.append({"frame": last_frame_idx, "time": last_frame_idx / fps, "type": "end"})

    # --- debug rows (unchanged) ---
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
TKChunkFrames - grab one frame every `chunk_secs` seconds from a video.

Drop this file into ComfyUI/custom_nodes/ (or add the classes to TKNodes)
and restart ComfyUI.

Two nodes:
  * TKChunkFrames        - takes a VIDEO input (fps is read from the video)
  * TKChunkFramesImages  - takes an IMAGE batch + fps (for pipelines that
                           already pass frames around as IMAGE tensors)

Output is an IMAGE *list* (one [1,H,W,C] image per chunk), so downstream
nodes run once per image. A 15s video with chunk_secs=5 gives 3 images
(frames at 0s, 5s, 10s).
"""

import math


def _pick_frames(images, fps, chunk_secs):
    total = int(images.shape[0])
    if total == 0:
        raise ValueError("TKChunkFrames: video has no frames.")
    if fps <= 0:
        raise ValueError("TKChunkFrames: fps must be > 0.")

    step = max(1, int(round(chunk_secs * fps)))  # frames per chunk
    indices = list(range(0, total, step))        # first frame of every chunk
    frames = [images[i:i + 1] for i in indices]  # keep batch dim -> [1,H,W,C]
    return frames, indices


"""
TKTransitionDetectorChunk - pull one segment (video frames + matching audio) out of a
full video using the boundaries produced by detect_boundaries().

Drop this file into ComfyUI/custom_nodes/ and restart ComfyUI.

Boundary semantics (matches detect_boundaries):
  - "cut" / "dissolve_end" / "forced": the boundary frame is the FIRST frame
    of the next segment.
  - "end": the last frame index of the video; it closes the final segment
    (that last frame is included).
Segments are therefore:
  seg 0 = [0, b0)   seg 1 = [b0, b1)   ...   last = [b_last, n)
"""

import json

import torch


class _AnyType(str):
    """Wildcard socket type so this input connects to whatever the
    boundary-detection node outputs (list, dict, string, tuple...)."""

    def __ne__(self, other):
        return False


ANY = _AnyType("*")


def _flatten(x):
    """Turn whatever arrives (int, list of ints, list of dicts, tuple from
    detect_boundaries, JSON string, nested lists) into a flat list of items."""
    if isinstance(x, tuple) and len(x) == 2 and isinstance(x[1], list):
        x = x[0]  # (boundaries, debug_rows)
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except ValueError:
            return []
    if isinstance(x, dict):
        if "frame" in x:
            return [x]
        x = x.get("boundaries", x.get("segments", []))
    if isinstance(x, (list, tuple)):
        out = []
        for item in x:
            out.extend(_flatten(item))
        return out
    return [] if x is None else [x]


def _one(x):
    """With INPUT_IS_LIST every input arrives wrapped in a list; take the first."""
    if isinstance(x, (list, tuple)):
        return x[0] if len(x) else None
    return x


def _extract_starts(boundaries, total_frames):
    """Normalise any supported boundaries format to a sorted list of
    segment start frames (always beginning with 0)."""
    starts = [0]
    for b in _flatten(boundaries):
        if isinstance(b, dict):
            if b.get("type") == "end":
                continue  # the 'end' marker closes the last segment, not a new start
            frame = b.get("frame")
        else:
            frame = b
            # plain frame numbers: a value on the very last frame is the
            # 'end' marker, not the start of a new one-frame segment
            if frame is not None and int(frame) >= total_frames - 1:
                continue
        if frame is None:
            continue
        frame = int(frame)
        if 0 < frame < total_frames:
            starts.append(frame)

    return sorted(set(starts))


class TKTransitionDetectorChunk:
    INPUT_IS_LIST = True  # receive the whole boundary list in ONE call

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "fps": ("FLOAT", {"default": 24.0, "min": 0.01, "max": 1000.0, "step": 0.01}),
                "full_video": ("IMAGE",),
                "boundary_frames": (ANY,),
            },
            "optional": {
                "full_audio": ("AUDIO",),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO")
    RETURN_NAMES = ("chunkOfVideo", "chunkOfAudio")
    FUNCTION = "run"
    CATEGORY = "TKNodes"

    def run(self, index, fps, full_video, boundary_frames, full_audio=None):
        index = int(_one(index) or 0)
        fps = float(_one(fps) or 24.0)
        full_video = _one(full_video)
        if full_video is None:
            raise ValueError("TKTransitionDetectorChunk: full_video is required")
        full_audio = _one(full_audio)
        total = int(full_video.shape[0])
        starts = _extract_starts(boundary_frames, total)
        seg_count = len(starts)

        if index >= seg_count:
            print(f"[TKTransitionDetectorChunk] index {index} out of range (0..{seg_count - 1}), clamping to last segment")
        idx = max(0, min(int(index), seg_count - 1))

        start = starts[idx]
        end = starts[idx + 1] if idx + 1 < seg_count else total  # last segment runs to the final frame

        chunk_video = full_video[start:end]
        print(f"[TKTransitionDetectorChunk] segment {idx}/{seg_count - 1}: frames {start}..{end - 1} ({end - start} frames)")

        # ---- audio ----
        if full_audio is not None:
            waveform = full_audio["waveform"]  # [B, C, samples]
            sr = int(full_audio["sample_rate"])
            total_samples = waveform.shape[-1]

            s0 = int(round(start / fps * sr))
            # last segment keeps the audio tail so nothing is dropped
            s1 = total_samples if (idx + 1 >= seg_count) else int(round(end / fps * sr))
            s0 = max(0, min(s0, total_samples))
            s1 = max(s0, min(s1, total_samples))

            chunk_audio = {"waveform": waveform[..., s0:s1].contiguous(), "sample_rate": sr}
        else:
            # no audio connected: return silence matching the chunk duration
            sr = 44100
            n_samples = int(round((end - start) / fps * sr))
            chunk_audio = {"waveform": torch.zeros((1, 2, n_samples)), "sample_rate": sr}

        return (chunk_video, chunk_audio)


class TKTransitionScenesCount:
    """Returns how many segments boundary_frames describes.
    Valid index values for TKTransitionDetectorChunk are 0 .. segment_count-1."""

    INPUT_IS_LIST = True  # receive the whole boundary list in ONE call

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "boundary_frames": (ANY,),
            },
            "optional": {
                # optional: boundaries at/after this frame are ignored (0 = no limit)
                "total_frames": ("INT", {"default": 0, "min": 0, "max": 100000000}),
            },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("segment_count", "last_index")
    FUNCTION = "run"
    CATEGORY = "TKNodes"

    def run(self, boundary_frames, total_frames=None):
        tf = _one(total_frames)
        limit = int(tf) if tf and tf > 0 else 10**12
        starts = _extract_starts(boundary_frames, limit)
        count = len(starts)
        return (count, count - 1)


