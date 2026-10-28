import torch
import torch.nn.functional as F
import torch
from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np
import math


#  TK Collector -  Various Nodes for Comfy UI, TKPromptEnhanced
#  August 10, 2025
#  https://civitai.com/user/trashkollector175

any_type = type("AnyType", (str,), {"__ne__": lambda self, o: False})
ANY = any_type("*")
######################################################################################
# Remember to include your NODE_CLASS_MAPPINGS at the bottom of your file!







    

class TKPromptEnhanced:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
            
                "positve_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Positve prompt here!",
                           }),
                "negative_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Incorrect body proportions. bad drawing, bad anatomy, bad body shape, blurred details, awkward poses, incorrect shadows, unrealistic expressions, lack of texture, poor composition, text, logo, out of aspect ratio, body not fully visible, ugly, defects, noise, fuzzy, oversaturated, soft, blurry, out of focus, frame",
                    "lazy": True             }),
               
                "use_cam_options" : ("BOOLEAN", {
                    "default" : True, "description":"Disable/Enable Camera options.  These camera descriptions simply get appended to the positive text."}),
                
                "camera_shot_size": ([
                            "-",
                            "The camera takes an extreme closeup. ",
                            "The camera takes a closeup. ",
                            "The camera takes a medium shot ",
                            "The camera takes a medium full shot. ",
                            "The camera takes a full shot. ",
                            "The camera takes an extreme wide shot",
                            "The camera takes a wide shot",
                               ],),
                "camera_focus": ([
                            "-",
                            "The main person is in focus. ",
                            "The main person is in focus, the background objects are out of focus. ",
                            "All objects in the scene are in focus. ",
                            "The camera takes a tilt-shift focus shot. ",
                            "The camera takes a shot with soft focus. ",
                            "The camera takes a split diopeter shot. ",
                               ],),
                            
                "camera_angle":([
                            "-",
                           
                            "The camera is filming at eye level. ",
                            "The camera is filming at low angle.",       
                            "The camera is filming at hip level.", 
                            "The camera is filming at a knee level.", 
                            "The camera is filming at a ground level.", 
                            "The camera is filming at a low angle.", 
                            "The camera is filming at a shoulder level.", 
                            "The camera is overhead.", 
                            "The camera is taking an aerial shot.", 

                            ],),
                            
                "camera_movement":([
                            "-",
                            "The camera is stationary.",
                            "The camera is jittery",
                            "The camera is zooming in. ",
                            "The camera is zooming out. ",       
                            "The camera is panning right. ", 
                            "The camera is panning right. ", 
                            "The camera tilts up. ", 
                            "The camera tilts down. ", 
                            "The camera orbits. ", 
 
                            ],),
                            
                "light": (["-",
                            "Scene has warm light. ",
                            "Scene has midday light.",
                            "Scene has morning light. ",
                            "Scene  has evening light. ",
                            "There is a spotlight on the subject. ",
                            "The scene has backlighting. ",
                            "The scene has dramatic lighting. ",
                            "The scene has bright neon lighting. ",
                            "The scene has low light. ",
                            "The scene has harsh shadows. ",
                            "The scene has specular lighting. ",
                            "The scene has soft diffused lighting. ",
                            "The scene has radiant rays. ",
                            "The scene is luminescent.     ",    ],), 
                            

                                      
                }
            }
        

    RETURN_TYPES = ("STRING","STRING")
    RETURN_NAMES = ("positive","negative")
    FUNCTION = "tkpromptenhanced"
    #OUTPUT_NODE = False
    CATEGORY = "TKNodes"
    DESCRIPTION = "Enhanced prompt, contains camera controls which are appended to the positive prompt"

    
    def tkpromptenhanced(self, positve_prompt, negative_prompt,use_cam_options, camera_shot_size, camera_angle, camera_focus, camera_movement, light):
        
        
        pos = positve_prompt 
        
        if use_cam_options == True:
           pos =    positve_prompt+ ". "+ camera_angle+". "+ camera_focus+". "+ camera_movement+". "+ camera_shot_size+". "+ light
        
            
        return (pos,negative_prompt)
        

