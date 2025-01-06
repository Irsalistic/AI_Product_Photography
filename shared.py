import webuiapi
import io
from io import BytesIO
import base64
import requests
import os
from PIL import Image
from fastapi import APIRouter, HTTPException, UploadFile, Form, File, Request, Response
from rembg import remove
from webuiapi import Upscaler

from process_photography import *

api = webuiapi.WebUIApi()

base_url = "192.168.100.48"

api = webuiapi.WebUIApi(host=base_url, port=7861, sampler='DPM++ 2M Karras', steps=25, use_https=False)

api.set_auth('organization', 'pass')

SDXL_styles = [

    {
        "name": "base",
        "prompt": "{prompt}",
        "negative_prompt": ""
    },
    {
        "name": "3D Model",
        "prompt": "professional 3d model {prompt} . octane render, highly detailed, volumetric, dramatic lighting",
        "negative_prompt": "ugly, deformed, noisy, low poly, blurry, painting"
    },

    {
        "name": "Anime",
        "prompt": "anime artwork {prompt} . anime style, key visual, vibrant, studio anime,  highly detailed",
        "negative_prompt": "photo, deformed, black and white, realism, disfigured, low contrast"
    },
    {
        "name": "Enhance",
        "prompt": "breathtaking {prompt} . award-winning, professional, highly detailed",
        "negative_prompt": "ugly, deformed, noisy, blurry, distorted, grainy"
    },
    {
        "name": "Fantasy Art",
        "prompt": "ethereal fantasy concept art of  {prompt} . magnificent, celestial, ethereal, painterly, epic, majestic, magical, fantasy art, cover art, dreamy",
        "negative_prompt": "photographic, realistic, realism, 35mm film, dslr, cropped, frame, text, deformed, glitch, noise, noisy, off-center, deformed, cross-eyed, closed eyes, bad anatomy, ugly, disfigured, sloppy, duplicate, mutated, black and white"
    },
    {
        "name": "Watercolor",
        "prompt": "Watercolor painting {prompt} . Vibrant, beautiful, painterly, detailed, textural, artistic",
        "negative_prompt": "anime, photorealistic, 35mm film, deformed, glitch, low contrast, noisy"
    }
]


def check_and_set_model(desired_model):
    # Save the current model name
    old_model = api.util_get_current_model()

    # Get the list of available models
    models = api.util_get_model_names()
    models = [info.split('.')[0] for info in models]
    old_model = old_model.split('.')[0]

    # Check if the current model matches the desired model
    if old_model == desired_model:
        print(f"Current model '{old_model}' matches the desired model '{desired_model}'. Good to go!")
    else:
        # Check if the desired model exists in the available models
        if desired_model in models:
            # Set the model to the desired model
            api.util_set_model(desired_model)
            print(f"Model has been set to the desired model '{desired_model}'.")
        else:
            print(
                f"Desired model '{desired_model}' is not available. Please choose from the following models: {models}")


max_dimension = 976


def resize_to_max_dimension(width, height):
    """
    Resizes the width and height while maintaining the aspect ratio,
    ensuring that neither dimension exceeds the specified maximum dimension.
    """
    aspect_ratio = width / height
    if width > height:
        new_width = min(width, max_dimension)
        new_height = new_width / aspect_ratio
    else:
        new_height = min(height, max_dimension)
        new_width = new_height * aspect_ratio
    return int(new_width), int(new_height)


def resize_image(image):
    if isinstance(image, Image.Image):
        # If image is already opened, convert it to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        image_bytes = image_bytes.read()
    else:
        # If image is in bytes format, use it directly
        image_bytes = image

    # Get original dimensions
    original_image = Image.open(io.BytesIO(image_bytes))
    original_width, original_height = original_image.size

    # Resize the image
    new_width, new_height = resize_to_max_dimension(original_width, original_height)
    resized_img = original_image.resize((new_width, new_height), Image.LANCZOS)

    return resized_img


def load_template(template_index):
    # Check if template_index is provided
    if template_index is not None:
        # Split template_index into category and image number
        category, img_number = template_index.split("_")
        img_number = int(img_number)

        # Define the base directory for static images
        base_dir = 'static/backgrounds/'

        # Get all files in the category directory
        category_dir = os.path.join(base_dir, category)
        if os.path.exists(category_dir):
            files = os.listdir(category_dir)

            # Search for a file with the given image number
            for file_name in files:
                if file_name.startswith(str(img_number)):
                    # Construct the full path to the image file
                    template_filename = os.path.join(category_dir, file_name)

                    # Read and return the template data from file
                    with open(template_filename, "rb") as template_file:
                        template_data = template_file.read()
                    return template_data

            # If no file with the given image number is found
            raise HTTPException(status_code=400, detail="Image not found")
        else:
            raise HTTPException(status_code=400, detail="Category directory not found")
    else:
        raise HTTPException(status_code=400, detail="Template index not provided")


def check_and_upscale_image(image_data, max_image_size_mb=1):
    # Open the image from bytes
    image = Image.open(BytesIO(image_data))

    # Get the size of the image data in megabytes
    image_size_mb = len(image_data) / (1024 * 1024)

    # Check if the image size is less than the maximum allowed size
    if image_size_mb < max_image_size_mb:
        print("upscalling...")
        try:
            # Upscale the image using webuiapi
            upscaled_image = api.extra_single_image(image=image,
                                                    upscaler_1=Upscaler.ESRGAN_4x,
                                                    upscaling_resize=1.5)
            return upscaled_image.image
        except Exception as e:
            print(f"Error during upscaling: {e}")
            # Return the original image data if upscaling fails
            return image_data
    else:
        # Return the original image data if it's already larger than the maximum size
        return image_data


def transparent_and_mask(image):
    # removing background
    transparent_image = remove(image)
    transparent_image = transparent_image.convert("RGBA")

    # Invert the alpha channel
    alpha = transparent_image.split()[3]
    inverted_alpha = Image.eval(alpha, lambda x: 255 - x)

    # Create a new image with white background and transparent object
    image_mask = Image.new("RGBA", transparent_image.size, (255, 255, 255, 255))  # White background

    # Paste the object (transparent) using inverted alpha as the mask
    image_mask.paste((255, 255, 255, 0), mask=inverted_alpha)

    return transparent_image, image_mask


# Generate white mask based on the dimension of the image
def generate_template_mask(input_image):
    width, height = input_image.size
    white_image = Image.new("RGB", (width, height), "white")
    return white_image


def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')
