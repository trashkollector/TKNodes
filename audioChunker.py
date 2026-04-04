import math

from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np
import torch
import torch.nn.functional as F
import torchaudio

def _get_private_splits_from_audio(audio_data, chunk_size, variation):
    # 1. Extract data from the ComfyUI Audio dictionary
    waveform = audio_data['waveform']      # Shape: [Batch, Channels, Samples]
    sample_rate = audio_data['sample_rate']
    
    # 2. Convert PyTorch tensor to raw bytes for pydub
    # We flatten all channels into a single mono stream for silence detection
    if waveform.dim() > 2:
        waveform = waveform.mean(dim=1) # Convert to mono
    
    # Scale float32 (-1.0 to 1.0) to int16 for pydub compatibility
    audio_np = (waveform.cpu().numpy() * 32767).astype(np.int16)
    raw_data = audio_np.tobytes()
    
    # 3. Create pydub AudioSegment from raw bytes
    audio = AudioSegment(
        data=raw_data,
        sample_width=2, # 16-bit (2 bytes)
        frame_rate=sample_rate,
        channels=1
    )
    
    # 4. Same splitting logic as before
    total_ms = len(audio)
    target, var = chunk_size * 1000, variation * 1000
    splits, curr = [0], 0
    
    while curr + (target - var) < total_ms:
        win_start = curr + (target - var)
        win_end = min(curr + (target + var), total_ms)
        window = audio[win_start:win_end]
        
        silence = detect_silence(window, min_silence_len=300, silence_thresh=-40)
        if silence:
            s_start, s_end = silence[0]
            split_at = win_start + s_start + (s_end - s_start) // 2
        else:
            split_at = curr + target
            
        splits.append(split_at)
        curr = split_at


    # add this fix to avoid 0 length    
    if splits[-1] < total_ms:
        splits.append(total_ms)
    return splits
    


