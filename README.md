# See workflow folder for example workflows of various nodes




# TKLargeVideoChunker
Used to chunk very large files to avoid out of memory conditions
<img width="814" height="655" alt="Screenshot 2026-10-31 123957" src="https://github.com/user-attachments/assets/8af55403-179c-4dd3-b0d9-aaeeb53e6b47" />



# TKSmartVideoChunker
Silence-based video/audio chunking for LTX 2.3 / Wan 2.2.   Looks for silence in audio to create chunk breaks.   
This is helpful when speakers take a breath and we don't cut off speaker while talking. 
Chunking is required to get around VRAM issues.  For Low VRAM set chunk size lower"

 Silence-based video/audio chunking for LTX 2.3 or Wan 2.2. Slices at native fps, resamples to target_fps, and snaps to a valid frame count


<img width="432" height="497" alt="Screenshot 2026-08-05 131620" src="https://github.com/user-attachments/assets/839ac1e9-1feb-44c0-9039-2de24a1dca77" />

# TKSmartAudioChunker
Silence based audio chunker.. used in workflow for Singing or Talking, so it never breaks middle sentence.
TKSmartVideoChunker will call this node for the audio breaks.

#TKMultiImagePrompt
Manager a group of images and prompts in a uniform way.   Used together with FOR LOOP START / END
<img width="611" height="694" alt="Screenshot 2026-10-31 124505" src="https://github.com/user-attachments/assets/e7d9ec07-4afe-4639-84bf-2520ce96666d" />



# TKPromptLooper
A node for looping multiple prompts and avoid messy code.  Up to 4 prompts.  Used for long workflow where you want to swap images and prompts.
<img width="744" height="384" alt="Screenshot 2026-08-05 132344" src="https://github.com/user-attachments/assets/24463863-72bb-41bc-898d-ffdabc85fa5d" />


# TKSceneDetection
Video Scene Detection

<img width="972" height="635" alt="Screenshot 2026-10-31 124133" src="https://github.com/user-attachments/assets/30234a7f-dc77-4a08-a083-e47fbbcf8204" />


# TKVideoUserInputs - 
GUI for collecting inputs for Video related workflow.
Easily select size with visual feedback.
![Alt text](assets/tkvideouserinputs.png)


# TKPrintValueToLog
Print value to log, helpful for debug or status of workflow

# TKTransitionDetector  
Detects scene changes in video, similar to how Davinci works.

# TKSnapFrames  
Snap frames for LTX or Wan boundry rules
If you don't snap frames , you might get errors or bad renders.
This avoid the clumsy math expressions that are normally required in the workflow




# TKNodes (Handy Nodes for ComfyUI)
     "TKPromptEnhanced": "Enhanced Prompt with camera descriptives",
     "TKTrimAudioWithBooleans": "Trim Audio (Booleans)",
     "TKCalcLTXFrames":    "Calculate LTX Frames ",
     "TKVideoUserInputs": "Video User Inputs",
     "TKPhotoUserInputs": "GUI - Photo User Inputs",
     "TKVideoUserInputsBasic": "Video User Inputs Basic",
     "TKVideoAudioFuse": "Video Audio Fuse",
     "TKAudioFuse": "Audio Merge/Fuse",
     "TKSmartAudioChunker": "Smart Audio Chunker",
     "TKSmartVideoChunker": "Smart Video Chunker",
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
     "TKTransitionDetector": "Video Transition Detector",
     "TKSnapFrames" : "Snap Frames to boundry rules",
     "TKAudioToFPSMatcher" :"Resample Audio for new FPS",





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



