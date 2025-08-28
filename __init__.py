from . import tknodes

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserInputs": tknodes.TKVideoUserInputs,
    "TKSamplerUserInputs": tknodes.TKSamplerUserInputs,
}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt w Cam",
     "TKVideoUserInputs": "Video User Inputs",
     "TKSamplerUserInputs": "Sampler Inputs",
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

