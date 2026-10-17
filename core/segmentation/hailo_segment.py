import numpy as np
from PIL import Image
from pathlib import Path

from hailo_platform import (
    HEF,
    VDevice,
    InferVStreams,
    ConfigureParams,
    InputVStreamParams,
    OutputVStreamParams
)

from hailo_platform.pyhailort._pyhailort import StreamInterface


HEF_PATH = "models/road_seg.hef"

# flat mask storage
MASK_ROOT = Path("services/masks")


class HailoSegmentor:

    def __init__(self):

        print("🚀 Loading HEF...")
        self.hef = HEF(HEF_PATH)

        print("🚀 Opening Hailo device...")
        self.device = VDevice()

        configure_params = ConfigureParams.create_from_hef(
            self.hef,
            interface=StreamInterface.PCIe
        )

        self.network_group = self.device.configure(
            self.hef,
            configure_params
        )[0]

        self.input_info = self.hef.get_input_vstream_infos()[0]

        self.output_info = self.hef.get_output_vstream_infos()[0]

        self.input_params = InputVStreamParams.make(
            self.network_group
        )

        self.output_params = OutputVStreamParams.make(
            self.network_group
        )

        print("✅ Hailo ready (SAFE MODE)")


    def segment_tile(self, tile_path, city=None):

        try:

            ####################################################
            # LOAD IMAGE
            ####################################################

            img = Image.open(tile_path).convert("RGB")

            if img.size != (512, 512):

                img = img.resize((512, 512))

            img_np = np.expand_dims(
                np.array(img, dtype=np.uint8),
                axis=0
            )

            ####################################################
            # RUN INFERENCE
            ####################################################

            with self.network_group.activate():

                with InferVStreams(
                    self.network_group,
                    self.input_params,
                    self.output_params
                ) as pipeline:

                    results = pipeline.infer({
                        self.input_info.name: img_np
                    })

            ####################################################
            # GET RAW OUTPUT
            ####################################################

            raw = results[self.output_info.name][0]

            ####################################################
            # THRESHOLD MASK
            ####################################################

            mask = (raw > 15).astype(np.uint8)

            if mask.ndim == 3:
                mask = mask.squeeze()

            ####################################################
            # INPUT TILE INFO
            ####################################################

            print("📂 TILE PATH:", tile_path)

            path = Path(tile_path)

            ####################################################
            # CITY NAME
            ####################################################

            city = path.parent.parent.name

            ####################################################
            # OUTPUT FOLDER
            ####################################################

            mask_dir = MASK_ROOT / city / "tiles"

            mask_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            ####################################################
            # OUTPUT FILE
            ####################################################

            output_path = mask_dir / path.name

            ####################################################
            # CREATE TRANSPARENT RGBA MASK
            ####################################################

            rgba = np.zeros(
                (512, 512, 4),
                dtype=np.uint8
            )

            ####################################################
            # ROADS = GREEN
            ####################################################

            rgba[mask > 0] = [0, 255, 0, 180]

            ####################################################
            # SAVE PNG
            ####################################################

            Image.fromarray(
                rgba,
                mode="RGBA"
            ).save(
                output_path,
                compress_level=0
            )

            print("✅ MASK SAVED:", output_path)

        except Exception as e:

            print("❌ SEGMENT ERROR:", e)
