import nodes
import torch
import torch.nn.functional as F
import torchaudio
import random
import math
import torch
from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np

#  TK Collector -  Various Nodes for Comfy UI, TKPromptEnhanced
#  August 10, 2025
#  https://civitai.com/user/trashkollector175


any_type = type("AnyType", (str,), {"__ne__": lambda self, o: False})
ANY = any_type("*")



# --- PRIVATE INTERNAL FUNCTION (Hidden from ComfyUI) ---
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
            }
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
        
        return (
            num_chunks, 
            float(end_ms - start_ms) / 1000.0, # chunk_size
            float(start_ms) / 1000.0,          # start_time
            float(splits[-1]) / 1000.0         # total_duration
        )
        

class TKAudioUnwrap:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"audio": ("AUDIO",)}}

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("waveform",)
    FUNCTION = "unwrap"
    CATEGORY = "audio"

    def unwrap(self, audio):
        return (audio["waveform"],)


class TKPrintValueToLog:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (ANY,),
                "label": ("STRING", {"default": "debug"}),
            }
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("value",)
    OUTPUT_NODE = True
    FUNCTION = "log"
    CATEGORY = "debug"

    def log(self, value, label):
        print(f"[DEBUG] {label}: {value}")
        return (value,)


class TKMergeAudioList:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"audio_list": ("AUDIO",)}}
    
    # This is essential: it collects all clips into one list instead of looping the node
    INPUT_IS_LIST = True 
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "merge"
    CATEGORY = "HandyNodes-KT"

    def merge(self, audio_list):
        waveforms = [item['waveform'] for item in audio_list]
        sample_rate = audio_list[0]['sample_rate']
        
        # 1. Create a tiny fade (0.1 seconds) to hide the 'pop'
        fade_len = int(sample_rate * 0.1) 
        fade_in = torch.linspace(0.0, 1.0, fade_len)
        fade_out = torch.linspace(1.0, 0.0, fade_len)


        # 2. Process the list to apply fades to the joins
        merged_waveform = waveforms[0]
        for i in range(1, len(waveforms)):
            current_clip = waveforms[i]
            
            # --- SAFETY CHECK ADDED HERE ---
            # Ensure fade_len is not longer than the available audio in either clip
            actual_fade = min(fade_len, merged_waveform.shape[-1], current_clip.shape[-1])
            
            # If the clips are too short, adjust the fade tensors to match the actual_fade size
            current_fade_out = fade_out[:actual_fade] if actual_fade < fade_len else fade_out
            current_fade_in = fade_in[:actual_fade] if actual_fade < fade_len else fade_in
            # -------------------------------

            # Apply fades using the safe 'actual_fade' size
            merged_waveform[:, :, -actual_fade:] *= current_fade_out
            current_clip[:, :, :actual_fade] *= current_fade_in
                    
            merged_waveform = torch.cat([merged_waveform, current_clip], dim=-1)
            

        # 3. Flatten to Batch 1 as we did before
        if merged_waveform.shape[0] > 1:
            merged_waveform = merged_waveform.reshape(1, merged_waveform.shape[1], -1)

        return ({"waveform": merged_waveform, "sample_rate": sample_rate},)


# Remember to include your NODE_CLASS_MAPPINGS at the bottom of your file!


class TKGenerateAudioSplits:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_path": ("STRING", {"default": ""}),
                "chunk_size_secs": ("INT", {"default": 10, "min": 5, "max": 60}),
                "variation_secs": ("INT", {"default": 2, "min": 0, "max": 5}),
                "silence_thresh": ("INT", {"default": -40, "min": -100, "max": 0}),
            }
        }

    RETURN_TYPES = ("LIST", "INT")
    RETURN_NAMES = ("splits", "num_chunks")
    FUNCTION = "generate"
    CATEGORY = "HandyNodes-KT"

    def generate(self, audio_path, chunk_size_secs, variation_secs, silence_thresh):
        audio = AudioSegment.from_file(audio_path)
        total_ms = len(audio)
        
        target_ms = chunk_size_secs * 1000
        var_ms = variation_secs * 1000
        
        splits = [0] # Start at 0ms
        current_pos = 0
        
        while current_pos + (target_ms - var_ms) < total_ms:
            # Search Window: e.g., 8s to 12s
            search_start = current_pos + (target_ms - var_ms)
            search_end = min(current_pos + (target_ms + var_ms), total_ms)
            
            window = audio[search_start:search_end]
            silences = detect_silence(window, min_silence_len=300, silence_thresh=silence_thresh)
            
            if silences:
                # Split in middle of found silence
                s_start, s_end = silences[0]
                split_at = search_start + s_start + (s_end - s_start) // 2
            else:
                # Force cut at target if no silence found
                split_at = current_pos + target_ms
                
            splits.append(split_at)
            current_pos = split_at
            
        splits.append(total_ms)
        print(f"[TK DEBUG] Generated {len(splits)-1} splits: {splits}")
        return (splits, len(splits) - 1)


