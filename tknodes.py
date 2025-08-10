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
                "ignore_all_camera_options" : ("BOOLEAN", {"default":False}),
                "subject_to_camera": (["The subject is looking straight forward at the camera.", 
                                       "The subject is looking away from the camera.",
                                       "The subject is looking up at the camera.",       
                                       "The subject is looking down at the camera.",                                       
                                       "The subject is looking up.",
                                       "The subject is looking down.",
                                       "The subject closes their eyes.", 
                                       "The subject turns their head.",
                                       "The subject looks at the other person.",                                       
                                       "The subject looks away from the other person.", ],),
                "camera_zoom": ([      "The camera is stationary.",
                                       "The camera zooms in very slowly.", 
                                       "The camera zooms in quickly.",
                                       "The camera zooms out slowly.",
                                       "The camera zooms out very slowly.",  ],),   
               "camera_pan": ([         "The camera does not pan.",
                                        "The camera pans slowly to the right.", 
                                       "The camera pans quickly to the right.",
                                       "The camera pans slowly to the left.",
                                       "The camera pans quickly to the left.", ],),      
               "camera_tilt": ([         "The camera does not tilt.",
                                        "The camera tilts upward.", 
                                       "The camera tilts downward.", ],),     
               "camera_depth": ([      "The camera takes a normal shot.",
                                       "The camera uses a wide angle shot.",
                                        "The camera uses a telephoto view.", 
                                       "The camera takes a close up shot.",],),                                         
                }
            }
        

    RETURN_TYPES = ("STRING","STRING")
    RETURN_NAMES = ("positive","negative")


    FUNCTION = "tkprompt"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"

    
    def tkprompt(self, positve_prompt, negative_prompt, ignore_all_camera_options,
                 subject_to_camera, camera_zoom, camera_pan, camera_tilt, camera_depth):

        if (ignore_all_camera_options) :
            return (positve_prompt, negative_prompt)
            
        pos =    positve_prompt+ " "+subject_to_camera + "   " +  camera_zoom + "  "+ camera_pan + "  "+ camera_tilt + "  " + camera_depth
            
        return (pos,negative_prompt)
        

    
     

    
    
 