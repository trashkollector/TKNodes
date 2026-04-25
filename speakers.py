from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
import torchaudio
import json
from pydub import AudioSegment
from pydub.silence import detect_silence
from pydub.silence import detect_nonsilent
import os
import sherpa_onnx
import urllib.request
import tarfile
import folder_paths
from server import PromptServer
from aiohttp import web


# HTTP Endpoint for scanning the audio file finding speakers and presenting in custom node
# calls PyDub for silence breaks
@PromptServer.instance.routes.post("/tk/detect_speakers")
async def detect_speakers_endpoint(request):
    try:
      
        json_data = await request.json()

        audio_name = json_data.get("audio")
        threshold = json_data.get("silence_threshold", 1.0) 
        print(f"silence thres {threshold}")
        # Convert seconds to milliseconds
        threshold_ms = int(threshold * 1000) 
        
        input_dir = folder_paths.get_input_directory()
        audio_path = os.path.join(input_dir, audio_name)

        speakerClass = TKLocateSpeakersUsingSilenceBreaks()

        segments, duration = speakerClass.get_diarization_speakers_from_audio_file(audio_path, threshold_ms)
    
        speakerClass.save_segments_for_later_use(segments)  # store for later

        return web.json_response({"speaker_times": segments, 
                                  "duration":  duration, "silence_threshold":threshold_ms})
        
    except Exception as e:
        print(f"[TKDetectSpeakers] Detection failed: {e}")
        return web.json_response({"error": str(e)}, status=500)





class TKTrimAudioWithBooleans:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "fullaudio": ("AUDIO",),

            },
            "optional": {
                "shouldTrimStart": ("BOOLEAN", {"default": False}),
                "trimStartMs": ("INT", {"default": 0, "min": 0, "max": 1000, "step": 100}),
                "shouldTrimEnd": ("BOOLEAN", {"default": False}),
                "trimEndMs": ("INT", {"default": 0, "min": 0, "max": 1000, "step": 100}),
            }
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("trimmedAudio",)
    FUNCTION = "trimAudio"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Trim audio with Booleans"

    def trimAudio(self, fullaudio, shouldTrimStart, trimStartMs, shouldTrimEnd, trimEndMs):
        waveform = fullaudio["waveform"]  # shape: [batch, channels, samples]
        sample_rate = fullaudio["sample_rate"]

        total_samples = waveform.shape[-1]

        # Convert ms to sample counts
        start_trim_samples = int((trimStartMs / 1000.0) * sample_rate) if shouldTrimStart else 0
        end_trim_samples   = int((trimEndMs   / 1000.0) * sample_rate) if shouldTrimEnd   else 0

        # Clamp so we never trim more than the total audio length
        start_trim_samples = min(start_trim_samples, total_samples)
        end_trim_samples   = min(end_trim_samples,   total_samples - start_trim_samples)

        # Calculate slice indices
        start_idx = start_trim_samples
        end_idx   = total_samples - end_trim_samples

        # Guard: if nothing would remain, return silence of 1 sample
        if end_idx <= start_idx:
            trimmed = torch.zeros(
                (waveform.shape[0], waveform.shape[1], 1),
                device=waveform.device,
                dtype=waveform.dtype
            )
        else:
            trimmed = waveform[:, :, start_idx:end_idx]

        return ({"waveform": trimmed, "sample_rate": sample_rate},)






