import torch
import torch.nn.functional as F
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
    DESCRIPTION = "GUI for setting video resolution , frames, duration"

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



class TKFadeInVideo:
    DESCRIPTION="Fade in Video"
    """Fades in the first N frames of a video from black (or a chosen color)
    to full opacity. Frame 1 = 0% opaque, frame N = 100% opaque, frames
    after N are untouched. Intended to run right after VAE Decode."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "Decoded video frames [N, H, W, C]"}),
                "fade_frames": ("INT", {"default": 5, "min": 1, "max": 240,
                                         "tooltip": "Number of frames to fade in over. "
                                                     "Frame 'fade_frames' reaches 100%."}),
                "start_alpha": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
                                           "tooltip": "Starting opacity at frame 1 (0.5 = 50%). "
                                                       "Ramps up to 1.0 by fade_frames."}),
            },
            "optional": {
                "fade_color": ("STRING", {"default": "0,0,0",
                                           "tooltip": "R,G,B (0-255) to fade in from. Default black."}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)
    FUNCTION = "fade_in"
    CATEGORY = "TKNodes"

    def fade_in(self, images, fade_frames, start_alpha=0.5, fade_color="0,0,0"):
        import torch
           
        total_frames = images.shape[0]
        n = min(fade_frames, total_frames)

        # Parse fade color -> normalized 0-1 tensor matching channel count
        try:
            r, g, b = [float(c.strip()) / 255.0 for c in fade_color.split(",")]
        except Exception:
            r, g, b = 0.0, 0.0, 0.0

        channels = images.shape[-1]
        if channels == 4:
            color = torch.tensor([r, g, b, 1.0], dtype=images.dtype, device=images.device)
        else:
            color = torch.tensor([r, g, b], dtype=images.dtype, device=images.device)

        result = images.clone()

        # Opacity ramps linearly from start_alpha -> 1.0 (fully opaque/original)
        # frame 1 -> start_alpha, frame n -> 1.0
        alpha_range = 1.0 - start_alpha
        for i in range(n):
            alpha = start_alpha + alpha_range * ((i + 1) / n)
            frame = images[i]
            faded = frame * alpha + color * (1.0 - alpha)
            result[i] = faded.clamp(0.0, 1.0)

        return (result,)



            

class TKCrossDissolve:
    DESCRIPTION="Cross Dissolve two video segments together to make transition seamless"
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "curr_scene": ("IMAGE",  {  "tooltip": "the current video segment. "}),
                "curve": (["linear", "ease_in_out"],  { "tooltip": "select Cross dissolve effect. "}),
            },
            "optional": {
                "prev_tail": ("IMAGE",  {"tooltip": "just the section of previous segment that we want to cross-dissolve. "}),  # absent/empty on segment 1
                "numDissolveFrames": ("INT", {"default": 0, "min": 0, "max": 4096, "tooltip": "number of frames to cross-dissolve. if <=0, uses the full length of prev_tail instead."}),
            }
        }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "blend"
    CATEGORY = "TKNodes"

    def blend(self, curr_scene, curve, prev_tail=None, numDissolveFrames=0):

        if prev_tail is None or prev_tail.shape[0] == 0:
            return (curr_scene,)

        if numDissolveFrames is not None and numDissolveFrames > 0:
            # take only the last numDissolveFrames of prev_tail, clamped to what's available
            tail_n = min(numDissolveFrames, prev_tail.shape[0])
            prev_tail = prev_tail[-tail_n:]

        n = min(prev_tail.shape[0], curr_scene.shape[0])
        print(f"[dissolve] n={n}, curve={curve}")

        curr_head = curr_scene[:n]
        curr_rest = curr_scene[n:]

        alphas = torch.linspace(0, 1, n)
        if curve == "ease_in_out":
            alphas = alphas * alphas * (3 - 2 * alphas)

        blended = torch.stack([
            (1 - a) * prev_tail[i] + a * curr_head[i]
            for i, a in enumerate(alphas)
        ])

        out = torch.cat([blended, curr_rest], dim=0)
        return (out,)