import math

from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np
import torch
import torch.nn.functional as F


 
class TKPromptLooper:
    DESCRIPTION = "Prompt Looper - Loops between 1 to 4 prompts/images.  It keeps alternating prompt and image for the workflow"

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "prompt1": ("STRING", {"tooltip": "prompt 1", "multiline": True}),
                "image1": ("IMAGE", ),

            },
            "optional": {
                "prompt2": ("STRING", {"tooltip": "prompt 2", "multiline": True}),
                "image2": ("IMAGE", ),
                "prompt3": ("STRING", {"tooltip": "prompt 3", "multiline": True}),
                "image3": ("IMAGE", ),
                "prompt4": ("STRING", {"tooltip": "prompt 4", "multiline": True}),
                "image4": ("IMAGE", ),
            }
        }

    RETURN_TYPES = ("INT", "STRING", "IMAGE")
    RETURN_NAMES = ("index", "prompt", "image")
    FUNCTION = "getResultsAtIndex"
    CATEGORY = "TKNodes"

    def getResultsAtIndex(self, index, prompt1, image1, prompt2, image2,
                       prompt3=None, image3=None, prompt4=None, image4=None):

        candidates = [
            (prompt1, image1),
            (prompt2, image2),
            (prompt3, image3),
            (prompt4, image4),
        ]

        items = []
        for prompt, image in candidates:
            if prompt is None or prompt.strip() == "":
                break
            items.append((prompt, image))

        count = len(items)
        if count == 0:
            raise ValueError("TKPromptLooper: no valid prompt/image pairs were supplied.")

        wrapped_index = index % count

        result_prompt, result_image = items[wrapped_index]

        return (wrapped_index, result_prompt, result_image)



