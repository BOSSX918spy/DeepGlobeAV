import numpy as np
from PIL import Image
import os
import json
from hailo_platform import (
    HEF, VDevice, InferVStreams, ConfigureParams,
    InputVStreamParams, OutputVStreamParams
)
from hailo_platform.pyhailort._pyhailort import StreamInterface

HEF_PATH = "models/road_seg.hef"
MASK_DIR = "services/masks"

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

        print("✅ Hailo ready")

    def segment_tile(self, tile_path):
        img = Image.open(tile_path).convert("RGB").resize((512, 512))
        img_np = np.array(img).astype(np.uint8)
        img_np = np.expand_dims(img_np, axis=0)

        with self.network_group.activate():
            with InferVStreams(self.network_group,
                               self.input_params,
                               self.output_params) as pipeline:

                results = pipeline.infer({self.input_info.name: img_np})

        raw = results[self.output_info.name][0]

        # threshold for roads
        mask = (raw > 15).astype(np.uint8) * 255
        
        

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        json_name = os.path.basename(tile_path).replace(".jpg", f"_{timestamp}.json")
        json_path = os.path.join(MASK_DIR, json_name)

        # convert 255 → 1 (binary)
        mask_binary = (mask > 0).astype(np.uint8)

        data = {
            "shape": mask_binary.shape,
            "mask": mask_binary.tolist()
        }

        with open(json_path, "w") as f:
            json.dump(data, f)

        print("📄 JSON saved:", json_path)
        # save mask
        filename = os.path.basename(tile_path).replace(".jpg", "_mask.png")
        save_path = os.path.join(MASK_DIR, filename)

        Image.fromarray(mask.squeeze()).save(save_path)
        print("🛣 Mask saved:", save_path)

        return save_path
