from . import tknodes

NODE_CLASS_MAPPINGS = {
    "TKPromptEnhanced": tknodes.TKPromptEnhanced,
    "TKVideoUserinputs": tknodes.TKVideoUserInputs,
    "TKSamplerUserInputs": tknodes.TKSamplerUserInputs,
}


# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
     "TKPromptEnhanced": "Enhanced Prompt w Cam",
     "TKVideoUserinputs": "Video User Inputs",
     "TKSamplerUserInputs": "Sampler Inputs",


}
