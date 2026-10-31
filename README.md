# See workflow folder for example workflows of various nodes




# TKLargeVideoChunker
Used to chunk very large files to avoid out of memory conditions.   Also chunks audio.  Must run within FOR LOOP/END

<img width="600" alt="Screenshot 2026-10-31 123957" src="https://github.com/user-attachments/assets/8af55403-179c-4dd3-b0d9-aaeeb53e6b47" />



# TKSmartVideoChunker
Silence-based video/audio chunking for LTX 2.3 / Wan 2.2.   Looks for silence in audio to create chunk breaks.   
This is helpful when speakers take a breath and we don't cut off speaker while talking. 
Chunking is required to get around VRAM issues.  For Low VRAM set chunk size lower"

 Silence-based video/audio chunking for LTX 2.3 or Wan 2.2. Slices at native fps, resamples to target_fps, and snaps to a valid frame count


<img width="432"  alt="Screenshot 2026-08-05 131620" src="https://github.com/user-attachments/assets/839ac1e9-1feb-44c0-9039-2de24a1dca77" />

# TKSmartAudioChunker
Silence based audio chunker.. used in workflow for Singing or Talking, so it never breaks middle sentence.
TKSmartVideoChunker will call this node for the audio breaks.


# TKMultiImagePrompt
Manager a group of images and prompts in a uniform way.   Used together with FOR LOOP START / END
<img width="611" height="694" alt="Screenshot 2026-10-31 124505" src="https://github.com/user-attachments/assets/e7d9ec07-4afe-4639-84bf-2520ce96666d" />


# TKPromptLooperAdv
Prompt Looper can handle unlimited number of images/prompts within a looping construct

<img width="600" alt="Screenshot 2026-10-31 125301" src="https://github.com/user-attachments/assets/37939d48-b5ea-4b2c-9cac-78c09620594e" />


# TKSceneDetection
Video Scene Detection

<img width="600" alt="Screenshot 2026-10-31 124133" src="https://github.com/user-attachments/assets/30234a7f-dc77-4a08-a083-e47fbbcf8204" />


# TKVideoUserInputsV2
Convenience node for collection size data for video.

<img width="500" alt="Screenshot 2026-10-31 125749" src="https://github.com/user-attachments/assets/8fe3f31a-51f9-4ed9-9006-d55937a26fd0" />



# TKPrintValueToLog
Print value to log, helpful for debug or status of workflow


# TKNodes (Handy Nodes for ComfyUI)

# A dictionary that contains the friendly/humanly readable titles for the nodes

NODE_DISPLAY_NAME_MAPPINGS = {
     "TKLargeVideoChunker": "Large Video Chunker",

     "TKTransitionDetector": "Video Transition Detector",
     "TKTransitionDetectorChunk": "Scene Detection - Get Video Chunk at index",
     "TKTransitionScenesCount": "Scene Detection - Get Total Transitions",
     
     "TKPromptEnhanced": "Enhanced Prompt with camera descriptives",
     "TKTrimAudioWithBooleans": "Trim Audio (Booleans)",
     "TKCalcLTXFrames":    "Calculate LTX Frames ",
     "TKVideoUserInputs": "Video User Inputs",
     "TKVideoUserInputsV2": "Video User Inputs - V2",
     "TKPhotoUserInputs": "GUI - Photo User Inputs",
     "TKVideoUserInputsBasic": "Video User Inputs Basic",
     "TKVideoAudioFuse": "Video Audio Fuse",
     "TKAudioFuse": "Audio Merge/Fuse",
     "TKSmartAudioChunker": "Smart Audio Chunker",
     "TKSmartVideoChunker": "Smart Video Chunker",
     "TKSimpleVideoChunker":"Simple Video Chunker",
     "TKAudioUnwrap": "Audio → Waveform Tensor",
     "TKPrintValueToLog": "Print Value to log",
     "TKSpeakerAudioTrackExtractor": "Extract nTh Audio track",
     "TKMergeAudioList": "Merge audio list to master audio",
     "TKTotalTracksInAudio": "User supplied tracks",
     "TKLocateSpeakersUsingSilenceBreaks": "Identify Speakers using Silence Breaks",
     "TKTrimImageOverlap": "Trim Padding used for Smooth Transition",
     "TKSpeakerDataFromTrack" : "Get a Track details from Track",
     "TKAudioSpeakerTalkTime": "Speaker Talk Times",
     "TKFadeInVideo": "Fade in Video",
     "TKPromptLooper": "Prompt Looper",
     "TKCrossDissolve":"Cross Dissolve Effect",
     "TKTrimFrames": "Trim Frames and Audio",

     "TKSnapFrames" : "Snap Frames to boundry rules",
     "TKAudioToFPSMatcher" :"Resample Audio for new FPS",
     "TKMultiImagePrompt": "Multi Image + Prompt",
     "TKPromptLooperAdv": "Prompt Looper Advanced",
     "TKMultiImageSelect": "Multi Image Select",
     "TKMultiPrompt": "Multi Prompt",

}




Manager install
----------------
Search for "Handy Nodes" in Comfy Manager

for manual install
---------------------
https://github.com/trashkollector/TKNodes

go to the custom_nodes folder in comfy

git clone https://github.com/trashkollector/TKNodes

Workflows
https://github.com/trashkollector/TKNodes/tree/main/workflow



