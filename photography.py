from sympy.parsing.sympy_parser import null
from process_photography import process_template_data
from shared import *
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Response
from io import BytesIO

router = APIRouter()
expected_keys_photography = ["XsGCpFOxHZlCOptSiCNKOgS1sxRMSxy5"]


@router.post("/img2product")
async def img2product(key: str = Form(...),
                      image: UploadFile = File(...),
                      template: UploadFile = File(None),
                      prompt: str = Form(""),
                      template_index: str = Form(None)
                      ):
    """
        Endpoint to process image to product transformation.

        Args:
            key (str): Authentication key.
            image (UploadFile): Uploaded image file.
            template (UploadFile): Template file.
            prompt (str): Prompt for the transformation.
            template_index (int): Index of the template.

        Returns:
            Response: Transformed image response.
    """

    # Check key authentication
    if key is None or key not in expected_keys_photography:
        raise HTTPException(status_code=401, detail="Unauthorized key")

    # Read image and template data
    image_data = await image.read()
    image_data = check_and_upscale_image(image_data)

    template_data = await template.read()

    x, y, transparent_image, image_mask, *controlnet_units = process_template_data(template_index, image_data,
                                                                                   template_data)
    # Set desired model
    desired_model_name = "realisticVisionV60B1_v51VAE"
    check_and_set_model(desired_model_name)

    negative_prompt = ("standalone object, no extraneous objects, solo-item, no clutter, isolated product, "
                       "low quality, blurry, grainy, unrealistic, watermarked, out of focus, bad lighting, "
                       "unrealistic shadows, cropped, dirty, damaged")

    result = api.img2img(
        images=[transparent_image],
        mask_image=image_mask,
        prompt=prompt,
        negative_prompt=negative_prompt if template_index or template else None,
        inpaint_full_res=0,
        inpainting_mask_invert=1,
        inpaint_full_res_padding=32,
        inpainting_fill=0,
        sampler_name="DPM++ 2M Karras",
        steps=20,
        width=x,
        height=y,
        seed=-1,
        cfg_scale=7,
        denoising_strength=0.75,
        mask_blur=4,
        alwayson_scripts={
            "controlnet": {"args": controlnet_units}
        },
    )

    buffered = BytesIO()
    result.image.save(buffered, format="PNG")
    buffered.seek(0)

    return Response(content=buffered.getvalue(), media_type="image/png")
