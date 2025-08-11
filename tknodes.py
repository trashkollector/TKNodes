import nodes
import torch


#  TK Collector -  Various Nodes for Comfy UI
#  August 10, 2025
#  https://civitai.com/user/trashkollector175
    
class TKPrompt:

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
                    "default": " incorrect body proportions. bad drawing, bad anatomy, bad body shape, blurred details, awkward poses, incorrect shadows, unrealistic expressions, lack of texture, poor composition, text, logo, out of aspect ratio, body not fully visible, ugly, defects, noise, fuzzy, oversaturated, soft, blurry, out of focus, frame",
                    "lazy": True             }),
               
                
                "camera": ([" ",
                            "The camera performa a dolly-out shot. ",
                            "The camera performs a  dolly-in. ",
                            "A reverse dolly shot of the character. ",
                            "A pan shot of the character. ",
                            "The camera tilts upward. ",
                            "The camera is above the scene, it is facing downward. ",
                            "The camera gradually zooms in. ",
                            "The camera gradually zooms out. ",
                            "The camera tracks the character as the character moves. ",
                            "A crane shot showing the expansiveness of the scene. ",
                            "An arc shot, circling the character in the scene. ",
                            "A handheld shot  with the camera moving slightly. ",
                            "An orbit shot around a the character. ",
                            "A parallax shot moving through the scene. ",
                            "A push-pull shot on the character.  ",
                            "An aerial shot soaring over the scene, the camera tilting down. ",
                            "A lateral shot tracking a character. ", ],),
                            
                            
                 "light": ([" ",
                            "Scene has warm light. ",
                            "Scene has morning light. ",
                            "Scene  has evenling light. ",
                            "There is a spotlight on the subject. ",
                            "The scene has backlighting. ",
                            "The scene has dramatic lighting. ",
                            "The scene has bright neon lighting. ",
                            "The scene has candlelit lighting. ",
                            "The scene has harsh shadows. ",
                            "The scene has specular lighting. ",
                            "The scene has soft diffused lighting. ",
                            "The scene has radiant god rays. ",
                            "The scene is luminescent.     ",    ],), 
                                      
                }
            }
        

    RETURN_TYPES = ("STRING","STRING")
    RETURN_NAMES = ("positive","negative")


    FUNCTION = "tkprompt"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"

    
    def tkprompt(self, positve_prompt, negative_prompt, camera, light):
            
        pos =    positve_prompt+ camera + light
            
        return (pos,negative_prompt)
        

    
     

    
    
 