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

######################################################################################

class TKSpeakerAudioTrackExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "fullaudio": ("AUDIO",),
                "combinedTrackInfo1": ("STRING", {"forceInput": True}),
                "combinedTrackInfo2": ("STRING", {"forceInput": True}),
                "padAudioForLtx" : ("BOOLEAN", {"default": True}),
                "index": ("INT", {"default": 1, "min": 1, "max": 10}),
            }
        }

    RETURN_TYPES = ("AUDIO",        "INT"  ,        "INT"      ,"INT")
    RETURN_NAMES = ("audioTrack","totalTracks", "numFrames" , "speakerNum")
    FUNCTION = "extractSpeakerTrackAudio"
    CATEGORY = "TKNodes"

    def extractSpeakerTrackAudio(self, fullaudio, combinedTrackInfo1, combinedTrackInfo2, index, padAudioForLtx):
        # 1. Get the startTime and EndTime by calling the helper function

        combinedTrackInfo = self.mergeAndSortTracks(combinedTrackInfo1, combinedTrackInfo2)
        start_time, end_time , speaker = getTrack(index, combinedTrackInfo)

      
        print(f"INDEX {index}: start={start_time}, end={end_time}, duration={end_time-start_time:.2f}s")

      

        if (speaker=="speaker1"):
            speakerNum=1
        elif (speaker=="speaker2"):
            speakerNum=2
        else: 
            speakerNum=0

        #  Extract the waveform and sample rate
        waveform = fullaudio["waveform"] # shape: [batch, channels, samples]
        sample_rate = fullaudio["sample_rate"]
        
        # Calculate sample indices
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)
        
        # Bounds checking to prevent index errors
        max_samples = waveform.shape[-1]
        max_duration = max_samples / sample_rate

        # ✅ Validate before slicing
        if start_time >= max_duration:
            raise ValueError(f"INDEX {index}: ERROR  start_time {start_time:.2f}s exceeds audio length {max_duration:.2f}s")
        if end_time > max_duration:
            raise ValueError(f"INDEX {index}: ERROR end_time {end_time:.2f}s exceeds audio length {max_duration:.2f}s — ERROR - Make sure you entered correct Speaker Times!")

        
        start_idx = max(0, min(start_sample, max_samples))
        end_idx = max(0, min(end_sample, max_samples))

   
        print(f"sample_rate={sample_rate}")
        print(f"waveform.shape={waveform.shape}")
        print(f"max_samples={max_samples}")
        print(f"start_sample={start_sample}, end_sample={end_sample}")
        print(f"start_idx={start_idx}, end_idx={end_idx}")

        # pad with 0.5 of leading silence and 0.3 of trailing silence
        if (padAudioForLtx):
            # --- 1. Silence durations (in seconds → samples) ---
            start_padding_samples = int(0.5 * sample_rate)
            end_padding_samples   = int(0.3 * sample_rate)

            if end_sample > max_samples:
                # Amount of missing audio
                missing = end_sample - max_samples

                # Slice what exists
                sliced = waveform[:, :, start_idx:max_samples]

                # Pad the missing tail with silence
                pad = torch.zeros(
                    (waveform.shape[0], waveform.shape[1], missing),
                    device=waveform.device,
                    dtype=waveform.dtype
                )

                new_waveform = torch.cat([sliced, pad], dim=-1)

            else:
                new_waveform = waveform[:, :, start_idx:end_idx]
              

            # --- 3. Prepend + append silence ---
            leading_silence = torch.zeros(
                (new_waveform.shape[0], new_waveform.shape[1], start_padding_samples),
                device=new_waveform.device,
                dtype=new_waveform.dtype
            )

            trailing_silence = torch.zeros(
                (new_waveform.shape[0], new_waveform.shape[1], end_padding_samples),
                device=new_waveform.device,
                dtype=new_waveform.dtype
            )

            # --- 4. Final waveform ---
            final_waveform = torch.cat(
                [leading_silence, new_waveform, trailing_silence],
                dim=-1
            )
        else:  # NO PADDING - get wave form using start and end times
            # Slice the waveform directly using the safe bounds calculated earlier
            final_waveform = waveform[:, :, start_idx:end_idx]
            
            # Define new_waveform as well so the print statement doesn't error out
            new_waveform = final_waveform


        print(
            f"INDEX {index}: start={start_time}, end={end_time}, "
            f"duration={end_time-start_time:.2f}s | "
            f"new_waveform={new_waveform.shape[-1]} samples | "
            f"final_waveform={final_waveform.shape[-1]} samples")

        totalTracks, last_time_stamp = self.getTotalTracks(combinedTrackInfo)
        if (last_time_stamp >= max_duration):
           raise ValueError(f" ERROR: Your timings exceeds the Audio Length - Fix your inputs - size {max_duration:.2f} seconds")

        nFrames = int(round((end_time - start_time) * 25)+25)


        # Force all numeric outputs to pure integers
        return (
            {"waveform": final_waveform, "sample_rate": sample_rate}, 
            int(totalTracks), 
            int(nFrames), 
            int(speakerNum)
        )




    def mergeAndSortTracks(self, combined_string1, combined_string2):
        # 1. Helper to parse string into pairs with a speaker label
        def parse_to_labeled_pairs(s, speaker_label):
            raw = [float(x.strip()) for x in s.split(",") if x.strip()]
            it = iter(raw)
            # Only keep tracks that aren't (0.0, 0.0)
            return [(start, end, speaker_label) for start, end in zip(it, it) 
                    if start != 0.0 or end != 0.0]

        # 2. Parse both inputs
        tracks1 = parse_to_labeled_pairs(combined_string1, "speaker1")
        tracks2 = parse_to_labeled_pairs(combined_string2, "speaker2")

        # 3. Combine and sort by start time
        all_tracks = sorted(tracks1 + tracks2)

        # 4. Flatten into strings and Debug
        final_values = []
        print(f"\n{'#' : <5} | {'Speaker' : <10} | {'Start' : <10} | {'End' : <10}")
        print("-" * 45)
        
        for i, (start, end, speaker) in enumerate(all_tracks, 1):
            # Debug Print
            print(f" {i : <5} | {speaker : <10} | {start : <10} | {end : <10}")
            
            # Append to result list
            final_values.extend([str(start), str(end), speaker])

        # 5. Join with commas
        return ",".join(final_values)


    



    def getTotalTracks(self, combined_string):
        if isinstance(combined_string, tuple):
            combined_string = combined_string[0]

        if not combined_string or not str(combined_string).strip():
            return 0, 0.0
            
        parts = str(combined_string).split(",")
        num_parts = len(parts)
        total_populated = 0
        max_end_time = 0.0 
        
        # Step through in chunks of 3 (start, end, label)
        for i in range(0, num_parts - 2, 3):
            try:
                start_val = parts[i].strip()
                end_val = parts[i+1].strip()
                
                # Basic string check to ensure we have numbers
                if not start_val or not end_val:
                    continue
                    
                start = float(start_val)
                end = float(end_val)

                # 1. Check for 'Empty/Padding' tracks (0,0)
                # If we hit 0,0, we assume the data ends here and stop counting
                if start == 0.0 and end == 0.0:
                    break 

                # 2. STRICT VALIDATION: If data exists but is nonsensical, 
                # return 0 for everything to block further processing.
                if start < 0 or end < 0 or start >= end:
                    print(f"CRITICAL ERROR: Invalid timestamps found (Start: {start}, End: {end})")
                    return 0, 0.0

                # 3. Track valid data
                total_populated += 1
                if end > max_end_time:
                    max_end_time = end
                
            except (ValueError, IndexError):
                print(f"CRITICAL ERROR: Non-numeric track data at index {i}")
                return 0, 0.0

        return int(total_populated), float(max_end_time)





