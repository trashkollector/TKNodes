import numpy as np
import torch
import torch.nn.functional as F
import torchaudio
import json
from pydub import AudioSegment
from pydub.silence import detect_silence
import os
import sherpa_onnx
import urllib.request
import tarfile
import folder_paths




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
                                      index, padAudioForLtx , addBreathNoise=False):
        # 1. Get the startTime and EndTime by calling the helper function
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

            if addBreathNoise:
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
            else : # we are not using breather noise, we are going to use 1 second of silence instead
                # Create 1 second of zeros: [batch, channels, sample_rate]
                batch_size = waveform.shape[0]
                target_channels = waveform.shape[1]
                num_samples = sample_rate # 1 second = sample_rate
                
                leading_pad = torch.zeros(
                    (batch_size, target_channels, num_samples), 
                    device=waveform.device, 
                    dtype=waveform.dtype
                )

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
        if (last_time_stamp > max_duration):
            if (last_time_stamp - max_duration > 0.1):
               raise ValueError(f" ERROR: Your timings exceeds the Audio Length - Fix your inputs - size {last_time_stamp} > {max_duration} seconds")

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





class TKAudioDiarizationControl:
    @classmethod
    def INPUT_TYPES(s):
        # 1. Start with the core required fields
        inputs = {
            "required": {
                "fullaudio": ("AUDIO",),
                "duration": ("FLOAT", {"default": 0.0, "min": 0.0}),
                "track_start_1": ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True}),
                "track_end_1": ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True}),
            },
            "optional": {
                "transition_times": ("STRING", {"default": "[]", "hidden":True}),
            }
        }
        
        # 2. Dynamically add tracks 2 through 10 to "optional"
        for i in range(2, 11):
            inputs["optional"][f"track_start_{i}"] = ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True})
            inputs["optional"][f"track_end_{i}"] = ("FLOAT", {"default": 0.0,  "max": 500.0, "hidden":True})
            
        return inputs

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("sherpa_diarization", "speakersTrackInfo1", "speakersTrackInfo2")
    FUNCTION = "getSplitTimesByUser"
    CATEGORY = "TKNodes"

    ## Gets the split times defined by User using the Custom Slider Node
    ## Allow up to 20 splits.  The user can add/delete splits as needed to define tracks
    # 3. Use **kwargs to catch all those dynamic track variables
    def getSplitTimesByUser(self, fullaudio, duration, transition_times="[]", **kwargs):
        # Example of how to access the data inside the function:
       
        tracks = []
        for i in range(1, 11):
            start = kwargs.get(f"track_start_{i}", 0.0)
            end = kwargs.get(f"track_end_{i}", 0.0)
            if start > 0 or end > 0: # Only process active tracks
                tracks.append((start, end))
        
    
        waveform = fullaudio["waveform"]
        sample_rate = fullaudio["sample_rate"]
        computed_duration = waveform.shape[-1] / sample_rate

        # mereged means take consecutive speakers of the same
        (diarization,merged_diarization) = self.get_diarization_speakers(fullaudio)

        
        transition_times = self.getTransitionTimes(fullaudio, merged_diarization)
        
        # Fix: Handle the case where split_times is already a list (from the UI)
        if isinstance(transition_times, list):
            trackSplits = [float(t) for t in transition_times if 0 < float(t) < computed_duration]
        else:
            try:
                trackSplits = json.loads(transition_times)
                trackSplits = [float(t) for t in trackSplits if 0 < float(t) < computed_duration]
            except (json.JSONDecodeError, TypeError, ValueError):
                trackSplits = []
        
        # Critical: Sort the list so the interval string is in order
        trackSplits.sort()

        # PASS 'splits' (the list) here, not the JSON string
        trackInfo = self.convert_splits_to_intervals(trackSplits, computed_duration)
        (track1,track2) = self.split_intervals(trackInfo)

        transition_times_sec = [round(t, 3) for t in transition_times]

        return {
            "ui": {
                "duration": [computed_duration],
                "transition_times": transition_times_sec,   # ← this line must be here
                "tracks": tracks,  # <--- Add this!
            },
            "result": (json.dumps(diarization), track1, track2)
        }



    def getTransitionTimes(self, fullaudio, diarization):

      

        if isinstance(diarization, list):
            print("length:", len(diarization))
            for i, seg in enumerate(diarization):
                print(f"  [{i}] {seg}")
        else:
            print("Diarization is NOT a list:", diarization)


        # guarantee it's always a list
        diarization = diarization or []
        # diarization is a list of dicts: {start, end, speaker}
        # ensure it's sorted
        diarization = sorted(diarization, key=lambda x: x["start"])

        print("\n================ DIARIZATION ================")
        print(f"Raw diarization type: {type(diarization)}")

        if diarization is None:
            print("Diarization is NONE — your function returned nothing!")
        else:
            print(f"Diarization length: {len(diarization)}")
            print("Diarization entries:")
            for idx, seg in enumerate(diarization):
                print(f"  [{idx}] start={seg.get('start')}  end={seg.get('end')}  speaker={seg.get('speaker')}")

        print("===================================================\n")

        transition_times = []

        for i in range(len(diarization) - 1):
            end_prev = diarization[i]["end"]
            start_next = diarization[i + 1]["start"]
            midpoint = (end_prev + start_next) / 2.0
            transition_times.append(midpoint)

        return transition_times


    ## takes a JSON list and converts into tracks used by speakers.
    def convert_splits_to_intervals(self, split_times_input, total_duration):

        try:
            # Check if we even need to load JSON
            if isinstance(split_times_input, list):
                print("[DEBUG] Input is already a list. Skipping json.loads.")
                raw_splits = split_times_input
            else:
                print("[DEBUG] Input is a string. Attempting json.loads.")
                import json
                raw_splits = json.loads(split_times_input)
                
            # Clean and Sort
            splits = sorted([float(t) for t in raw_splits if 0 < float(t) < total_duration])
            print(f"[DEBUG]  Processed & Sorted splits: {splits}")
            
        except Exception as e:
            print(f"[DEBUG] Error during parsing: {e}")
            splits = []

        result = []
        current_start = 0.0

        for split in splits:
            # Format the segment start
            result.append(f"{current_start:.3f}")
            
            # Create the 'end' by subtracting 0.01 from the split
            # Rounding to 3 decimals keeps the precision you see in the debug
            seg_end = round(split - 0.01, 3) 
            if (seg_end > total_duration):
                seg_end=total_duration-0.1
                
            result.append(f"{seg_end:.3f}")
            
            # Update start for the next segment
            current_start = split

        # Final segment: last split to total duration
        result.append(f"{current_start:.3f}")
        result.append(f"{total_duration:.3f}")
        
        final_string = ",".join(result)
        print(f"[DEBUG] Final String: {final_string}\n")
        
        return final_string
    

    ## takes a list of tracks and separates it so it can be used by two alternating speakers.
    def split_intervals(self, input_str):
        # 1. Clean the string and turn it into a list of items
        # .strip() removes any extra spaces around the numbers
        items = [x.strip() for x in input_str.split(",") if x.strip()]
        
        # 2. Separate into two lists by checking the "pair index"
        # (i // 2) gives us 0 for the first pair, 1 for the second, etc.
        str1_items = [items[i] for i in range(len(items)) if (i // 2) % 2 == 0]
        str2_items = [items[i] for i in range(len(items)) if (i // 2) % 2 == 1]
        
        # 3. Join them back into comma-delimited strings
        return ",".join(str1_items), ",".join(str2_items)


    def download_speaker_models(self):
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

  
    def get_diarization_speakers(self, audio_data):
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
            self.download_speaker_models()

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
        merged_segments = []

        for r in segments_list:
            # 1. Maintain the original segments list as requested
            segments.append({
                "start": r.start,
                "end": r.end,
                "speaker": r.speaker
            })

            # 2. Build the merged_segments list by combining consecutive same-speaker entries
            if not merged_segments or r.speaker != merged_segments[-1]["speaker"]:
                # New speaker detected: start a new entry
                merged_segments.append({
                    "start": r.start,
                    "end": r.end,
                    "speaker": r.speaker
                })
            else:
                # Same speaker continues: update the end time of the last entry
                merged_segments[-1]["end"] = r.end

        return segments, merged_segments







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


