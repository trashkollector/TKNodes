from . import tknodes

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKPhotoUserInputs": tknodes.TKPhotoUserInputs,
    "TKVideoUserInputsBasic": tknodes.TKVideoUserInputsBasic,
    "TKVideoAudioFuse": tknodes.TKVideoAudioFuse,
    "TKAudioFuse": tknodes.TKAudioFuse,
    "TKAudioUnwrap": tknodes.TKAudioUnwrap,
    "TKPrintValueToLog": tknodes.TKPrintValueToLog,
    "TKCalcAudioChunks": tknodes.TKCalcAudioChunks,}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt (Cam)",
     "TKVideoUserInputs": "Video User Inputs",
     "TKPhotoUserInputs": "Visual Photo Sizer",
     "TKVideoUserInputsBasic": "Video User Inputs Basic",
     "TKVideoAudioFuse": "Merge Video and multiple Audio tracks",
     "TKAudioFuse": "Merge multiple Audio tracks together",
     "TKAudioUnwrap": "Extract Waveform from Audio",
     "TKPrintValueToLog": "Write to Comfy Log",
     "TKCalcAudioChunks": "Chunkify long audio",


}


WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
