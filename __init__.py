from . import tknodes

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKPhotoUserInputs": tknodes.TKPhotoUserInputs,
    "TKVideoUserInputsBasic": tknodes.TKVideoUserInputsBasic,
    "TKVideoAudioFuse": tknodes.TKVideoAudioFuse,
    "TKAudioFuse": tknodes.TKAudioFuse,
    "TKMergeAudioList": tknodes.TKMergeAudioList,
    "TKAudioUnwrap": tknodes.TKAudioUnwrap,
    "TKSmartAudioChunker": tknodes.TKSmartAudioChunker,
    "TKPrintValueToLog": tknodes.TKPrintValueToLog,
    "TKCalcAudioChunks": tknodes.TKCalcAudioChunks,}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt (Cam)",
     "TKVideoUserInputs": "Video User Inputs",
     "TKPhotoUserInputs": "GUI - Photo User Inputs",
     "TKVideoUserInputsBasic": "Video User Inputs Basic",
     "TKVideoAudioFuse": "Video Audio Fuse",
     "TKAudioFuse": "Audio Fuse",
     "TKMergeAudioList": "Merge audio list",
     "TKSmartAudioChunker": "Smart Audio Chunker",
     "TKAudioUnwrap": "Audio → Waveform Tensor",
     "TKPrintValueToLog": "Print Value to log",
     "TKCalcAudioChunks": "Calc Audio Chunks",


}


WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