class TKCalcAudioChunks:
    """
    Splits audio into equal chunks, each as large as possible up to 15 seconds.

    Examples:
      10s -> 1 chunk of 10s
      20s -> 2 chunks of 10s
      26s -> 2 chunks of 13s
      60s -> 4 chunks of 15s

    Wire:
      audio          -> from Get_audio / Load Audio
      index          -> from For Loop Start (index)

    Outputs:
      num_chunks     -> For Loop Start (total)
      chunk_size     -> Trim Audio Duration (duration)
      start_time     -> Trim Audio Duration (start_index)
      total_duration -> optional / debug
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "index": ("INT", {"default": 0}),
            },
            "optional": {
                "chunk_secs": ("INT", {"default": 12}),
            }
            
        }

    RETURN_TYPES = ("INT", "FLOAT", "FLOAT", "FLOAT")
    RETURN_NAMES = ("num_chunks", "chunk_size", "start_time", "total_duration")
    FUNCTION = "calc"
    CATEGORY = "audio"

    def calc(self, audio, index, chunk_secs):
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]

        num_samples = waveform.shape[-1]
        total_duration = num_samples / sample_rate

        if total_duration <= chunk_secs:
            num_chunks = 1
            chunk_size = total_duration
        else:
            num_chunks = math.ceil(total_duration / chunk_secs)
            chunk_size = total_duration / num_chunks
        start_time = index * chunk_size

        print(f"[CalcAudioChunks] total={total_duration:.2f}s  chunks={num_chunks}  chunk_size={chunk_size:.2f}s  start={start_time:.2f}s")

        return (num_chunks, chunk_size, start_time, total_duration)

    
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
                    ["Use # Frames", "Use # Seconds"],
                ),
                "total_frames": ("INT", {"default": 81,   "min": 32, "max": 1000, "description" : "This value applies when length_selector = Use Frames"}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000, "description" : "This value applies when length_selector = Use Seconds"}),
                "fps":         ("FLOAT", {"default": 16.0, "min": 16.0, "max": 60.0, "description" : "FPS from video info node"}),
                

            },
        }

    RETURN_TYPES = ("INT", "INT","INT","FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames","fps")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Common Video User Inputs-  Use the Length_Selector to determine if you want to select by frames or seconds"

    def main(self, width, height, total_frames, length_selector, fps, num_seconds, ):
     
        if (length_selector=="Use # Seconds") :
            total_frames = int(fps * num_seconds)
        return (width, height, total_frames, fps )





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



    
       
        
        
class TKVideoAudioFuse :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "image": ("IMAGE",),
                              
                "audio1": ("AUDIO",),  
            
                "audio1_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                

            },
        
            "optional": {
            
                "audio2": ("AUDIO",),    
                "audio2_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    

                "audio3": ("AUDIO",),    
                "audio3_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    
            }
        }
        

    RETURN_TYPES = ("IMAGE",  "AUDIO")
    RETURN_NAMES = ("image",  "audio")


    FUNCTION = "tkvideoaudiofuse"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"
    DESCRIPTION = "Fuse/Overlayt up to 3 audio streams and 1 video together.  "

    
    def tkvideoaudiofuse(self, image, audio1,  audio1_volume,   audio2_volume,  audio3_volume, audio2=None, audio3=None, ):
        audio_tensor1 = audio1['waveform']      
        sr = audio1["sample_rate"]
        avg1 = self.adjustVolume(audio_tensor1, audio1_volume)
        
 
        if  audio2 is not None :
            sr2 =audio2["sample_rate"]
            aud2 =  self.adjustVolume(audio2["waveform"], audio2_volume)
            (avg1, sr) = self.average_audio_tensors(avg1, aud2, sr, sr2 )
        
        if audio3 is not None :
            sr3 =audio3["sample_rate"]
            aud3 =  self.adjustVolume(audio3["waveform"], audio3_volume)
            (avg1, sr) = self.average_audio_tensors(avg1, aud3, sr, sr3 )
    
        audio = {
           "waveform": avg1,
           "sample_rate": sr
        }
        return ( image, audio)
        

    def adjustVolume(self, tensor, vol) :
        gain_in_db = vol*3

        # Apply the volume transform
        vol_transform = torchaudio.transforms.Vol(gain=gain_in_db, gain_type='db')
        new_tensor = vol_transform(tensor)
        
        return new_tensor
        
        
    def average_audio_tensors(self,
        audio1,
        audio2,
        sr1,
        sr2
    ) :
        """
        Averages two audio tensors of potentially different lengths and channel counts.

        It resamples tensors to a common sample rate, converts them to mono, pads the 
        shorter tensor with zeros, and then averages the result.

        Args:
            audio1 (torch.Tensor): The first audio tensor.
                                   Expected shape: [channels, frames].
            audio2 (torch.Tensor): The second audio tensor.
                                   Expected shape: [channels, frames].
            sr1 (int): The sample rate of the first audio tensor.
            sr2 (int): The sample rate of the second audio tensor.

        Returns:
            torch.Tensor: A new tensor representing the average of the two inputs, 
                          as a mono signal.
        """
        
        if not isinstance(audio1, torch.Tensor) or not isinstance(audio2, torch.Tensor):
            raise TypeError("Inputs must be PyTorch tensors.")

        # Step 1: Resample tensors to a common sample rate
        target_sr = min(sr1, sr2)
        if sr1 != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr1, new_freq=target_sr)
            audio1 = resampler(audio1)
        if sr2 != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr2, new_freq=target_sr)
            audio2 = resampler(audio2)

        # Step 2: Convert tensors to mono if they have more than one channel
        # This is done by averaging the channels
        if audio1.shape[1] > 1:
            audio1 = torch.mean(audio1, dim=0, keepdim=True)
        if audio2.shape[1] > 1:
            audio2 = torch.mean(audio2, dim=0, keepdim=True)

        # Step 3: Pad the shorter tensor to match the length of the longer tensor

        max_len = max(audio1.shape[2], audio2.shape[2])
        
        if audio1.shape[2] < max_len:
            padding_needed = max_len - audio1.shape[2]
            padded_audio1 = F.pad(audio1, (0, padding_needed), 'constant', 0)
        else:
            padded_audio1 = audio1

        if audio2.shape[2] < max_len:
            padding_needed = max_len - audio2.shape[2]
            padded_audio2 = F.pad(audio2, (0, padding_needed), 'constant', 0)
        else:
            padded_audio2 = audio2

        # Step 4: Average the padded tensors
        averaged_audio = (padded_audio1 + padded_audio2) / 2

        return (averaged_audio, target_sr)


class TKAudioFuse :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "audio1": ("AUDIO",),  
                "audio1_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                
                "audio2": ("AUDIO",),    
                "audio2_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),   
            },
            "optional": {
                "audio3": ("AUDIO",),    
                "audio3_volume" : ("INT", {"default":0,"min":-10,"max":10, "description":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    
            }
        }
        
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "tkaudiofuse"
    #OUTPUT_NODE = False
    CATEGORY = "TKNodes"
    DESCRIPTION = "Fuse/Overlay up to 3 audio streams together"

    
    def tkaudiofuse(self, audio1,  audio1_volume,   audio2 , audio2_volume,  audio3_volume,  audio3 =None, ):
       
        vidaud_obj = TKVideoAudioFuse()
        

        audio_tensor1 = audio1['waveform']      
        sr = audio1["sample_rate"]
        avg1 = vidaud_obj.adjustVolume(audio_tensor1, audio1_volume)
        
 
        if  audio2 is not None :
            sr2 =audio2["sample_rate"]
            aud2 =  vidaud_obj.adjustVolume(audio2["waveform"], audio2_volume)
            (avg1, sr) = vidaud_obj.average_audio_tensors(avg1, aud2, sr, sr2 )
        
        if audio3 is not None :
            sr3 =audio3["sample_rate"]
            aud3 =  vidaud_obj.adjustVolume(audio3["waveform"], audio3_volume)
            (avg1, sr) = vidaud_obj.average_audio_tensors(avg1, aud3, sr, sr3 )
            
        print(avg1.shape )
        audio = {
           "waveform": avg1,
           "sample_rate": sr,
        }
     
        return (audio,)
        

   
