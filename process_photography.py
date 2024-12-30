import webuiapi
from io import BytesIO

from webuiapi import ControlNetUnit
from fastapi import HTTPException
from PIL import Image
from shared import *
from shared import image_to_base64, generate_template_mask, resize_image
from shared import load_template


def process_template_data(template_index, image_data, template_data):
    """
    Process template data and image data to prepare for control net units.

    Args:
        template_index (int): Index of the template.
        image_data (bytes): Binary image data.
        template_data (bytes): Binary template data.

    Returns:
        tuple: Tuple containing processed image dimensions, transparent image, image mask, and control net units.
    """
    if template_index is not None:
        template_data = load_template(template_index)

    # open and resize the image
    # image = Image.open(BytesIO(image_data))
    image = image_data
    image = resize_image(image)
    transparent_image, image_mask = transparent_and_mask(image)
    x, y = image.size

    # controlnet unit1 default set to following parameters
    controlnet_unit1 = {
        "input_image": image_to_base64(transparent_image),
        "controlnet_type": "SoftEdge",
        "model": "control_v11p_sd15_softedge [a8575a2a]",
        "module": "softedge_pidinet",
        "mask": image_to_base64(image_mask),
        "weight": 1,
        "resize_mode": "Crop and Resize",
        "lowvram": True,
        "processor_res": 512,
        "pixel_perfect": True,
    }

    # if the template data is available update control_unit 1 and add two other controlnet units for template matching.
    if template_data:
        template_image = Image.open(BytesIO(template_data))
        template_image = resize_image(template_image)
        template_image = template_image.resize(image.size)
        template_mask = generate_template_mask(template_image)

        # update controlnet_unit1
        controlnet_unit1.update({
            "guessmode": True,
        })

        controlnet_unit2 = {
            "input_image": image_to_base64(template_image),
            "controlnet_type": "Reference",
            "model": None,
            "module": "reference_only",
            "mask": image_to_base64(template_mask),
            "weight": 2,
            "resize_mode": "Crop and Resize",
            "lowvram": False,
            "processor_res": 512,
            "guidance_start": 0,
            "guidance_end": 1,
            "guessmode": True,
            "pixel_perfect": True,
            "control_mode": "ControlNet is more important"
        }

        controlnet_unit3 = {
            "input_image": image_to_base64(template_image),
            "controlnet_type": "Canny",
            "model": "control_v11p_sd15_canny [d14c016b]",
            "module": "canny",
            "mask": image_to_base64(template_mask),
            "weight": 2,
            "resize_mode": "Crop and Resize",
            "lowvram": False,
            "processor_res": 512,
            "guidance_start": 0,
            "guidance_end": 1,
            "guessmode": True,
            "pixel_perfect": True,
            "control_mode": "ControlNet is more important"
        }

        return x, y, transparent_image, image_mask, controlnet_unit1, controlnet_unit2, controlnet_unit3

    return x, y, transparent_image, image_mask, controlnet_unit1
