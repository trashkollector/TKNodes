from . import tknodes, misc, speakers, audioChunker, utilnodes,  MultiImagePrompt


NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKPhotoUserInputs": tknodes.TKPhotoUserInputs,
    "TKVideoUserInputsBasic": tknodes.TKVideoUserInputsBasic,
    "TKVideoAudioFuse": misc.TKVideoAudioFuse,
    "TKAudioFuse": misc.TKAudioFuse,
    "TKAudioUnwrap": misc.TKAudioUnwrap,
    "TKSmartAudioChunker": audioChunker.TKSmartAudioChunker,
    "TKSmartVideoChunker": audioChunker.TKSmartVideoChunker,
    "TKPrintValueToLog": misc.TKPrintValueToLog,
    "TKMergeAudioList": misc.TKMergeAudioList,
    "TKSpeakerAudioTrackExtractor" : speakers.TKSpeakerAudioTrackExtractor,
    "TKLocateSpeakersUsingSilenceBreaks" : speakers.TKLocateSpeakersUsingSilenceBreaks,
    "TKTotalTracksInAudio" : speakers.TKTotalTracksInAudio,
    "TKSpeakerDataFromTrack" : speakers.TKSpeakerDataFromTrack,
    "TKTrimImageOverlap": audioChunker.TKTrimImageOverlap,
    "TKCalcLTXFrames":    audioChunker.TKCalcLTXFrames,
    "TKTrimAudioWithBooleans": speakers.TKTrimAudioWithBooleans,
    "TKAudioSpeakerTalkTime": speakers.TKAudioSpeakerTalkTime,
    "TKFadeInVideo": tknodes.TKFadeInVideo,
    "TKCrossDissolve": tknodes.TKCrossDissolve,
    "TKPromptLooper": audioChunker.TKPromptLooper,  
    "TKTrimFrames": tknodes.TKTrimFrames,
    "TKTransitionDetector": utilnodes.TKTransitionDetector,
    "TKSnapFrames" : utilnodes.TKSnapFrames,
    "TKAudioToFPSMatcher" : utilnodes.TKAudioToFPSMatcher,
    "TKMultiImagePrompt": MultiImagePrompt.TKMultiImagePrompt,
    "TKPromptLooperAdv": audioChunker.TKPromptLooperAdv,
}



# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
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
     "TKTransitionDetector": "Video Transition Detector",
     "TKSnapFrames" : "Snap Frames to boundry rules",
     "TKAudioToFPSMatcher" :"Resample Audio for new FPS",
     "TKMultiImagePrompt": "Multi Image + Prompt",
     "TKPromptLooperAdv": "Prompt Looper Advanced",

}




WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