class TKSmartVideoChunker:
    DESCRIPTION = "Silence-based video/audio chunking for LTX 2.3"

    """Silence-based video/audio chunking for LTX 2.3. Slices at native fps,
    resamples to target_fps, and snaps to a valid frame count (8n+1).
 
    Carries actual_end_time forward across loop iterations (via
    start_time_override) so chunk boundaries stay sample/frame accurate
    even when 8n+1 snapping trims or pads a chunk's true length.
    """
 
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "video": ("IMAGE", {"tooltip": "Source video"}),
                "audio": ("AUDIO", {"tooltip": "Source audio"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 9999,"tooltip": "Index from Loop - zero based"}),
                "chunk_secs": ("INT", {"default": 10,"tooltip": "Size of each video segment in seconds"}),
                "variation": ("INT", {"default": 2, "tooltip": "Num seconds variation.  chunks_secs +/- variation adds flexiblity to find silence"}),
                "source_fps": ("FLOAT", {"default": 30.0, "min": 1.0, "max": 240.0, "step": 0.01,
                                          "tooltip": "TRUE fps of incoming video tensor"}),
                "target_fps": ("FLOAT", {"default": 25.0, "min": 1.0, "max": 240.0, "step": 0.01,
                                          "tooltip": "fps required by LTX- usually 25"}),
            },
            "optional": {
                "start_time_override": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 999999.0, "step": 0.001,
                                                    "tooltip": "Use -1 for index 0, used to maintain exact timing of chunks."}),
            },
        }
 
    RETURN_TYPES = ("INT",          "IMAGE",         "AUDIO",       "INT",           "FLOAT",           "FLOAT",           "FLOAT",            "INT",)
    RETURN_NAMES = ("num_chunks", "chunkOImages", "chunkOfAudio", "numberFrames", "actual_end_time", "actual_start_time", "chunk_duration", "numLTXFrames",)
    FUNCTION = "get_video_chunk_at_index"
    CATEGORY = "TKNodes"
 
    def get_video_chunk_at_index(self, video, audio, index, chunk_secs, variation,
                                  source_fps, target_fps, start_time_override=-1.0):
        import torch
 
        # 1. Silence-based timing, real seconds, fps-agnostic
        audio_chunker = TKSmartAudioChunker()
        num_chunks, chunk_size, start_time, total_duration = audio_chunker.calculate(
            audio, index, chunk_secs, variation
        )


        # 1b. Override start_time with the carried actual end of the previous
        #     chunk, so boundaries stay contiguous regardless of 8n+1 snapping.
        if start_time_override is not None:
            if start_time_override >= 0.0:
                start_time = start_time_override

        # 2. Slice video at native fps
        total_frames = video.shape[0]
        start_frame = int(round(start_time * source_fps))
        true_end_frame = int(round((start_time + chunk_size) * source_fps))
        start_frame = max(0, min(start_frame, total_frames - 1))
        true_end_frame = max(start_frame + 1, min(true_end_frame, total_frames))

        # extend the native window so resampling has enough real frames
        # to round UP to the next 8n+1 boundary (never short)
        pad_native_frames = int(round(8 * (source_fps / target_fps))) + 1
        end_frame = min(true_end_frame + pad_native_frames, total_frames)

        native_chunk = video[start_frame:end_frame]
        native_frame_count = native_chunk.shape[0]
        true_native_frame_count = true_end_frame - start_frame  # unpadded, real target

        # 3. Resample native_fps -> target_fps
        true_chunk_duration = true_native_frame_count / source_fps
        true_target_frame_count = max(1, int(round(true_chunk_duration * target_fps)))

        actual_chunk_duration = native_frame_count / source_fps
        target_frame_count = max(1, int(round(actual_chunk_duration * target_fps)))

        if target_fps == source_fps:
            resampled_chunk = native_chunk
        else:
            src_indices = torch.round(
                torch.arange(target_frame_count, dtype=torch.float32) * (source_fps / target_fps)
            ).long()
            src_indices = torch.clamp(src_indices, 0, native_frame_count - 1)
            resampled_chunk = native_chunk[src_indices]

        # 4. Snap to valid LTX frame count (8n+1) - round UP, never down.
        #    generation_frames = what we ask LTX to generate (always >= true target)
        #    true_target_frame_count = what we trim back down to before writing to disk
        raw_count = resampled_chunk.shape[0]
        generation_frames = min(
            raw_count,
            8 * ((true_target_frame_count - 1) // 8 + 1) + 1
        )
        video_chunk = resampled_chunk[:generation_frames]
        number_frames = min(true_target_frame_count, generation_frames)  # trim target


 
        # 5. Slice audio to match, sample-accurate
        exact_video_duration = number_frames / target_fps
        print(f"[DEBUG] target_fps={target_fps} number_frames={number_frames} exact_video_duration={exact_video_duration}")

        waveform = audio['waveform']
        sample_rate = audio['sample_rate']
        total_samples = waveform.shape[-1]
 
        start_sample = int(round(start_time * sample_rate))
        end_sample = start_sample + int(round(exact_video_duration * sample_rate))
        start_sample = max(0, min(start_sample, total_samples - 1))
 
        if end_sample > total_samples:
            existing_waveform = waveform[..., start_sample:total_samples]
            missing_samples = end_sample - total_samples
            silence_pad = torch.zeros(
                (waveform.shape[0], waveform.shape[1], missing_samples),
                dtype=waveform.dtype, device=waveform.device
            )
            sliced_waveform = torch.cat([existing_waveform, silence_pad], dim=-1)
        else:
            sliced_waveform = waveform[..., start_sample:end_sample]
 
        audio_chunk = {"waveform": sliced_waveform, "sample_rate": sample_rate}
 
        # 6. Carry the real end time forward for the next iteration
        actual_end_time = start_time + exact_video_duration
 
        return (num_chunks, video_chunk, audio_chunk, number_frames, actual_end_time, start_time, exact_video_duration, generation_frames,)
 
 
 

# --- THE COMFYUI NODE ---
class TKSmartAudioChunker:

    DESCRIPTION = "Smart Audio Chunker is used to take an audio segment and split it up in chunks.  It searches for silence to split up the audio.  It also adds some silence to the chunks specifically for LTX"


    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",{"tooltip":"the Full audio that will get chunked"}), # Connect the gray wire here
                "index": ("INT", {"default": 0, "tooltip": "Index from the for loop" }),
                "chunk_secs": ("INT", {"default": 10, "tooltip": "Size of an Audio Chunk, for low VRAM use 5"}),
                "variation": ("INT", {"default": 2, "tooltip": "we separate when we find silence, this tells how far back and forward to search for silence"}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("num_chunks", "chunk_size", "start_time", "total_duration")
    FUNCTION = "calculate"
    CATEGORY = "HandyNodes-KT"

    def calculate(self, audio, index, chunk_secs, variation):
        # Run the private logic using the audio wire data
        splits = self.get_silence_splits_from_audio(audio, chunk_secs, variation)

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
    

    def get_silence_splits_from_audio(self, audio_data, chunk_size, variation):
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
    


class TKTrimImageOverlap:
    DESCRIPTION="Trims overlap frames from video segments when they have been previously paddded for various reasons"
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
    # This is what ComfyUI looks for to display a node-level description



    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":           ("IMAGE",{"tooltip":"source image with padding "}),
                "idx":             ("INT", {"default": 0, "min": 0, "max": 9999, "tooltip": "Index for audio chunks"}),
                "total_segments":  ("INT", {"default": 1, "min": 1, "max": 9999, "tooltip": "total audio chunks"}),
                "start_frames":    ("INT", {"default": 12, "min": 0, "max": 9999, "tooltip": "start frame to remove"}),
                "end_frames":      ("INT", {"default": 13, "min": 0, "max": 9999, "tooltip": "end framess to remove"}),
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
    DESCRIPTION = "LTX requires very specific frame counts.. this guarantees perfect LTX boundries"

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
                "chunk_secs": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 9999.0, "step": 0.001, "tooltip": "Seconds duration of audio chunk"}),
                "fps":        ("INT",   {"default": 25,  "min": 1,    "max": 240, "tooltip": "Frame per sec -usually 25 "}),
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





    