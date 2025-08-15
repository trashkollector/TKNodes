import nodes
import torch


#  TK Collector -  Various Nodes for Comfy UI, TKPromptEnhanced
#  August 10, 2025
#  https://civitai.com/user/trashkollector175
    
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
                    "lazy": True             }),
                "negative_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Incorrect body proportions. bad drawing, bad anatomy, bad body shape, blurred details, awkward poses, incorrect shadows, unrealistic expressions, lack of texture, poor composition, text, logo, out of aspect ratio, body not fully visible, ugly, defects, noise, fuzzy, oversaturated, soft, blurry, out of focus, frame",
                    "lazy": True             }),
               
                
                "camera_shot_size": ([
                            "The camera takes an extreme closeup. ",
                            "The camera takes a closeup. ",
                            "The camera takes a medium shot ",
                            "The camera takes a medium full shot. ",
                            "The camera takes a full shot. ",
                            "The camera takes an extreme wide shot",
                            "The camera takes a wide shot",
                               ],),
                "camera_focus": ([
                            "Main object is in focus, background is out of focus. ",
                            "All objects in the scene are in deep focus. ",
                            "The camera takes a tilt-shift focus shot. ",
                            "The camera takes a shot with soft focus. ",
                            "The camera takes a split diopeter shot. ",
                               ],),
                            
                "camera_angle":([
                            "The camera is at eye level. ",
                            "The camera is at low angle.",       
                            "The camera is at hip level.", 
                            "The camera is at a knee level.", 
                            "The camera is at a ground level.", 
                            "The camera is at a low angle.", 
                            "The camera is at a shoulder level.", 
                            "The camera is overhead.", 
                            "The camera is taking an aerial.", 

                            ],),
                            
                "camera_movement":([
                            "The camera is stationary.",
                            "The camera is zooming in. ",
                            "The camera is zooming out. ",       
                            "The camera is panning right. ", 
                            "The camera is panning right. ", 
                            "The camera tilts up. ", 
                            "The camera tilts down. ", 
                            "The camera orbits. ", 
 
                            ],),
                            
                "light": (["Scene has warm light. ",
                           
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

    
    def tkpromptenhanced(self, positve_prompt, negative_prompt, camera_shot_size, camera_angle, camera_focus, camera_movement, light):
            
        pos =    positve_prompt+ ". "+ camera_angle+". "+ camera_focus+". "+ camera_movement+". "+ camera_shot_size+". "+ light
        
            
        return (pos,negative_prompt)
        

    
     

    
    
 