class TKVideoUserInputs:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "height": ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "length_selector": (
                                ["Use # Seconds", "Use # Frames"], # "Use # Seconds" is now the default
                                {"default": "Use # Seconds"}       # Explicitly defining the default
                            ),
                "total_frames": ("INT", {"default": 97,   "min": 10, "max": 1000, "tooltip" : "This value applies when length_selector = Use Frames"}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000, "tooltip" : "This value applies when length_selector = Use Seconds"}),
                "fps":         ("FLOAT", {"default": 24.0, "min": 16.0, "max": 60.0, "tooltip" : "FPS from video info node"}),
                

            },
        }

    RETURN_TYPES = ("INT",              "INT",         "INT",    "FLOAT", "FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames","fps", "totalSeconds")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "GUI for setting video resolution , frames, duration"

    def main(self, width, height, total_frames, length_selector, fps, num_seconds, ):
     
        returnSecs = num_seconds
        if (length_selector=="Use # Seconds") :
            total_frames = int(fps * num_seconds)
        else :
            returnSecs =   float(total_frames) / fps;
        

        return (width, height, total_frames, fps, returnSecs )

    

class TKVideoUserInputsV2:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "height": ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000, "tooltip": "This value applies when length_selector = Use Seconds"}),
                "model_type": (["LTX", "WAN"], {
                    "default": "LTX",
                    "tooltip": "Target model frame-count boundary: LTX=8n+1, WAN=4n+1, None=no snapping"
                }),
            },
        }

    RETURN_TYPES = ("INT", "INT", "INT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames", "fps", "total_secs")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "GUI for setting video resolution, frames, duration"

    # frames must be (step * n + 1) for these models
    FRAME_STEP = {"LTX": 8, "WAN": 4}

    def main(self, width, height,  num_seconds, model_type="LTX"):

        fps = 25
        if (model_type == "WAN"):
            fps=16
        
        total_frames = int(round(fps * num_seconds))

        step = self.FRAME_STEP.get(model_type)
        if step:
            n = max(1, int(round((total_frames - 1) / step)))
            total_frames = n * step + 1

        # report the duration of the frame count actually returned
        total_seconds = float(total_frames) / fps

        return (width, height, total_frames, fps, total_seconds)






class TKVideoUserInputsBasic:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "height": ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
               
               },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("video_width", "video_height")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Common Video User Inputs- Basic"

    def main(self, width, height ):
     
        
        return (width, height )




class TKPhotoUserInputs:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 3000, "min": 100, "max": 3000, "step": 64}),
                "height": ("INT", {"default": 3000, "min": 100, "max": 3000, "step": 64}),
               
               },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("photo_width", "photo_height")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Photo User Inputs"

    def main(self, width, height ):
     
        
        return (width, height )



