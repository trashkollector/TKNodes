import nodes
import torch
import torch.nn.functional as F
import torchaudio

any_type = type("AnyType", (str,), {"__ne__": lambda self, o: False})
ANY = any_type("*")


# take a video and up to 3 audio streams and merge everything together and control volume
class TKVideoAudioFuse :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "image": ("IMAGE",{"tooltip":"the video part - so it can be merged with up to 3 audio streams"}),
                              
                "audio1": ("AUDIO",{"tooltip":"1st Audio Stream - will be fused/merged with video, the images"}),  
            
                "audio1_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                

            },
        
            "optional": {
            
                "audio2": ("AUDIO",{"tooltip":"2nd Audio Stream - will be fused/merged with video and all audio tracks"}),    
                "audio2_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    

                "audio3": ("AUDIO",{"tooltip":"2nd Audio Stream - will be fused/merged with video and all audio tracks"}),    
                "audio3_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    
            }
        }
        

    RETURN_TYPES = ("IMAGE",  "AUDIO")
    RETURN_NAMES = ("image",  "audio")


    FUNCTION = "tkvideoaudiofuse"

    #OUTPUT_NODE = False

    CATEGORY = "TKNodes"
    DESCRIPTION = "Fuse/Overlayt up to 3 audio streams and 1 video together.  "

    
    def tkvideoaudiofuse(self, image, audio1,  audio1_volume,   audio2_volume,  audio3_volume, audio2=None, audio3=None, ):
        audio_tensor1 = audio1['waveform']      
        sr = audio1["sample_rate"]
        avg1 = self.adjustVolume(audio_tensor1, audio1_volume)
        
 
        if  audio2 is not None :
            sr2 =audio2["sample_rate"]
            aud2 =  self.adjustVolume(audio2["waveform"], audio2_volume)
            (avg1, sr) = self.average_audio_tensors(avg1, aud2, sr, sr2 )
        
        if audio3 is not None :
            sr3 =audio3["sample_rate"]
            aud3 =  self.adjustVolume(audio3["waveform"], audio3_volume)
            (avg1, sr) = self.average_audio_tensors(avg1, aud3, sr, sr3 )
    
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

# take up 3 to audio streams and merge/fuse them together to create on audio stream
class TKAudioFuse :
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):

        return {
            "required": {
                "audio1": ("AUDIO", {"tooltip":"Fuse or merge two to 3 audio streams together producing 1 final audio"}),  
                "audio1_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                
                "audio2": ("AUDIO",{"tooltip":"Fuse or merge two to 3 audio streams together producing 1 final audio"}),    
                "audio2_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),   
            },
            "optional": {
                "audio3": ("AUDIO",),    
                "audio3_volume" : ("INT", {"default":0,"min":-10,"max":10, "tooltip":"Enter volume -10 lowest, 0 = normal, 10 = loudest"}),                    
            }
        }
        
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "tkaudiofuse"
    #OUTPUT_NODE = False
    CATEGORY = "TKNodes"
    DESCRIPTION = "Fuse/Overlay up to 3 audio streams together"

    
    def tkaudiofuse(self, audio1,  audio1_volume,   audio2 , audio2_volume,  audio3_volume,  audio3 =None, ):
       
        vidaud_obj = TKVideoAudioFuse()
        

        audio_tensor1 = audio1['waveform']      
        sr = audio1["sample_rate"]
        avg1 = vidaud_obj.adjustVolume(audio_tensor1, audio1_volume)
        
 
        if  audio2 is not None :
            sr2 =audio2["sample_rate"]
            aud2 =  vidaud_obj.adjustVolume(audio2["waveform"], audio2_volume)
            (avg1, sr) = vidaud_obj.average_audio_tensors(avg1, aud2, sr, sr2 )
        
        if audio3 is not None :
            sr3 =audio3["sample_rate"]
            aud3 =  vidaud_obj.adjustVolume(audio3["waveform"], audio3_volume)
            (avg1, sr) = vidaud_obj.average_audio_tensors(avg1, aud3, sr, sr3 )
            
        print(avg1.shape )
        audio = {
           "waveform": avg1,
           "sample_rate": sr,
        }
     
        return (audio,)




# Unwrap an audio return the waveform.        
class TKAudioUnwrap:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"audio": ("AUDIO",)}}

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("waveform",)
    FUNCTION = "unwrap"
    CATEGORY = "audio"
    DESCRIPTION = "Unwrap an audio latent - return the waveform. "


    def unwrap(self, audio):
        return (audio["waveform"],)

## Print to log
class TKPrintValueToLog:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "value": (ANY,{"tooltip" : "Value to be printed to comfyui.log"}),
                "label": ("STRING", {"default": "mylog","tooltip": "Label for your log"}),
            }
        }

    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ("value",)
    OUTPUT_NODE = True
    FUNCTION = "log"
    CATEGORY = "debug"
    DESCRIPTION = "Print to Log - useful for debugging nodes "


    def log(self, value, label):
        print(f"[{label}] : {value}")
        return (value,)

   
##
## Takes a list of audio files and join them to create on stream
## Useful when concat a bunch of videos together with VHS Combile
class TKMergeAudioList:
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio_list": ("AUDIO", {"tooltip" : "a list of audio to convert to 1 audio stream"})
            }
        }
    
    # This is essential: it collects all clips into one list instead of looping the node
    INPUT_IS_LIST = True 
    RETURN_TYPES = ("AUDIO",)
    FUNCTION = "merge"
    CATEGORY = "HandyNodes-KT"
    DESCRIPTION = " Takes a list of audio files and join them to create on stream"

    def merge(self, audio_list):
        waveforms = [item['waveform'] for item in audio_list]
        sample_rate = audio_list[0]['sample_rate']
        
        # 1. Create a tiny fade (0.1 seconds) to hide the 'pop'
        fade_len = int(sample_rate * 0.1) 
        fade_in = torch.linspace(0.0, 1.0, fade_len)
        fade_out = torch.linspace(1.0, 0.0, fade_len)


        # 2. Process the list to apply fades to the joins
        merged_waveform = waveforms[0]
        for i in range(1, len(waveforms)):
            current_clip = waveforms[i]
            
            # --- SAFETY CHECK ADDED HERE ---
            # Ensure fade_len is not longer than the available audio in either clip
            actual_fade = min(fade_len, merged_waveform.shape[-1], current_clip.shape[-1])
            
            # If the clips are too short, adjust the fade tensors to match the actual_fade size
            current_fade_out = fade_out[:actual_fade] if actual_fade < fade_len else fade_out
            current_fade_in = fade_in[:actual_fade] if actual_fade < fade_len else fade_in
            # -------------------------------

            # Apply fades using the safe 'actual_fade' size
            merged_waveform[:, :, -actual_fade:] *= current_fade_out
            current_clip[:, :, :actual_fade] *= current_fade_in
                    
            merged_waveform = torch.cat([merged_waveform, current_clip], dim=-1)
            

        # 3. Flatten to Batch 1 as we did before
        if merged_waveform.shape[0] > 1:
            merged_waveform = merged_waveform.reshape(1, merged_waveform.shape[1], -1)

        return ({"waveform": merged_waveform, "sample_rate": sample_rate},)
