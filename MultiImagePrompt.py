import hashlib
import os
import numpy as np
import torch
from PIL import Image, ImageOps
import folder_paths


class TKMultiImagePrompt:
    """
    Upload up to 4 images, each paired with its own prompt text box.
    Collects everything into a SINGLE output instead of 8 separate outputs:

        TK_IMAGE_PROMPT_LIST -> [
            {"image": IMAGE_tensor, "prompt": str, "filename": str, "slot": int},
            ...
        ]

    Empty/unfilled slots are skipped in the output (list length == number of
    slots actually filled, not always 4).
    """

    NUM_SLOTS = 4

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
        ]
        files = sorted(files)

        required = {}
        for i in range(1, cls.NUM_SLOTS + 1):
            # "" is a valid empty selection so slots can be left unfilled.
            # No "image_upload" flag here on purpose: that flag triggers
            # ComfyUI's own built-in upload-widget extension, which would add
            # a second, native upload button on top of our custom JS row.
            # We handle uploading ourselves in the JS extension instead.
            required[f"image_{i}"] = ([""] + files, {})
            required[f"prompt_{i}"] = ("STRING", {"multiline": True, "default": ""})

        return {"required": required}

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

    def collect(self, **kwargs):
        results = []
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
    def IS_CHANGED(cls, **kwargs):
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
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        for i in range(1, cls.NUM_SLOTS + 1):
            image_name = kwargs.get(f"image_{i}")
            if image_name and not folder_paths.exists_annotated_filepath(image_name):
                return f"Invalid image file for slot {i}: {image_name}"
        return True