# --- THE COMFYUI NODE ---
class TKSmartAudioChunker:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",), # Connect the gray wire here
                "index": ("INT", {"default": 0}),
                "chunk_secs": ("INT", {"default": 10}),
                "variation": ("INT", {"default": 2}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("num_chunks", "chunk_size", "start_time", "total_duration")
    FUNCTION = "calculate"
    CATEGORY = "HandyNodes-KT"

    def calculate(self, audio, index, chunk_secs, variation):
        # Run the private logic using the audio wire data
        splits = _get_private_splits_from_audio(audio, chunk_secs, variation)

        num_chunks = len(splits) - 1
        idx = max(0, min(index, num_chunks - 1))
        
        start_ms = splits[idx]
        end_ms = splits[idx + 1]
        
        chunkSizeMs = float((end_ms - start_ms) )     # chunk_size
        origChunkSize = chunkSizeMs


       
        startChunkMs = float(start_ms)       # start_time
             
        durMs = float(splits[-1])         # total_duration


        return (
            num_chunks, 
            chunkSizeMs/1000.0,
            startChunkMs/1000.0,
            durMs  / 1000.0,
        )
 


class TKTrimImageOverlap:
    """
    Trims overlap frames from video segments based on position in sequence.

    - First segment  (idx == 0):              trim end only
    - Middle segments (0 < idx < total - 1):  trim both start and end
    - Last segment   (idx == total - 1):      trim start only

    Inputs:
        image           : IMAGE batch (N, H, W, C)
        idx             : int  – current loop index (0-based)
        total_segments  : int  – total number of segments
        start_frames    : int  – frames to remove from start (overlap on front)
        end_frames      : int  – frames to remove from end   (overlap on back)

    Output:
        IMAGE batch with overlap frames removed
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":           ("IMAGE",),
                "idx":             ("INT", {"default": 0, "min": 0, "max": 9999}),
                "total_segments":  ("INT", {"default": 1, "min": 1, "max": 9999}),
                "start_frames":    ("INT", {"default": 12, "min": 0, "max": 9999}),
                "end_frames":      ("INT", {"default": 13, "min": 0, "max": 9999}),
            }
        }

    RETURN_TYPES  = ("IMAGE",)
    RETURN_NAMES  = ("image",)
    FUNCTION      = "trim"
    CATEGORY      = "TKNodes/video"

    def trim(self, image: torch.Tensor, idx: int, total_segments: int,
             start_frames: int, end_frames: int) -> tuple:

        total_frames = image.shape[0]

        is_first  = (idx == 0)
        is_last   = (idx == total_segments - 1)

        trim_start = not is_first   # trim start on middle + last
        trim_end   = not is_last    # trim end   on first  + middle

        start = start_frames if trim_start else 0
        end   = total_frames - end_frames if trim_end else total_frames

        # Safety clamp so we never produce an empty batch
        start = max(0, min(start, total_frames - 1))
        end   = max(start + 1, min(end, total_frames))

        trimmed = image[start:end]

        print(f"[TKTrimImageOverlap] idx={idx}/{total_segments-1} | "
              f"frames={total_frames} → {trimmed.shape[0]} | "
              f"trim_start={trim_start}({start_frames}f) "
              f"trim_end={trim_end}({end_frames}f)")

        return (trimmed,)


class TKCalcLTXFrames:
    """
    Converts a bare chunk duration (NO overlap) to a valid LTX frame count,
    and computes the exact overlap needed so trimming is perfectly accurate.

    LTX requires frame counts where (n - 1) % 8 == 0
    Valid values: 1, 9, 17, 25, ... 225, 233, 241, ...

    Workflow:
        1. Pass the RAW chunk duration (no overlap added yet).
        2. This node rounds UP to the next valid LTX frame count.
        3. The extra frames are split evenly into start/end overlap.
        4. Pass overlap_ms to Smart Audio Chunker instead of a hardcoded value.
        5. Pass start_trim_frames / end_trim_frames to TKTrimImageOverlap.

    Inputs:
        chunk_secs      : FLOAT   – chunk duration in seconds (NO overlap)
        fps             : INT     – frames per second (default 25)

    Outputs:
        frame_count     : INT   – LTX-compatible frame count (with overlap)
        overlap_ms      : FLOAT – milliseconds to add to each side of chunk
        start_trim_frames : INT – frames to trim from start (for TKTrimImageOverlap)
        end_trim_frames   : INT – frames to trim from end   (for TKTrimImageOverlap)
        actual_secs     : FLOAT – total duration represented by frame_count
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "chunk_secs": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 9999.0, "step": 0.001}),
                "fps":        ("INT",   {"default": 25,  "min": 1,    "max": 240}),
            }
        }

    RETURN_TYPES  = ("INT",         "FLOAT",      "INT",               "INT",             "FLOAT")
    RETURN_NAMES  = ("frame_count", "overlap_ms", "start_trim_frames", "end_trim_frames", "actual_secs")
    FUNCTION      = "calc"
    CATEGORY      = "TKNodes/video"

    def calc(self, chunk_secs: float, fps: int) -> tuple:
        raw = chunk_secs * fps

        # Round UP to next valid LTX frame count: n = 8k + 1
        k = math.ceil((raw - 1) / 8)
        k = max(0, k)
        frame_count = 8 * k + 1
        actual_secs = frame_count / fps

        # Extra frames added by rounding — split evenly between start and end
        extra_frames = frame_count - math.ceil(raw)
        end_trim   = extra_frames // 2
        start_trim = extra_frames - end_trim   # start gets the remainder if odd

        overlap_ms = (extra_frames / fps) * 1000 / 2  # ms per side

        print(f"[TKCalcLTXFrames] {chunk_secs:.3f}s × {fps}fps = {raw:.2f} raw → "
              f"{frame_count} frames ({actual_secs:.3f}s) | "
              f"extra={extra_frames}f | overlap={overlap_ms:.1f}ms/side | "
              f"trim start={start_trim}f end={end_trim}f")

        return (frame_count, overlap_ms, start_trim, end_trim, actual_secs)