class TKSpeakerDataFromTrack:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "trackIndex": ("INT", {"default": 1, "min": 1, "max": 100}),
                "speakerNum": ("INT", {"forceInput": True}),
                "image1": ("IMAGE",),
                "prompt1": ("STRING", {"multiline": True, "default": ""}),
                "image2": ("IMAGE",),
                "prompt2": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("selectedImage", "selectedText", "currentIndex")
    FUNCTION = "select_data"
    CATEGORY = "TKNodes"

    def select_data(self, trackIndex, speakerNum, image1, prompt1, image2, prompt2):
        # 1. Logic to pick based on the speakerNum provided by your extractor
        if speakerNum == 1:
            img, txt = image1, prompt1
        elif speakerNum == 2:
            img, txt = image2, prompt2
        else:
            # Fallback for index 0 or unknown
            img, txt = image1, prompt1 

        return (img, txt, trackIndex)
        




class TKTotalTracksInAudio:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "combinedTrackInfo1": ("STRING", {"forceInput": True}),
                "combinedTrackInfo2": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("totalTracks",)
    FUNCTION = "calculate_total"
    CATEGORY = "TKNodes"

    def calculate_total(self, combinedTrackInfo1, combinedTrackInfo2):
        # We use a temporary instance of your extractor to reuse the logic
        from .tknodes import TKSpeakerAudioTrackExtractor 
        extractor = TKSpeakerAudioTrackExtractor()
        
        # 1. Merge the strings using your existing logic
        merged = extractor.mergeAndSortTracks(combinedTrackInfo1, combinedTrackInfo2)
        
        # 2. Get the total count
        total, last_end_time = extractor.getTotalTracks(merged)
        
        return (int(total),)



