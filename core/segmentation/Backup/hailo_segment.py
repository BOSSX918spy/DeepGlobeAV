import numpy as np
from PIL import Image
from pathlib import Path
from datetime import datetime

from hailo_platform import (
    HEF, VDevice, InferVStreams, ConfigureParams,
    InputVStreamParams, OutputVStreamParams
)
from hailo_platform.pyhailort._pyhailort import StreamInterface

HEF_PATH = "models/road_seg.hef"
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

        self.network_group = self.device.configure(self.hef, configure_params)[0]

        self.input_info = self.hef.get_input_vstream_infos()[0]
        self.output_info = self.hef.get_output_vstream_infos()[0]

        self.input_params = InputVStreamParams.make(self.network_group)
        self.output_params = OutputVStreamParams.make(self.network_group)

        print("✅ Hailo ready (SAFE MODE)")

    def segment_tile(self, tile_path, city=None):
        try:
            img = Image.open(tile_path).convert("RGB")

            if img.size != (512, 512):
                img = img.resize((512, 512))

            img_np = np.expand_dims(np.array(img, dtype=np.uint8), axis=0)

            with self.network_group.activate():
                with InferVStreams(
                    self.network_group,
                    self.input_params,
                    self.output_params
                ) as pipeline:

                    results = pipeline.infer({
                        self.input_info.name: img_np
                    })

            raw = results[self.output_info.name][0]

            mask = (raw > 15).astype(np.uint8)

            if mask.ndim == 3:
                mask = mask.squeeze()

            city = Path(tile_path).parts[-3]

            base = Path(tile_path).stem
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            npy_dir = MASK_ROOT / city / "npy"
            png_dir = MASK_ROOT / city / "png"

            npy_dir.mkdir(parents=True, exist_ok=True)
            png_dir.mkdir(parents=True, exist_ok=True)

            np.save(npy_dir / f"{base}_{timestamp}.npy", mask)

            Image.fromarray(
                (mask * 255).astype(np.uint8),
                mode="L"
            ).save(png_dir / f"{base}_{timestamp}.png", compress_level=0)

        except Exception as e:
            print("❌ SEGMENT ERROR:", e)
