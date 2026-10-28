import hashlib
import os
import numpy as np
import torch
from PIL import Image, ImageOps
import folder_paths


class TKMultiImagePrompt:
    DESCRIPTION = "Used for purpose of looping thru a collection of Images and Prompts.  Note: you can also chain these if you need more prompts.  Requires for start/end workflow. You will need PromptLooperAdv to process this prompts"

    """
    Upload up to 4 images, each paired with its own prompt text box.
    Collects everything into a SINGLE output instead of 8 separate outputs:

        TK_IMAGE_PROMPT_LIST -> [
            {"image": IMAGE_tensor, "prompt": str, "filename": str, "slot": int},
            ...
        ]

    Empty/unfilled slots are skipped in the output (list length == number of
    slots actually filled, not always 4).

    Optional `image_prompt_list` input lets you chain multiple
    TKMultiImagePrompt nodes together — the incoming list is prepended to
    this node's own selections, so chained nodes accumulate in the order
    they're wired (first node in the chain = first entries in the final list).
    """

    NUM_SLOTS = 4

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        ]
        files = folder_paths.filter_files_content_types(files, ["image"])
        files = sorted(files)

        required = {}
        for i in range(1, cls.NUM_SLOTS + 1):
            # "" is a valid empty selection so slots can be left unfilled.
            # image_upload=True hooks into ComfyUI's built-in upload widget,
            # which also enables drag-and-drop onto this widget.

            required[f"prompt_{i}"] = ("STRING", {"multiline": True, "default": ""})
            required[f"image_{i}"] = ([""] + files, {})

        optional = {
            "image_prompt_list": ("TK_IMAGE_PROMPT_LIST",),
        }

        return {"required": required, "optional": optional}


    CATEGORY = "TKNodes/image"
    RETURN_TYPES = ("TK_IMAGE_PROMPT_LIST",)
    RETURN_NAMES = ("image_prompt_list",)
    FUNCTION = "collect"

    def _load_image(self, filename):
        if not filename:
            return None

        image_path = folder_paths.get_annotated_filepath(filename)
        if not image_path or not os.path.exists(image_path):
            return None

        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        if img.mode == "I":
            img = img.point(lambda px: px * (1 / 255))
        rgb_image = img.convert("RGB")
        rgb_image = np.array(rgb_image).astype(np.float32) / 255.0
        rgb_tensor = torch.from_numpy(rgb_image)[None, ]  # [1, H, W, C]
        return rgb_tensor

    def collect(self, image_prompt_list=None, **kwargs):
        results = []

        # Chained selections from an upstream TKMultiImagePrompt come first
        if image_prompt_list:
            results.extend(image_prompt_list)

        for i in range(1, self.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")
            prompt_text = kwargs.get(f"prompt_{i}", "")

            image_tensor = self._load_image(image_name)
            if image_tensor is None:
                continue  # skip empty slot

            results.append({
                "image": image_tensor,
                "prompt": prompt_text,
                "filename": image_name,
                "slot": i,
            })

        return (results,)

    @classmethod
    def IS_CHANGED(cls, image_prompt_list=None, **kwargs):
        m = hashlib.sha256()
        for i in range(1, cls.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")
            prompt_text = kwargs.get(f"prompt_{i}", "") or ""

            if image_name:
                image_path = folder_paths.get_annotated_filepath(image_name)
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        m.update(f.read())

            m.update(prompt_text.encode("utf-8"))

        # Account for upstream chain changes too, so this node re-runs if
        # an earlier node in the chain changes even though its own
        # slots are unchanged.
        if image_prompt_list:
            m.update(str(len(image_prompt_list)).encode("utf-8"))
            for entry in image_prompt_list:
                m.update((entry.get("filename") or "").encode("utf-8"))
                m.update((entry.get("prompt") or "").encode("utf-8"))

        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        for i in range(1, cls.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")
            if image_name and not folder_paths.exists_annotated_filepath(image_name):
                return f"Invalid image file for slot {i}: {image_name}"
        return True





import torch.nn.functional as F  # add to your imports


class TKMultiImageSelect:
    DESCRIPTION = "Used for purpose of selecting up to 12 images to feed into a Looping workflow. Use PromptLooperAdv to select the desired image. "

    """
    Upload up to 12 images (list length == number of
    slots actually filled, not always 12).
    Also outputs all filled slots as a single IMAGE batch.
    """

    NUM_SLOTS = 12

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        ]
        files = folder_paths.filter_files_content_types(files, ["image"])
        files = sorted(files)

        required = {}
        for i in range(1, cls.NUM_SLOTS + 1):
            # "" is a valid empty selection so slots can be left unfilled.
            required[f"image_{i}"] = ([""] + files, {})
        return {"required": required}

    CATEGORY = "TKNodes/image"
    RETURN_TYPES = ("TK_IMAGE_LIST", "IMAGE")
    RETURN_NAMES = ("image_list", "IMAGES")
    FUNCTION = "collect"

    def _load_image(self, filename):
        if not filename:
            return None

        image_path = folder_paths.get_annotated_filepath(filename)
        if not image_path or not os.path.exists(image_path):
            return None

        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        if img.mode == "I":
            img = img.point(lambda px: px * (1 / 255))
        rgb_image = img.convert("RGB")
        rgb_image = np.array(rgb_image).astype(np.float32) / 255.0
        rgb_tensor = torch.from_numpy(rgb_image)[None, ]  # [1, H, W, C]
        return rgb_tensor

    def _make_batch(self, results):
        if not results:
            # Nothing selected: return a tiny blank image rather than erroring
            return torch.zeros((1, 64, 64, 3), dtype=torch.float32)

        tensors = [r["image"] for r in results]
        target_h, target_w = tensors[0].shape[1], tensors[0].shape[2]

        resized = []
        for t in tensors:
            if t.shape[1] != target_h or t.shape[2] != target_w:
                # [1,H,W,C] -> [1,C,H,W] -> resize -> back
                t = t.permute(0, 3, 1, 2)
                t = F.interpolate(
                    t, size=(target_h, target_w),
                    mode="bilinear", align_corners=False,
                )
                t = t.permute(0, 2, 3, 1).clamp(0.0, 1.0)
            resized.append(t)

        return torch.cat(resized, dim=0)  # [N, H, W, C]

    def collect(self, **kwargs):
        results = []
        for i in range(1, self.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")

            image_tensor = self._load_image(image_name)
            if image_tensor is None:
                continue  # skip empty slot

            results.append({
                "image": image_tensor,
                "filename": image_name,
                "slot": i,
            })

        batch = self._make_batch(results)
        return (results, batch)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        m = hashlib.sha256()
        for i in range(1, cls.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")

            if image_name:
                image_path = folder_paths.get_annotated_filepath(image_name)
                if image_path and os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        m.update(f.read())

        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        for i in range(1, cls.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")
            if image_name and not folder_paths.exists_annotated_filepath(image_name):
                return f"Invalid image file for slot {i}: {image_name}"
        return True




class TKMultiPrompt:
    DESCRIPTION = "Used for purpose of looping thru a collection of Prompts.  See also, TKMultiImagePrompt, and TKMultiImageSelect for similar features.  "

    """
         Allows you to set up multiple prompts, this can then be used together with TKMultiImageSelect to randomize prompts for images
    """

    NUM_SLOTS = 4

    @classmethod
    def INPUT_TYPES(cls):

        required = {}
        for i in range(1, cls.NUM_SLOTS + 1):
            required[f"prompt_{i}"] = ("STRING", {"multiline": True, "default": ""})

        optional = {
            "prompt_list": ("TK_PROMPT_LIST",),
        }

        return {"required": required, "optional": optional}


    CATEGORY = "TKNodes/prompt"
    RETURN_TYPES = ("TK_PROMPT_LIST",)
    RETURN_NAMES = ("prompt_list",)
    FUNCTION = "collect"

    def collect(self, prompt_list=None, **kwargs):
        results = []

        if prompt_list:
            results.extend(prompt_list)

        for i in range(1, self.NUM_SLOTS + 1):
            prompt_text = kwargs.get(f"prompt_{i}", "")


            results.append({
                "prompt": prompt_text,
                "slot": i,
            })

        return (results,)

    @classmethod
    def IS_CHANGED(cls, prompt_list=None, **kwargs):
        m = hashlib.sha256()
        for i in range(1, cls.NUM_SLOTS + 1):
            prompt_text = kwargs.get(f"prompt_{i}", "") or ""

            m.update(prompt_text.encode("utf-8"))

        # Account for upstream chain changes too, so this node re-runs if
        # an earlier node in the chain changes even though its own
        # slots are unchanged.
        if prompt_list:
            m.update(str(len(prompt_list)).encode("utf-8"))
            for entry in prompt_list:
                m.update((entry.get("prompt") or "").encode("utf-8"))

        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