class TKFadeInVideo:
    DESCRIPTION="Fade in Video"
    """Fades in the first N frames of a video from black (or a chosen color)
    to full opacity. Frame 1 = 0% opaque, frame N = 100% opaque, frames
    after N are untouched. Intended to run right after VAE Decode."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Decoded video frames [N, H, W, C]"}),
                "fade_frames": ("INT", {"default": 5, "min": 1, "max": 240,
                                         "tooltip": "Number of frames to fade in over. "
                                                     "Frame 'fade_frames' reaches 100%."}),
                "start_alpha": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                                           "tooltip": "Starting opacity at frame 1 (0.5 = 50%). "
                                                       "Ramps up to 1.0 by fade_frames."}),
            },
            "optional": {
                "fade_color": ("STRING", {"default": "0,0,0",
                                           "tooltip": "R,G,B (0-255) to fade in from. Default black."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "fade_in"
    CATEGORY = "TKNodes"

    def fade_in(self, images, fade_frames, start_alpha=0.5, fade_color="0,0,0"):
        import torch
           
        total_frames = images.shape[0]
        n = min(fade_frames, total_frames)

        # Parse fade color -> normalized 0-1 tensor matching channel count
        try:
            r, g, b = [float(c.strip()) / 255.0 for c in fade_color.split(",")]
        except Exception:
            r, g, b = 0.0, 0.0, 0.0

        channels = images.shape[-1]
        if channels == 4:
            color = torch.tensor([r, g, b, 1.0], dtype=images.dtype, device=images.device)
        else:
            color = torch.tensor([r, g, b], dtype=images.dtype, device=images.device)

        result = images.clone()

        # Opacity ramps linearly from start_alpha -> 1.0 (fully opaque/original)
        # frame 1 -> start_alpha, frame n -> 1.0
        alpha_range = 1.0 - start_alpha
        for i in range(n):
            alpha = start_alpha + alpha_range * ((i + 1) / n)
            frame = images[i]
            faded = frame * alpha + color * (1.0 - alpha)
            result[i] = faded.clamp(0.0, 1.0)

        return (result,)



            

class TKCrossDissolve:
    DESCRIPTION="Cross Dissolve two video segments together to make transition seamless"
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "curr_scene": ("IMAGE",  {  "tooltip": "the current video segment. "}),
                "curve": (["linear", "ease_in_out"],  { "tooltip": "select Cross dissolve effect. "}),
            },
            "optional": {
                "prev_tail": ("IMAGE",  {"tooltip": "previous video segment to cross-dissolve. "}),  # absent/empty on segment 1
                "numDissolveFrames": ("INT", {"default": 20, "min": 0, "max": 1000, "tooltip": "number of frames to cross-dissolve. if <=0, uses the full length of prev_tail instead."}),
            }
        }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "blend"
    CATEGORY = "TKNodes"

    def blend(self, curr_scene, curve, prev_tail=None, numDissolveFrames=0):

        if prev_tail is None or prev_tail.shape[0] == 0:
            return (curr_scene,)

        if numDissolveFrames is not None and numDissolveFrames > 0:
            # take only the last numDissolveFrames of prev_tail, clamped to what's available
            tail_n = min(numDissolveFrames, prev_tail.shape[0])
            prev_tail = prev_tail[-tail_n:]

        n = min(prev_tail.shape[0], curr_scene.shape[0])
        print(f"[dissolve] n={n}, curve={curve}")

        curr_head = curr_scene[:n]
        curr_rest = curr_scene[n:]

        alphas = torch.linspace(0, 1, n)
        if curve == "ease_in_out":
            alphas = alphas * alphas * (3 - 2 * alphas)

        blended = torch.stack([
            (1 - a) * prev_tail[i] + a * curr_head[i]
            for i, a in enumerate(alphas)
        ])

        out = torch.cat([blended, curr_rest], dim=0)
        return (out,)



class TKColorMatchTransition:
    DESCRIPTION = "Matches the color of the start of the current clip to the end of the previous clip, easing back to the original over N frames."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "curr_scene": ("IMAGE", {"tooltip": "the current video segment (the one that gets color-corrected). "}),
                "prev_scene": ("IMAGE", {"tooltip": "previous video segment. if empty, curr_scene passes through unchanged. "}),
                "numTransitionFrames": ("INT", {"default": 20, "min": 0, "max": 1000, "tooltip": "number of frames at the start of curr_scene to correct. if <=0, uses the full length of curr_scene."}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "match"
    CATEGORY = "TKNodes"

    def match(self, curr_scene, prev_scene, numTransitionFrames):

        if prev_scene is None or prev_scene.shape[0] == 0:
            return (curr_scene,)

        total = curr_scene.shape[0]
        n = total if numTransitionFrames <= 0 else min(numTransitionFrames, total)

        # measure color of the last frames of prev and the first frames of curr
        ref = prev_scene[-5:].to(curr_scene.device).float()
        src = curr_scene[:5].float()
        ref_mean, ref_std = ref.mean(dim=(0, 1, 2)), ref.std(dim=(0, 1, 2))
        src_mean, src_std = src.mean(dim=(0, 1, 2)), src.std(dim=(0, 1, 2))
        gain = (ref_std / src_std.clamp(min=1e-4)).clamp(0.5, 2.0)

        head = curr_scene[:n].float()
        matched = (head - src_mean) * gain + ref_mean

        # 1.0 on the first frame, easing to 0.0 on the last frame of the window
        alphas = torch.linspace(0, 1, n, device=curr_scene.device)
        alphas = alphas * alphas * (3 - 2 * alphas)
        w = (1 - alphas).view(-1, 1, 1, 1)

        corrected = (head + w * (matched - head)).clamp(0.0, 1.0).to(curr_scene.dtype)
        out = torch.cat([corrected, curr_scene[n:]], dim=0)
        return (out,)




class TKTrimFrames:
    DESCRIPTION = "Trims video and audio as one unified action. Determines this by checking FPS."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frame_count": ("INT", {"default": 1, "min": 1, "max": 100000,
                                        "tooltip": "max frames to keep after start_frame (clamped to what's available)"}),
                "target_fps": ("FLOAT", {"default": 25.0, "min": 1.0, "max": 240.0}),
            },
            "optional": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                "start_frame": ("INT", {"default": 0, "min": 0, "max": 100000,
                                        "tooltip": "frames to cut from the beginning"}),
                "trim_on_mismatch": ("BOOLEAN", {"default": True,
                                        "tooltip": "if audio ends before the requested duration, shorten the frames to match"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "AUDIO", "INT")
    RETURN_NAMES = ("images", "audio", "frame_count")
    FUNCTION = "trim"
    CATEGORY = "TKNodes"

    def trim(self, frame_count, target_fps, images=None, audio=None,
             start_frame=0, trim_on_mismatch=True):
        start_frame = start_frame or 0
        n = frame_count  # effective frame count, only ever shrinks

        # Clamp to the frames that exist
        if images is not None:
            n = min(n, images.shape[0] - start_frame)

        # Clamp to the audio that exists
        out_audio = None
        if audio is not None:
            waveform = audio["waveform"]
            sr = audio["sample_rate"]
            total = waveform.shape[-1]
            start_s = int(round(start_frame / target_fps * sr))

            if trim_on_mismatch:
                frames_left = int(round(max(total - start_s, 0) / sr * target_fps))
                n = min(n, frames_left)

            n = max(n, 1)  # never return nothing, so downstream nodes don't crash

            start_s = min(start_s, max(total - 1, 0))
            end_s = min(int(round((start_frame + n) / target_fps * sr)), total)
            end_s = max(end_s, min(start_s + 1, total))
            out_audio = {"waveform": waveform[..., start_s:end_s], "sample_rate": sr}
        else:
            n = max(n, 1)

        out_images = None
        if images is not None:
            s = min(start_frame, max(images.shape[0] - 1, 0))
            out_images = images[s:s + n]

        return (out_images, out_audio, n)


"""
TKLargeVideoChunker
------------------
Streams one chunk of a very large video file straight from disk, so the whole
video never has to be loaded into RAM/VRAM. Wire `index` to your loop counter
and use `number_chunks` to know when to stop.

