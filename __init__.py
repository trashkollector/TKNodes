from . import tknodes

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKPhotoUserInputs": tknodes.TKPhotoUserInputs,
    "TKVideoUserInputsBasic": tknodes.TKVideoUserInputsBasic,
    "TKVideoAudioFuse": tknodes.TKVideoAudioFuse,
    "TKAudioFuse": tknodes.TKAudioFuse,
    "TKAudioUnwrap": tknodes.TKAudioUnwrap,
    "TKSmartAudioChunker": tknodes.TKSmartAudioChunker,
    "TKPrintValueToLog": tknodes.TKPrintValueToLog,
    "TKMergeAudioList": tknodes.TKMergeAudioList,
    "TKSpeakerAudioTrackExtractor" : tknodes.TKSpeakerAudioTrackExtractor,\
    "TKTotalTracksInAudio" : tknodes.TKTotalTracksInAudio,
    "TKSpeakerDataFromTrack" : tknodes.TKSpeakerDataFromTrack,
    "TKAudioSpeakerTalkTime": tknodes.TKAudioSpeakerTalkTime,}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt (Cam)",
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
     "TKSpeakerDataFromTrack" : "Get a Track details from Track",
     "TKAudioSpeakerTalkTime": "Speaker Talk Times",


}


WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
