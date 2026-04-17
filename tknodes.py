import nodes
import torch
import torch.nn.functional as F
import torchaudio
import random
import math
import torch
from pydub import AudioSegment
from pydub.silence import detect_silence
import numpy as np

#  TK Collector -  Various Nodes for Comfy UI, TKPromptEnhanced
#  August 10, 2025
#  https://civitai.com/user/trashkollector175


any_type = type("AnyType", (str,), {"__ne__": lambda self, o: False})
ANY = any_type("*")

######################################################################################









# Remember to include your NODE_CLASS_MAPPINGS at the bottom of your file!




    
class TKPromptEnhanced:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
            
                "positve_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Positve prompt here!",
                           }),
                "negative_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Incorrect body proportions. bad drawing, bad anatomy, bad body shape, blurred details, awkward poses, incorrect shadows, unrealistic expressions, lack of texture, poor composition, text, logo, out of aspect ratio, body not fully visible, ugly, defects, noise, fuzzy, oversaturated, soft, blurry, out of focus, frame",
                    "lazy": True             }),
               
                "use_cam_options" : ("BOOLEAN", {
                    "default" : True, "description":"Disable/Enable Camera options.  These camera descriptions simply get appended to the positive text."}),
                
                "camera_shot_size": ([
                            "-",
                            "The camera takes an extreme closeup. ",
                            "The camera takes a closeup. ",
                            "The camera takes a medium shot ",
                            "The camera takes a medium full shot. ",
                            "The camera takes a full shot. ",
                            "The camera takes an extreme wide shot",
                            "The camera takes a wide shot",
                               ],),
                "camera_focus": ([
                            "-",
                            "The main person is in focus. ",
                            "The main person is in focus, the background objects are out of focus. ",
                            "All objects in the scene are in focus. ",
                            "The camera takes a tilt-shift focus shot. ",
                            "The camera takes a shot with soft focus. ",
                            "The camera takes a split diopeter shot. ",
                               ],),
                            
                "camera_angle":([
                            "-",
                           
                            "The camera is filming at eye level. ",
                            "The camera is filming at low angle.",       
                            "The camera is filming at hip level.", 
                            "The camera is filming at a knee level.", 
                            "The camera is filming at a ground level.", 
                            "The camera is filming at a low angle.", 
                            "The camera is filming at a shoulder level.", 
                            "The camera is overhead.", 
                            "The camera is taking an aerial shot.", 

                            ],),
                            
                "camera_movement":([
                            "-",
                            "The camera is stationary.",
                            "The camera is jittery",
                            "The camera is zooming in. ",
                            "The camera is zooming out. ",       
                            "The camera is panning right. ", 
                            "The camera is panning right. ", 
                            "The camera tilts up. ", 
                            "The camera tilts down. ", 
                            "The camera orbits. ", 
 
                            ],),
                            
                "light": (["-",
                            "Scene has warm light. ",
                            "Scene has midday light.",
                            "Scene has morning light. ",
                            "Scene  has evening light. ",
                            "There is a spotlight on the subject. ",
                            "The scene has backlighting. ",
                            "The scene has dramatic lighting. ",
                            "The scene has bright neon lighting. ",
                            "The scene has low light. ",
                            "The scene has harsh shadows. ",
                            "The scene has specular lighting. ",
                            "The scene has soft diffused lighting. ",
                            "The scene has radiant rays. ",
                            "The scene is luminescent.     ",    ],), 
                            

                                      
                }
            }
        

    RETURN_TYPES = ("STRING","STRING")
    RETURN_NAMES = ("positive","negative")
    FUNCTION = "tkpromptenhanced"
    #OUTPUT_NODE = False
    CATEGORY = "TKNodes"
    DESCRIPTION = "Enhanced prompt, contains camera controls which are appended to the positive prompt"

    
    def tkpromptenhanced(self, positve_prompt, negative_prompt,use_cam_options, camera_shot_size, camera_angle, camera_focus, camera_movement, light):
        
        
        pos = positve_prompt 
        
        if use_cam_options == True:
           pos =    positve_prompt+ ". "+ camera_angle+". "+ camera_focus+". "+ camera_movement+". "+ camera_shot_size+". "+ light
        
            
        return (pos,negative_prompt)
        

    
     
class TKVideoUserInputs:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "height": ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "length_selector": (
                                ["Use # Seconds", "Use # Frames"], # "Use # Seconds" is now the default
                                {"default": "Use # Seconds"}       # Explicitly defining the default
                            ),
                "total_frames": ("INT", {"default": 97,   "min": 10, "max": 1000, "tooltip" : "This value applies when length_selector = Use Frames"}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000, "tooltip" : "This value applies when length_selector = Use Seconds"}),
                "fps":         ("FLOAT", {"default": 24.0, "min": 16.0, "max": 60.0, "tooltip" : "FPS from video info node"}),
                

            },
        }

    RETURN_TYPES = ("INT",              "INT",         "INT",    "FLOAT", "FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames","fps", "totalSeconds")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Common Video User Inputs-  Use the Length_Selector to determine if you want to select by frames or seconds"

    def main(self, width, height, total_frames, length_selector, fps, num_seconds, ):
     
        returnSecs = num_seconds
        if (length_selector=="Use # Seconds") :
            total_frames = int(fps * num_seconds)
        else :
            returnSecs =   float(total_frames) / fps;
        

        return (width, height, total_frames, fps, returnSecs )





class TKVideoUserInputsBasic:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
                "height": ("INT", {"default": 1280, "min": 100, "max": 1288, "step": 32}),
               
               },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("video_width", "video_height")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Common Video User Inputs- Basic"

    def main(self, width, height ):
     
        
        return (width, height )




class TKPhotoUserInputs:
    def __init__(self):
        pass
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "width":  ("INT", {"default": 3000, "min": 100, "max": 3000, "step": 64}),
                "height": ("INT", {"default": 3000, "min": 100, "max": 3000, "step": 64}),
               
               },
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("photo_width", "photo_height")
    FUNCTION = "main"
    CATEGORY = "TKNodes"
    DESCRIPTION = "Photo User Inputs"

    def main(self, width, height ):
     
        
        return (width, height )



    
       
        
        