Inputs
    path_vid_file  (STRING)  full path to the video file
    chunk_seconds  (INT)     length of each chunk in seconds
    index          (INT)     which chunk to return (0-based)
    max_duration   (INT)     seconds of video to use, counted from the start;
                             0 = full duration

Outputs
    number_chunks  (INT)     total number of chunks in the file
    chunkOfImages  (IMAGE)   frames of this chunk  [N, H, W, 3] float32 0-1
    chunkOfAudio   (AUDIO)   audio of this chunk, sample-aligned to the frames
    fps            (FLOAT)   frame rate of the video file

Requires: ffmpeg (on PATH, or via the imageio-ffmpeg package, which VHS ships)
          and PyAV ("av"), which ComfyUI already depends on.
"""

import math
import os
import shutil
import subprocess
import sys

import numpy as np
import torch


def _find_ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise RuntimeError(
        "TKLargeVideoLooper: ffmpeg not found. Put ffmpeg on PATH or "
        "`pip install imageio-ffmpeg` in the ComfyUI Python environment."
    )


def _clean_path(p):
    # Handles Windows "Copy as path" quotes and stray whitespace
    if not isinstance(p, str) or not p.strip():
        return ""
    return os.path.normpath(p.strip().strip('"').strip("'"))


def _probe(path):
    import av

    with av.open(path, mode="r") as c:
        assert isinstance(c, av.container.InputContainer)
        if not c.streams.video:
            raise RuntimeError(f"No video stream found in: {path}")
        vs = c.streams.video[0]
        rate = vs.average_rate or vs.guessed_rate
        if not rate:
            raise RuntimeError("Could not determine the video frame rate.")
        fps = float(rate)
        width = vs.codec_context.width
        height = vs.codec_context.height

        duration = None
        if vs.duration is not None and vs.time_base is not None:
            duration = float(vs.duration * vs.time_base)
        elif c.duration:
            duration = float(c.duration / av.time_base)

        total_frames = int(vs.frames) if vs.frames else 0
        if total_frames <= 0:
            if duration is None:
                raise RuntimeError("Could not determine the video length.")
            total_frames = int(round(duration * fps))

        audio = None
        if c.streams.audio:
            a = c.streams.audio[0]
            audio = (int(a.rate), int(a.channels))

    return fps, width, height, total_frames, audio


def _popen(cmd, **kw) -> "subprocess.Popen[bytes]":
    flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    return subprocess.Popen(cmd, creationflags=flags, **kw)


class TKLargeVideoChunker:
    DESCRIPTION="Helps avoid memory issues with large videos.   Meant to be run within FOR LOOP START/END.  index = current loop counter. Take an large video file an process a chunk at a time.  Use chunk_seconds to define chunk size, use max_duration (seconds) to define how much of video to process. "
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path_vid_file": ("STRING", {"default": "", "multiline": False}),
                "chunk_seconds": ("INT", {"default": 10, "min": 1, "max": 3600, "step": 1}),
                "index": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "max_duration": ("INT", {"default": 0, "min": 0, "max": 86400, "step": 1}),
            }
        }

    RETURN_TYPES = ("INT", "IMAGE", "AUDIO", "FLOAT", "IMAGE")
    RETURN_NAMES = ("number_chunks", "chunkOfImages", "chunkOfAudio", "fps", "start_frame")
    FUNCTION = "load_chunk"
    CATEGORY = "TKNodes/video"

    @classmethod
    def IS_CHANGED(cls, path_vid_file, chunk_seconds, index, max_duration=0):
        # When an input is wired from another node, ComfyUI calls IS_CHANGED
        # before that node has run, so the values can be None. Always re-run then.
        if path_vid_file is None or chunk_seconds is None or index is None or max_duration is None:
            return float("nan")
        p = _clean_path(path_vid_file)
        try:
            return f"{os.path.getmtime(p)}_{chunk_seconds}_{index}_{max_duration}"
        except OSError:
            return float("nan")

    def load_chunk(self, path_vid_file, chunk_seconds, index, max_duration=0):
        path = _clean_path(path_vid_file)
        if not path:
            raise ValueError("TKLargeVideoLooper: path_vid_file is empty.")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"TKLargeVideoLooper: file not found: {path}")

        ffmpeg = _find_ffmpeg()
        fps, width, height, total_frames, audio_info = _probe(path)

        # max_duration > 0 limits processing to the first N seconds
        if max_duration and max_duration > 0:
            total_frames = max(1, min(total_frames, int(round(max_duration * fps))))

        frames_per_chunk = max(1, int(round(chunk_seconds * fps)))
        number_chunks = max(1, math.ceil(total_frames / frames_per_chunk))

        if index < 0 or index >= number_chunks:
            raise ValueError(
                f"TKLargeVideoLooper: index {index} out of range "
                f"(file has {number_chunks} chunks, valid 0..{number_chunks - 1})."
            )

        start_frame = index * frames_per_chunk
        want_frames = min(frames_per_chunk, total_frames - start_frame)
        start_time = start_frame / fps

        # ---------- video ----------
        cmd = [
            ffmpeg, "-v", "error", "-nostdin", "-noautorotate",
            "-ss", f"{start_time:.6f}", "-i", path,
            "-frames:v", str(want_frames),
            "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ]
        frame_bytes = width * height * 3
        images = torch.empty((want_frames, height, width, 3), dtype=torch.float32)
        n_read = 0
        proc = _popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None and proc.stderr is not None
        try:
            while n_read < want_frames:
                buf = proc.stdout.read(frame_bytes)
                if len(buf) < frame_bytes:
                    break
                arr = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3)
                images[n_read] = torch.from_numpy(arr.copy()).float().div_(255.0)
                n_read += 1
        finally:
            proc.stdout.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            proc.stderr.close()
            proc.wait()

        if n_read == 0:
            raise RuntimeError(f"TKLargeVideoLooper: ffmpeg returned no frames. {err}")
        images = images[:n_read]  # last chunk can be shorter than expected

        # ---------- audio ----------
        duration = n_read / fps
        if audio_info is not None:
            sr, ch = audio_info
            expected = int(round(duration * sr))
            acmd = [
                ffmpeg, "-v", "error", "-nostdin",
                "-ss", f"{start_time:.6f}", "-t", f"{duration:.6f}", "-i", path,
                "-vn", "-f", "f32le", "-acodec", "pcm_f32le",
                "-ar", str(sr), "-ac", str(ch), "-",
            ]
            aproc = _popen(acmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            raw = aproc.communicate()[0]
            samples = np.frombuffer(bytes(raw), dtype=np.float32)
            samples = samples[: (len(samples) // ch) * ch].reshape(-1, ch)
            wave = torch.from_numpy(samples.copy()).t().contiguous()  # [C, S]
            # lock audio length to the video chunk so they stay in sync
            if wave.shape[1] < expected:
                wave = torch.nn.functional.pad(wave, (0, expected - wave.shape[1]))
            else:
                wave = wave[:, :expected]
        else:
            sr, ch = 44100, 2
            wave = torch.zeros((ch, int(round(duration * sr))), dtype=torch.float32)

        audio_out = {"waveform": wave.unsqueeze(0), "sample_rate": sr}  # [1, C, S]

          # Extract just the first frame while keeping the 4D batch structure ComfyUI expects
        first_frame_only = images[0:1]

        return (number_chunks, images, audio_out, float(fps), first_frame_only)


