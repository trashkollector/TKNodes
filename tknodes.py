import nodes
import torch
import torch.nn.functional as F
import torchaudio


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
                           }),
                "negative_prompt": ("STRING", {
                    "multiline": True, #True if you want the field to look like the one on the ClipTextEncode node
                    "default": "Incorrect body proportions. bad drawing, bad anatomy, bad body shape, blurred details, awkward poses, incorrect shadows, unrealistic expressions, lack of texture, poor composition, text, logo, out of aspect ratio, body not fully visible, ugly, defects, noise, fuzzy, oversaturated, soft, blurry, out of focus, frame",
                    "lazy": True             }),
               
                "use_cam_options" : ("BOOLEAN", {
                    "default" : True,}),
                
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
                    ["Use # Frames", "Use # Seconds"],
                ),
                "total_frames": ("INT", {"default": 81,   "min": 32, "max": 1000}),
                "num_seconds": ("FLOAT", {"default": 5.0, "min": 2.0, "max": 1000}),
                "fps":         ("FLOAT", {"default": 16.0, "min": 16.0, "max": 60.0}),
                

            },
        }

    RETURN_TYPES = ("INT", "INT","INT","FLOAT")
    RETURN_NAMES = ("video_width", "video_height", "total_frames","fps")
    FUNCTION = "main"
    CATEGORY = "TKNodes"

    def main(self, width, height, total_frames, length_selector, fps, num_seconds, ):
     
        if (length_selector=="Use # Seconds") :
            total_frames = int(fps * num_seconds)
        return (width, height, total_frames, fps )







    
class TKSamplerUserInputs :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
            
                "steps": ("INT", {
                    "default": "10", "min": 1, "max": 200,
                    "lazy": True  }),      
                "cfg":  ("FLOAT", {
                    "default": "1.0", "min": 0, "max": 100,
                    "lazy": True   }),                  
            
                }
            }
        

    RETURN_TYPES = ("INT",  "FLOAT")
    RETURN_NAMES = ("steps","cfg")


    FUNCTION = "tksamplerinputs"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"

    
    def tksamplerinputs(self, steps, cfg ):
            
            
            
        return ( steps, cfg)
        
        
        
class TKVideoAudioFuse :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "image": ("IMAGE",),
                              
                "audio1": ("AUDIO",),  
            
                "audio1_volume" : ("INT", {"default":0,"min":-10,"max":10}),                

            },
        
            "optional": {
            
                "audio2": ("AUDIO",),    
                "audio2_volume" : ("INT", {"default":0,"min":-10,"max":10}),                    

                "audio3": ("AUDIO",),    
                "audio3_volume" : ("INT", {"default":0,"min":-10,"max":10}),                    
            }
        }
        

    RETURN_TYPES = ("IMAGE",  "AUDIO")
    RETURN_NAMES = ("image",  "audio")


    FUNCTION = "tkvideoaudiofuse"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"

    
    def tkvideoaudiofuse(self, image, audio1,  audio1_volume,   audio2_volume,  audio3_volume, audio2=None, audio3=None, ):
        audio_tensor1 = audio1['waveform']      
        sr = audio1["sample_rate"]
        avg1 = self.adjustVolume(audio_tensor1, audio1_volume)
        
 
        if  audio2 is not None :
            sr2 =audio2["sample_rate"]
            aud2 =  self.adjustVolume(audio2["waveform"], audio2_volume)
            (avg1, sr) = self.average_audio_tensors(audio_tensor1, aud2, sr, sr2 )
        
        if audio3 is not None :
            sr3 =audio3["sample_rate"]
            aud2 =  self.adjustVolume(audio3["waveform"], audio3_volume)
            (avg1, sr) = self.average_audio_tensors(avg1, audio3["waveform"], sr, sr3 )
    
        audio = {
           "waveform": avg1,
           "sample_rate": sr
        }
        return ( image, audio)
        

    def adjustVolume(self, tensor, vol) :
        gain_in_db = vol*3

        # Apply the volume transform
        vol_transform = torchaudio.transforms.Vol(gain=gain_in_db, gain_type='db')
        new_tensor = vol_transform(tensor)
        
        return new_tensor
        
        
    def average_audio_tensors(self,
        audio1,
        audio2,
        sr1,
        sr2
    ) :
        """
        Averages two audio tensors of potentially different lengths and channel counts.

        It resamples tensors to a common sample rate, converts them to mono, pads the 
        shorter tensor with zeros, and then averages the result.

        Args:
            audio1 (torch.Tensor): The first audio tensor.
                                   Expected shape: [channels, frames].
            audio2 (torch.Tensor): The second audio tensor.
                                   Expected shape: [channels, frames].
            sr1 (int): The sample rate of the first audio tensor.
            sr2 (int): The sample rate of the second audio tensor.

        Returns:
            torch.Tensor: A new tensor representing the average of the two inputs, 
                          as a mono signal.
        """
        print(audio1.shape)
        print(audio2.shape)

        
        if not isinstance(audio1, torch.Tensor) or not isinstance(audio2, torch.Tensor):
            raise TypeError("Inputs must be PyTorch tensors.")

        # Step 1: Resample tensors to a common sample rate
        target_sr = min(sr1, sr2)
        if sr1 != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr1, new_freq=target_sr)
            audio1 = resampler(audio1)
        if sr2 != target_sr:
            resampler = torchaudio.transforms.Resample(orig_freq=sr2, new_freq=target_sr)
            audio2 = resampler(audio2)

        # Step 2: Convert tensors to mono if they have more than one channel
        # This is done by averaging the channels
        if audio1.shape[1] > 1:
            audio1 = torch.mean(audio1, dim=0, keepdim=True)
        if audio2.shape[1] > 1:
            audio2 = torch.mean(audio2, dim=0, keepdim=True)

        # Step 3: Pad the shorter tensor to match the length of the longer tensor

        max_len = max(audio1.shape[2], audio2.shape[2])
        
        if audio1.shape[2] < max_len:
            padding_needed = max_len - audio1.shape[2]
            padded_audio1 = F.pad(audio1, (0, padding_needed), 'constant', 0)
        else:
            padded_audio1 = audio1

        if audio2.shape[2] < max_len:
            padding_needed = max_len - audio2.shape[2]
            padded_audio2 = F.pad(audio2, (0, padding_needed), 'constant', 0)
        else:
            padded_audio2 = audio2

        # Step 4: Average the padded tensors
        averaged_audio = (padded_audio1 + padded_audio2) / 2

        return (averaged_audio, target_sr)


   