# This node extracts all the track info enterd by the user  and then sorts them and combines 
# them so it can subsequentally loop thru them in the workflow"
# Extract nth Audio Track Node
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

    RETURN_TYPES = ("AUDIO",        "INT"  ,        "INT"      ,"INT"       ,      "INT" ,         "INT")
    RETURN_NAMES = ("audioTrack","totalTracks", "numFrames" , "speakerNum"   , "front_pad_ms", "end_pad_ms")
    FUNCTION = "extractSpeakerTrackAudio"
    CATEGORY = "TKNodes"
    DESCRIPTION ="This node extracts all the track info enterd by the user  and then sorts them and combines them so it can subsequentally loop thru them in the workflow"

    def extractSpeakerTrackAudio(self, fullaudio, combinedTrackInfo1, combinedTrackInfo2, 
                                      index, padAudioForLtx , addBreathNoise=False):
        # 1. Get the startTime and EndTime by calling the helper function

        print(f"track info combined={combinedTrackInfo1} {combinedTrackInfo2}")
        combinedTrackInfo = self.mergeAndSortTracks(combinedTrackInfo1, combinedTrackInfo2)
        start_time, end_time, speaker = TKAudioSpeakerTalkTime.getTrack(index, combinedTrackInfo)

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
        if start_time > max_duration+0.1:
            raise ValueError(f"INDEX {index}: ERROR start_time {start_time:.2f}s exceeds audio length {max_duration:.2f}s")
        if end_time > max_duration+0.1:
            raise ValueError(f"INDEX {index}: ERROR end_time {end_time:.2f}s exceeds audio length {max_duration:.2f}s — ERROR - Make sure you entered correct Speaker Times!")

        start_idx = max(0, min(start_sample, max_samples))
        end_idx = max(0, min(end_sample, max_samples))

        print(f"sample_rate={sample_rate}")
        print(f"waveform.shape={waveform.shape}")
        print(f"max_samples={max_samples}")
        print(f"start_sample={start_sample}, end_sample={end_sample}")
        print(f"start_idx={start_idx}, end_idx={end_idx}")

        # Helper: load the pad audio asset, resample if needed, and trim/tile to exact sample count
        def load_breather_pad_file(target_samples, device, dtype):
  
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

        # pad audio withe silence and/or breath
        
        front_pad_ms=0
        end_pad_ms=0

        extraFrames=0
        if (padAudioForLtx):

            # Get speech waveform first (used in both branches)
            new_waveform = waveform[:, :, start_idx:end_idx]

            batch_size = waveform.shape[0]
            target_channels = waveform.shape[1]

            # Create 500ms of silence: [batch, channels, sample_rate // 2]
            half_second_samples = sample_rate // 2
            silence_500ms = torch.zeros(
                (batch_size, target_channels, half_second_samples),
                device=waveform.device,
                dtype=waveform.dtype
            )

            if addBreathNoise:
                extra_frames = 25 + 13
                front_pad_ms=1000  # specify ammount to be deleted later.

                #  breather +500ms silence + original audio + 500ms silence
                breather_pad = load_breather_pad_file(sample_rate, waveform.device, waveform.dtype)
                final_waveform = torch.cat([breather_pad, new_waveform, silence_500ms], dim=-1)

            else:
                extra_frames =13
                front_pad_ms=0

                # No breather noise -         original audio + 500ms silence
                final_waveform = torch.cat([new_waveform, silence_500ms], dim=-1)


        else:  # USER SELECTED 0 PADDING!

            final_waveform = waveform[:, :, start_idx:end_idx]
            new_waveform = final_waveform
                

        print(
            f"Get Track - INDEX {index}: start={start_time}, end={end_time}, "
            f"duration={end_time-start_time:.2f}s | "
            f"new_waveform={new_waveform.shape[-1]} samples | "
            f"final_waveform={final_waveform.shape[-1]} samples")

        totalTracks, last_time_stamp = self.getTotalTracks(combinedTrackInfo)
        if (last_time_stamp > max_duration):
            if (last_time_stamp - max_duration > 0.1):
               raise ValueError(f" ERROR: Your timings exceeds the Audio Length - Fix your inputs - size {last_time_stamp} > {max_duration} seconds")


        nFrames = int(round((end_time - start_time) * 25) + extra_frames)

        # Force all numeric outputs to pure integers
        return (
            {"waveform": final_waveform, "sample_rate": sample_rate},
            int(totalTracks),
            int(nFrames),
            int(speakerNum),
            int(front_pad_ms),
            int(end_pad_ms),
        
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
                    print(f"*****  CRITICAL ERROR: Check to make sure your timings that you entered are correct.  Invalid timestamps found (Start: {start}, End: {end})")
                    return 0, 0.0

                # 3. Track valid data
                total_populated += 1
                if end >= max_end_time:
                    max_end_time = end
                
            except (ValueError, IndexError):
                print(f"CRITICAL ERROR: Non-numeric track data at index {i}")
                return 0, 0.0

        return int(total_populated), float(max_end_time)




# Given the Speaker, select the appropriate PROMPT and START IMAGE. since they alternate we need this
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
    DESCRIPTION ="Given the Speaker, select the appropriate PROMPT and START IMAGE. since they alternate we need this"

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
        



# Get the total talks tracks between the 2 Speakers"
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



# This node locates speakers in an Audio file base on silence breaks.  Priarily this is use with AI generated audo.  
# Make sure you put breaks in audioi file for this to work. 
#  Use the threshold to determine how much silence to insert
   

class TKLocateSpeakersUsingSilenceBreaks:
    @classmethod
    def INPUT_TYPES(s):
        # 1. Start with the core required fields
        inputs = {
            "required": {
                "silence_threshold" : ("FLOAT", {"default": 1.0, "min": 0.2, "max": 4.0 , "step": 0.01}),
                "fullaudio": ("AUDIO",),
                "duration": ("FLOAT", {"default": 0.0, "min": 0.0}),
                "track_start_1": ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True}),
                "track_end_1": ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True}),
            },
            "optional": {
                "speaker_times": ("STRING", {"default": "[]", "hidden":True}),
                  # This is never visible in the UI but passed to execute()
                "track_state": ("STRING", {"default": "DataUnchanged", "hidden":True}),
            },

        }
        
        # 2. Dynamically add tracks 2 through 14 to "optional"
        for i in range(2, 15):
            inputs["optional"][f"track_start_{i}"] = ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True})
            inputs["optional"][f"track_end_{i}"] = ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True})
            
        return inputs

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("diarization", "speakersTrackInfo1", "speakersTrackInfo2")
    FUNCTION = "calculatTracksBySilence"
    CATEGORY = "TKNodes"
    DESCRIPTION = "This node locates speakers in an Audio file base on silence breaks.  Priarily this is use with AI generated audo.  Make sure you put breaks in audioi file for this to work.  Use the threshold to determine how much silence to insert"
   
    autoSegmentsFromAudio=[]

   # Emulate diarization by using silence as breaks for speakers.
    def calculatTracksBySilence(self, silence_threshold, fullaudio, duration, speaker_times="[]",
                                track_state="DataUnchanged", **kwargs):
        # Example of how to access the data inside the function:
     
        waveform = fullaudio["waveform"]
        sample_rate = fullaudio["sample_rate"]
        computed_duration = waveform.shape[-1] / sample_rate

        manualDiarization = self.convertEditBoxesToDiarization(**kwargs)
  
       
        # USER ENTERED DATA TO OVERRIDE AUTO
        if track_state == "DataChange": 
            # MANUAL DIARIZATION

            speaker_times = manualDiarization
            (speaker1tracks, speaker2tracks) = self.extact_2_speakers_from_diarization(manualDiarization)

        # AUTO DIARIZATION
        else :
            diarization       = self.autoSegmentsFromAudio

            speaker_times = diarization
            (speaker1tracks, speaker2tracks) = self.extact_2_speakers_from_diarization(diarization)
                    
        sp1 = self.convert_segments_to_track_string(speaker1tracks)
        sp2 = self.convert_segments_to_track_string(speaker2tracks)



        return {
            "ui": {
                "duration": [computed_duration],
                "speaker_times": speaker_times , 
            },
            "result": (json.dumps(speaker_times) , sp1 , sp2)
        }


    # build out diarization list using edit boxes entered by user
    def convertEditBoxesToDiarization(self, **kwargs):
        segments = []
        
        for i in range(1, 15):
            start = kwargs.get(f"track_start_{i}", 0.0)
            end = kwargs.get(f"track_end_{i}", 0.0)
            
            if end > start:
                # We use a dictionary here so seg["speaker"] works later
                speaker = 0 if i <= 7 else 1
                segments.append({
                    "start": start,
                    "end": end,
                    "speaker": speaker # This is an integer
                })
        
        # Sort the dictionaries by the 'start' time
        segments.sort(key=lambda x: x["start"])
        
        return segments




    @classmethod  # <--- Add this decorator
    def save_segments_for_later_use(cls, segments):

        cls.autoSegmentsFromAudio = segments.copy() 




    def convert_segments_to_track_string(self, segments):
        """
        Converts a list of segment dictionaries into a flat string.
        Input: [{"start": 0.0, "end": 3.9, "speaker": 0}, ...]
        Output: "0.000,3.942,5.193,9.510"
        """
        if not segments:
            return ""
            
        parts = []
        for seg in segments:
            # Access by key name since 'segments' is a list of dicts
            start = seg.get("start", 0.0)
            end = seg.get("end", 0.0)
            
            parts.append(f"{float(start):.3f}")
            parts.append(f"{float(end):.3f}")
            
        return ",".join(parts)

    


    def build_speaker_tracks(self, **kwargs):
        """
        Reads track_start_1..10 and track_end_1..10 from kwargs.
        Tracks 1-5  → Speaker1Tracks
        Tracks 6-10 → Speaker2Tracks

        Returns:
            tuple: (Speaker1Tracks, Speaker2Tracks) as comma-delimited strings
        """
        speaker1_parts = []
        speaker2_parts = []

        for i in range(1, 11):
            start = kwargs.get(f"track_start_{i}", 0.0)
            end   = kwargs.get(f"track_end_{i}",   0.0)

            # Skip empty/default tracks
            if start == 0.0 and end == 0.0:
                continue

            entry = f"{start:.3f},{end:.3f}"

            if i <= 5:
                speaker1_parts.append(entry)
            else:
                speaker2_parts.append(entry)

        Speaker1Tracks = ", ".join(speaker1_parts)
        Speaker2Tracks = ", ".join(speaker2_parts)

        return Speaker1Tracks, Speaker2Tracks
    


    def getTransitionMidPoints(self, fullaudio, diarization):

        # guarantee it's always a list
        diarization = diarization or []
        # diarization is a list of dicts: {start, end, speaker}
        # ensure it's sorted
        diarization = sorted(diarization, key=lambda x: x["start"])

        transition_times = []

        for i in range(len(diarization) - 1):
            end_prev = diarization[i]["end"]
            start_next = diarization[i + 1]["start"]
            midpoint = (end_prev + start_next) / 2.0
            transition_times.append(midpoint)

        return transition_times


    

    ## takes a list of tracks and separates it so it can be used by two alternating speakers.
    def seperate_tracks_for_speakers(self, input_str):
        # 1. Clean the string and turn it into a list of items
        # .strip() removes any extra spaces around the numbers
        items = [x.strip() for x in input_str.split(",") if x.strip()]
        
        # 2. Separate into two lists by checking the "pair index"
        # (i // 2) gives us 0 for the first pair, 1 for the second, etc.
        str1_items = [items[i] for i in range(len(items)) if (i // 2) % 2 == 0]
        str2_items = [items[i] for i in range(len(items)) if (i // 2) % 2 == 1]
        
        # 3. Join them back into comma-delimited strings
        return ",".join(str1_items), ",".join(str2_items)


    def download_sherpa_speaker_models(self):
        dest_dir = os.path.join(folder_paths.models_dir, "onnx")
        os.makedirs(dest_dir, exist_ok=True)

        # Define EXACT names your loader expects
        seg_target = "sherpa-onnx-pyannote-segmentation-3-0.onnx"
        #emb_target = "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
        emb_target = "nemo_en_titanet_large.onnx"

        # 1. Handle Segmentation (The tarball)
        seg_path = os.path.join(dest_dir, seg_target)
        if not os.path.exists(seg_path):
            url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
            temp_tar = os.path.join(dest_dir, "temp_seg.tar.bz2")
            print(f"[TKNodes] Downloading segmentation model...")
            urllib.request.urlretrieve(url, temp_tar)
            
            with tarfile.open(temp_tar, "r:bz2") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".onnx"):
                        # FORCE the name to match your loader
                        member.name = seg_target 
                        tar.extract(member, path=dest_dir)
                        break
            os.remove(temp_tar)

        # 2. Handle Embedding (Direct download)
        emb_path = os.path.join(dest_dir, emb_target)
        if not os.path.exists(emb_path):

            print(f"[TKNodes] Downloading embedding model...")
            url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/nemo_en_titanet_large.onnx"
            urllib.request.urlretrieve(url, emb_path)

        print(f"[TKNodes] ONNX Models verified in: {dest_dir}")

  
    def get_diarization_speakers_old(self, audio_data):
        print(f"[DEBUG]  Inside get_speaker_splits_from_audio_with_sherpa ")
        waveform = audio_data['waveform']
        sample_rate = audio_data['sample_rate']
        
        # 1. Convert torch tensor to mono
        if waveform.dim() > 1:
            waveform = waveform.mean(dim=0)
        
        # 2. Resample to 16kHz (Sherpa-ONNX requirement)
        if sample_rate != 16000:
            import torch.nn.functional as F
            num_samples = int(waveform.shape[-1] * 16000 / sample_rate)
            waveform = F.interpolate(waveform.view(1, 1, -1), size=num_samples, mode='linear', align_corners=False).view(-1)
            sample_rate = 16000

        audio_np = waveform.detach().cpu().numpy().astype(np.float32)

        # 3. Flatten to 1D
        audio_np = audio_np.reshape(-1)

        # 4. Normalize if needed
        if np.max(np.abs(audio_np)) > 1.0:
            audio_np = audio_np / 32768.0

        # 5. Configure paths
        models_dir = folder_paths.models_dir
        onnx_path = os.path.join(models_dir, "onnx")
        
        segmentation_path = os.path.join(onnx_path, "sherpa-onnx-pyannote-segmentation-3-0.onnx")
        embedding_path = os.path.join(onnx_path, "nemo_en_titanet_large.onnx")

        if not os.path.exists(segmentation_path) or not os.path.exists(embedding_path):
            self.download_sherpa_speaker_models()

        print(f"[DEBUG]  Successfully found SHERPA models ")
        # Use the full prefix to avoid IDE "not found" errors
        # Use the consolidated 2026 class names to clear the IDE errors
        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=segmentation_path,
                ),
                
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=embedding_path,  # nemo_titanet_l
            ),
            clustering=sherpa_onnx.FastClusteringConfig(
                num_clusters=2,
                threshold=0.7,
            ),
        )


        sd = sherpa_onnx.OfflineSpeakerDiarization(config)
        print(f"[DEBUG]  Successfully found SHERPA models ")   

        # 6. Process the audio
        result = sd.process(audio_np)
 


        # sort into a list of segments
        segments_list = result.sort_by_start_time()

        # if diarization failed or returned nothing
        if not segments_list:
            print("DEBUG: No segments returned by Sherpa.")
            return []
        


        segments = []

        for r in segments_list:
            # 1. Maintain the original segments list as requested
            segments.append({
                "start": r.start,
                "end": r.end,
                "speaker": r.speaker
            })

        return segments


    # Emulate diarization by using silence to detect speakers
    # Need to follow rules and include silence so speakers switch
    def get_diarization_speakers_using_silence(self, filename, split_threshold_ms=800):
        # This now only uses one threshold to decide when to toggle speakers
  
        # Build the Audacity Label file and then check to see if user provided one
        base_name = os.path.basename(filename).rsplit('.', 1)[0] + ".txt"
        
        # 2. Define the two places to look
        path_in_input = os.path.join(os.path.dirname(filename), base_name)
        path_in_docs = os.path.join(str(Path.home()), "Documents", base_name)

        # 3. Search logic
        final_label_path = None
        if os.path.exists(path_in_input):
            final_label_path = path_in_input
        elif os.path.exists(path_in_docs):
            print(f"DEBUG: Found labels in Documents! {path_in_docs}")
            final_label_path = path_in_docs

        # 4. Use the labels if found
        if final_label_path:
            segments = self.get_diarization_from_labels(final_label_path)
            audio = AudioSegment.from_file(filename)
            return segments, len(audio) / 1000.0

        audio = AudioSegment.from_file(filename)
        duration_sec = len(audio) / 1000.0

         # FALLBACK: Your original silence logic starts here

        print(f"Pydub Processing audio file with split_threshold {split_threshold_ms}ms")
        print(f"Audacity label files also supported .   Check  workflow for more info")
        
        if audio.channels > 1:
            audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)


        # Detect non-silent chunks based on pydub's sensitivity
        chunks = detect_nonsilent(
            audio,
            min_silence_len=100,     
            silence_thresh=-40       
        )

        if not chunks:
            print("DEBUG: No segments found.")
            return [], duration_sec

        segments = []
        current_speaker = 0
        
        # Initialize first chunk
        current_start, current_end = chunks[0]

        for i in range(1, len(chunks)):
            next_start, next_end = chunks[i]
            gap = next_start - current_end 

            # ALWAYS end the segment when a gap is found
            segments.append({
                "start": float(current_start / 1000.0),
                "end":   float(current_end / 1000.0),
                "speaker": current_speaker
            })

            # Check if the gap was long enough to switch speakers
            if gap >= split_threshold_ms:
                current_speaker = 1 if current_speaker == 0 else 0
            
            # Start the next segment
            current_start = next_start
            current_end = next_end

        # Append the final chunk
        segments.append({
            "start": float(current_start / 1000.0),
            "end":   float(current_end / 1000.0),
            "speaker": current_speaker
        })

        return segments, duration_sec



    def get_diarization_from_labels(self, label_filename):

        print(f"Using labels file for track timings")
        segments = []
        current_speaker = 0  # Start with Speaker 0

        with open(label_filename, "r") as f:
            for i, line in enumerate(f):
                parts = line.strip().split("\t")
                if len(parts) < 2: continue
                
                start_sec = float(parts[0])
                end_sec = float(parts[1])
                label_text = parts[2] if len(parts) > 2 else ""

                # Check for manual override "1" or "2"
                if "1" in label_text:
                    speaker_id = 0
                elif "2" in label_text:
                    speaker_id = 1
                else:
                    # No manual number? Use the flip-flop logic
                    speaker_id = current_speaker

                print(f"DEBUG: Segment {i} | Speaker {speaker_id} | Start: {start_sec:.2f}s | End: {end_sec:.2f}s |Label: '{label_text}'")

                segments.append({
                    "start": start_sec,
                    "end": end_sec,
                    "speaker": speaker_id
                })

                # Always toggle based on the CURRENT segment so the NEXT one alternates
                current_speaker = 1 if speaker_id == 0 else 0
                
        return segments






    
    def merge_diarization_segments(self, segments, max_duration_sec=10.0):
        if not segments:
            return []

        merged = []
        # Start with the first segment as our "working" block
        current_group = segments[0].copy()

        for i in range(1, len(segments)):
            next_seg = segments[i]
            
            # Calculate what the duration would be if we merged them
            potential_duration = next_seg["end"] - current_group["start"]

            # Check: Same speaker AND stays under the time limit?
            if (next_seg["speaker"] == current_group["speaker"] and 
                potential_duration <= max_duration_sec):
                
                # Update the end time of the current working block
                current_group["end"] = next_seg["end"]
            else:
                # Either speaker changed or limit hit: Save current and start new group
                merged.append(current_group)
                current_group = next_seg.copy()

        # Don't forget to add the very last group
        merged.append(current_group)

        print(f"[DEBUG] Merged {len(segments)} raw segments into {len(merged)} grouped segments")
        return merged

    

    def load_audio_as_mono(self, filename: str) -> AudioSegment:
        """Load an audio file and convert it to mono for use with pydub."""
        audio = AudioSegment.from_file(filename)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        return audio
    
    def get_diarization_speakers_from_audio_file(self, audio_path, silence_thresh):

        (diar, duration) = self.get_diarization_speakers_using_silence(audio_path,  silence_thresh)

        # if same speaker speaks for short time, merge those segments together
        mergeDiar = self.merge_small_consecutive_segments(diar)

        # Derive duration from segments instead of waveform
  
        return  mergeDiar, duration 
    


    # take speaker diarization data and creater profile for 2 users only
    def extact_2_speakers_from_diarization(self, diarData):
        speaker1Segs = []
        speaker2Segs = []

        for seg in diarData:
            # If speaker is 0 (or anything other than 1), put in speaker1Segs
            if seg["speaker"] == 1:
                speaker2Segs.append(seg)
            else:
                # This handles speaker 0 and your fallback for any speaker > 1
                speaker1Segs.append(seg)
                
        return speaker1Segs, speaker2Segs
    



    def merge_small_consecutive_segments(self, segments, max_duration=10.0):
        """
        Merges consecutive segments from the same speaker if they are small (< max_duration).
        
        Rules:
        - Scan for consecutive segments with the same speaker
        - If a segment is < max_duration, try to merge it with the next segment
        (same speaker) as long as the combined duration stays < max_duration
        - Once a merge would exceed max_duration, start a new merged segment
        
        Args:
            segments: List of dicts with 'start', 'end', 'speaker' keys
            max_duration: Maximum duration in seconds for merging (default: 10.0)
        
        Returns:
            List of merged segment dicts
        """
        if not segments:
            return []

        merged = []
        current = dict(segments[0])  # copy so we don't mutate the original

        for next_seg in segments[1:]:
            same_speaker = next_seg['speaker'] == current['speaker']
            current_duration = current['end'] - current['start']
            combined_duration = next_seg['end'] - current['start']

            if same_speaker and current_duration < max_duration and combined_duration < max_duration:
                # Extend the current segment to absorb the next one
                current['end'] = next_seg['end']
            else:
                # Flush current and start fresh
                merged.append(current)
                current = dict(next_seg)

        merged.append(current)  # flush the last segment

        # print(f"[DEBUG] Merged pydub silence detection found {len(merged)} segments")
        # for i, s in enumerate(merged):
        #     print(f"  [{i}] start={s['start']:.3f}  end={s['end']:.3f}  speaker={s['speaker']}")

        return merged


    def process_segments_for_two_speakers(self, segments):
        """
        Process segments and return two strings containing time ranges for each speaker.
        
        Args:
            segments: list of dicts with 'start', 'end', 'speaker' keys
        
        Returns:
            tuple: (Speaker1Tracks, Speaker2Tracks) as strings
        """
        if not segments:
            return "", ""

        # --- Step 1: Discover the two dominant speakers ---
        speaker_counts = {}
        for seg in segments:
            spk = seg["speaker"]
            speaker_counts[spk] = speaker_counts.get(spk, 0) + 1

        # Sort speakers by frequency; top 2 become Speaker 1 and Speaker 2
        sorted_speakers = sorted(speaker_counts, key=lambda s: speaker_counts[s], reverse=True)
        speaker1_id = sorted_speakers[0]
        speaker2_id = sorted_speakers[1] if len(sorted_speakers) > 1 else None

        # --- Step 2: Assign extra speakers to the nearest Speaker 1 or Speaker 2 ---
        def resolve_speaker(seg_index):
            spk = segments[seg_index]["speaker"]
            if spk == speaker1_id:
                return 1
            if spk == speaker2_id:
                return 2

            # Extra speaker: search outward for the nearest Speaker 1 or 2
            left, right = seg_index - 1, seg_index + 1
            while left >= 0 or right < len(segments):
                if left >= 0:
                    neighbor = segments[left]["speaker"]
                    if neighbor == speaker1_id:
                        return 1
                    if neighbor == speaker2_id:
                        return 2
                    left -= 1
                if right < len(segments):
                    neighbor = segments[right]["speaker"]
                    if neighbor == speaker1_id:
                        return 1
                    if neighbor == speaker2_id:
                        return 2
                    right += 1

            return 1  # Fallback: assign to Speaker 1

        # --- Step 3: Build the two track strings ---
        speaker1_parts = []
        speaker2_parts = []

        for i, seg in enumerate(segments):
            start = seg["start"]
            end = seg["end"]
            assigned = resolve_speaker(i)
            entry = f"{start:.3f}-{end:.3f}"

            if assigned == 1:
                speaker1_parts.append(entry)
            else:
                speaker2_parts.append(entry)

        Speaker1Tracks = ", ".join(speaker1_parts)
        Speaker2Tracks = ", ".join(speaker2_parts)

        return Speaker1Tracks, Speaker2Tracks



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


   
    @staticmethod
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