class TKAudioSpeakerTalkTime:
    @classmethod
    def INPUT_TYPES(s):
        inputs = {
            "required": {
                "track_start_1": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_end_1": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
              
            },
            "optional": {
                "track_start_2": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_end_2": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_start_3": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_end_3": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),                
                "track_start_4": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_end_4": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),                
                "track_start_5": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),
                "track_end_5": ("FLOAT", {"default": 0.00, "min": 0.00, "max": 500.0, }),                

            }
        }
        return inputs

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("trackTimesCombined",)
    FUNCTION = "speakerTalkTimes"
    CATEGORY = "TKNodes"

    def speakerTalkTimes(self, track_start_1, track_end_1, track_start_2 , track_end_2 ,
                                track_start_3, track_end_3,track_start_4 , track_end_4,
                                track_start_5, track_end_5,  ):

        
        # Group inputs into pairs
        tracks = [
            (track_start_1, track_end_1),
            (track_start_2, track_end_2),
            (track_start_3, track_end_3),
            (track_start_4, track_end_4),
            (track_start_5, track_end_5)
        ]

        # Flatten the pairs and convert to strings, ignoring pairs that are both 0.0
        values = []
        for start, end in tracks:
            if start != 0.0 or end != 0.0:
                values.extend([str(start), str(end)])

        # Concatenate with commas
        combined_string = ",".join(values)
        
        return (combined_string,)


   

def getTrack(index, combined_string_of_tracks):
    # Fix: If ComfyUI sends this as a tuple, grab the first item (the string)
    if isinstance(combined_string_of_tracks, tuple):
        combined_string_of_tracks = combined_string_of_tracks[0]
    
    # Check for None or empty strings to prevent crashes
    if not combined_string_of_tracks or not isinstance(combined_string_of_tracks, str):
        return 0.0, 0.0, ""

    # Split the string back into a list of individual values
    parts = [p.strip() for p in combined_string_of_tracks.split(",") if p.strip()]
    
    # Calculate the starting position (1-based index)
    # Changed multiplier to 3 because each track is now [start, end, speaker]
    start_pos = (index - 1) * 3
    
    try:
        # Pull the start, end, and speaker values
        starttime = float(parts[start_pos])
        endtime = float(parts[start_pos + 1])
        speaker = parts[start_pos + 2]
        return starttime, endtime, speaker
    except (IndexError, ValueError) as e:
        # Log the error and the problematic index
        print(f"Error retrieving track at index {index}: {e}")
        # Return 0.0 and empty string if the index doesn't exist
        return 0.0, 0.0, ""





##################################################################################################





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



##
## Takes a list of audio files and join them to create on stream
## Useful when concat a bunch of videos together with VHS Combile
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
                "total_frames": ("INT", {"default": 97,   "min": 10, "max": 1000, "description" : "This value applies when length_selector = Use Frames"}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000, "description" : "This value applies when length_selector = Use Seconds"}),
                "fps":         ("FLOAT", {"default": 24.0, "min": 16.0, "max": 60.0, "description" : "FPS from video info node"}),
                

            },
        }

    RETURN_TYPES = ("INT",              "INT",         "INT",    "FLOAT", "FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames","fps", "totalSeconds")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Common Video User Inputs-  Use the Length_Selector to determine if you want to select by frames or seconds"

    def main(self, width, height, total_frames, length_selector, fps, num_seconds, ):
     
        returnSecs = num_seconds
        if (length_selector=="Use # Seconds") :
            total_frames = int(fps * num_seconds)
        else :
            returnSecs =   float(total_frames) / fps;
        

        return (width, height, total_frames, fps, returnSecs )





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
        

   
