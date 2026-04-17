import torch
import torch.nn.functional as F
import torchaudio


class TKSpeakerAudioTrackExtractor:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "fullaudio": ("AUDIO",),
                "combinedTrackInfo1": ("STRING", {"forceInput": True , "tooltip": "Speaker 1 track info."}),
                "combinedTrackInfo2": ("STRING", {"forceInput": True,  "tooltip": "Speaker 2 track info."}),
                "padAudioForLtx" : ("BOOLEAN", {"default": True, "tooltip": "pad audio track with silence..helps lip sync."}),
                "index": ("INT", {"default": 1, "min": 1, "max": 10, "tooltip": "the track number from ALL tracks"}),
            },
            "optional" :{
                "addBreathNoise" : ("BOOLEAN", {"default": False, "tooltip": "This will add human breath to start of audio, turn this ON increases chances of lip sync working."}),
            }
        }

    RETURN_TYPES = ("AUDIO",        "INT"  ,        "INT"      ,"INT")
    RETURN_NAMES = ("audioTrack","totalTracks", "numFrames" , "speakerNum")
    FUNCTION = "extractSpeakerTrackAudio"
    CATEGORY = "TKNodes"
    DESCRIPTION ="This node extracts all the track info enterd by the user  and then sorts them and combines them so it can subsequentally loop thru them in the workflow"

    def extractSpeakerTrackAudio(self, fullaudio, combinedTrackInfo1, combinedTrackInfo2, 
                                      index, padAudioForLtx):
        # 1. Get the startTime and EndTime by calling the helper function
        combinedTrackInfo = self.mergeAndSortTracks(combinedTrackInfo1, combinedTrackInfo2)
        start_time, end_time, speaker = getTrack(index, combinedTrackInfo)

        print(f"INDEX {index}: start={start_time}, end={end_time}, duration={end_time-start_time:.2f}s")

        if (speaker == "speaker1"):
            speakerNum = 1
        elif (speaker == "speaker2"):
            speakerNum = 2
        else:
            speakerNum = 0

        # Extract the waveform and sample rate
        waveform = fullaudio["waveform"]  # shape: [batch, channels, samples]
        sample_rate = fullaudio["sample_rate"]

        # Calculate sample indices
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)

        # Bounds checking to prevent index errors
        max_samples = waveform.shape[-1]
        max_duration = max_samples / sample_rate

        # Validate before slicing
        if start_time >= max_duration:
            raise ValueError(f"INDEX {index}: ERROR start_time {start_time:.2f}s exceeds audio length {max_duration:.2f}s")
        if end_time > max_duration:
            raise ValueError(f"INDEX {index}: ERROR end_time {end_time:.2f}s exceeds audio length {max_duration:.2f}s — ERROR - Make sure you entered correct Speaker Times!")

        start_idx = max(0, min(start_sample, max_samples))
        end_idx = max(0, min(end_sample, max_samples))

        print(f"sample_rate={sample_rate}")
        print(f"waveform.shape={waveform.shape}")
        print(f"max_samples={max_samples}")
        print(f"start_sample={start_sample}, end_sample={end_sample}")
        print(f"start_idx={start_idx}, end_idx={end_idx}")

        # Helper: load the pad audio asset, resample if needed, and trim/tile to exact sample count
        def load_pad_audio(target_samples, device, dtype):
            import torchaudio
            import os

            asset_path = os.path.join(os.path.dirname(__file__), "assets", "breather.wav")
            pad_waveform, pad_sr = torchaudio.load(asset_path, backend="soundfile")

            if pad_sr != sample_rate:
                resampler = torchaudio.transforms.Resample(orig_freq=pad_sr, new_freq=sample_rate)
                pad_waveform = resampler(pad_waveform)

            # Match channel count
            target_channels = waveform.shape[1]
            if pad_waveform.shape[0] < target_channels:
                pad_waveform = pad_waveform.expand(target_channels, -1)
            elif pad_waveform.shape[0] > target_channels:
                pad_waveform = pad_waveform[:target_channels, :]

            # Trim to exact target (handles any minor resampling rounding)
            pad_waveform = pad_waveform[:, :target_samples]

            return pad_waveform.unsqueeze(0).to(device=device, dtype=dtype)

        # pad with leading and trailing asset audio
        if (padAudioForLtx):
            import torchaudio
            import os

            # Load breather once to get its exact sample count
            asset_path = os.path.join(os.path.dirname(__file__), "assets", "breather.wav")
            _breather, _breather_sr = torchaudio.load(asset_path, backend="soundfile")
            if _breather_sr != sample_rate:
                _breather = torchaudio.transforms.Resample(orig_freq=_breather_sr, new_freq=sample_rate)(_breather)

            # Match channel count
            target_channels = waveform.shape[1]
            if _breather.shape[0] < target_channels:
                _breather = _breather.expand(target_channels, -1)
            elif _breather.shape[0] > target_channels:
                _breather = _breather[:target_channels, :]

            # Add batch dim [batch, channels, samples]
            leading_pad = _breather.unsqueeze(0).to(device=waveform.device, dtype=waveform.dtype)

            # Get speech waveform
            new_waveform = waveform[:, :, start_idx:end_idx]

            # Prepend breath only
            final_waveform = torch.cat([leading_pad, new_waveform], dim=-1)

        else:
            final_waveform = waveform[:, :, start_idx:end_idx]
            new_waveform = final_waveform



        print(
            f"INDEX {index}: start={start_time}, end={end_time}, "
            f"duration={end_time-start_time:.2f}s | "
            f"new_waveform={new_waveform.shape[-1]} samples | "
            f"final_waveform={final_waveform.shape[-1]} samples")

        totalTracks, last_time_stamp = self.getTotalTracks(combinedTrackInfo)
        if (last_time_stamp >= max_duration):
            raise ValueError(f" ERROR: Your timings exceeds the Audio Length - Fix your inputs - size {max_duration:.2f} seconds")

        nFrames = int(round((end_time - start_time) * 25) + 25)

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
    DESCRIPTION ="Given the Speaker,, select the appropriate PROMPT and START IMAGE. since they alternate we need this"

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
                "combinedTrackInfo1": ("STRING", {"forceInput": True, "tooltip":"Speaker 1 defined track times"}),
                "combinedTrackInfo2": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("totalTracks",)
    FUNCTION = "calculate_total"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Get the total talks tracks between the 2 Speakers"

    def calculate_total(self, combinedTrackInfo1, combinedTrackInfo2):
        # We use a temporary instance of your extractor to reuse the logic
        from .speakers import TKSpeakerAudioTrackExtractor 
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


