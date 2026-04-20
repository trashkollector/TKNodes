from . import tknodes, misc, speakers, audioChunker

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKPhotoUserInputs": tknodes.TKPhotoUserInputs,
    "TKVideoUserInputsBasic": tknodes.TKVideoUserInputsBasic,
    "TKVideoAudioFuse": misc.TKVideoAudioFuse,
    "TKAudioFuse": misc.TKAudioFuse,
    "TKAudioUnwrap": misc.TKAudioUnwrap,
    "TKSmartAudioChunker": audioChunker.TKSmartAudioChunker,
    "TKPrintValueToLog": misc.TKPrintValueToLog,
    "TKMergeAudioList": misc.TKMergeAudioList,
    "TKSpeakerAudioTrackExtractor" : speakers.TKSpeakerAudioTrackExtractor,
    "TKAudioSelectSplits" : speakers.TKAudioSelectSplits,
    "TKTotalTracksInAudio" : speakers.TKTotalTracksInAudio,
    "TKSpeakerDataFromTrack" : speakers.TKSpeakerDataFromTrack,
    "TKTrimImageOverlap": audioChunker.TKTrimImageOverlap,
    "TKCalcLTXFrames":    audioChunker.TKCalcLTXFrames,
    "TKAudioSpeakerTalkTime": speakers.TKAudioSpeakerTalkTime,}



# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt (Cam)",
     "TKCalcLTXFrames":    "TK Calc LTX Frames",
     "TKVideoUserInputs": "Video User Inputs",
     "TKPhotoUserInputs": "GUI - Photo User Inputs",
     "TKVideoUserInputsBasic": "Video User Inputs Basic",
     "TKVideoAudioFuse": "Video Audio Fuse",
     "TKAudioFuse": "Audio Merge/Fuse",
     "TKSmartAudioChunker": "Smart Audio Chunker",
     "TKAudioUnwrap": "Audio → Waveform Tensor",
     "TKPrintValueToLog": "Print Value to log",
     "TKSpeakerAudioTrackExtractor": "Extract nTh Audio track",
     "TKMergeAudioList": "Merge audio list to 1 audio",
     "TKTotalTracksInAudio": "User supplied tracks",
     "TKAudioSelectSplits": "Audio Splits Selector Slider",
     "TKTrimImageOverlap": "Trim images to remove overlap",
     "TKSpeakerDataFromTrack" : "Get a Track details from Track",
     "TKAudioSpeakerTalkTime": "Speaker Talk Times",


}


WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
