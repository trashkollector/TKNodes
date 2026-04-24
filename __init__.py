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
    "TKLocateSpeakersUsingSilenceBreaks" : speakers.TKLocateSpeakersUsingSilenceBreaks,
    "TKTotalTracksInAudio" : speakers.TKTotalTracksInAudio,
    "TKSpeakerDataFromTrack" : speakers.TKSpeakerDataFromTrack,
    "TKTrimImageOverlap": audioChunker.TKTrimImageOverlap,
    "TKCalcLTXFrames":    audioChunker.TKCalcLTXFrames,
    "TKTrimAudioWithBooleans": speakers.TKTrimAudioWithBooleans,
    "TKAudioSpeakerTalkTime": speakers.TKAudioSpeakerTalkTime,}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt (Cam)",
     "TKTrimAudioWithBooleans": "Trim Audio (Booleans)",
     "TKCalcLTXFrames":    "Calculate LTX Frames",
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
     "TKLocateSpeakersUsingSilenceBreaks": "Identify Speakers using Silence Breaks",
     "TKTrimImageOverlap": "Trim extra padding frames from video",
     "TKSpeakerDataFromTrack" : "Get a Track details from Track",
     "TKAudioSpeakerTalkTime": "Speaker Talk Times",


}


WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
