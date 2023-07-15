import json

from krita import Krita
from PyQt5.QtCore import QBuffer, QByteArray, QSize
from PyQt5.QtGui import QColor, QImage, QPainter

MAX_UINT = 4294967295
NO_TEXTURE = MAX_UINT

META_VERSION = "v0.7.2-97-gc2aaa18"
DEFAULT_PHYSICS = {"pixelsPerMeter": 1000.0, "gravity": 9.8}
DEFAULT_UVS = [0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0]
DEFAULT_INDICES = [0, 1, 2, 2, 1, 3]
DEFAULT_TINT = [1.0, 1.0, 1.0]
DEFAULT_SCREEN_TINT = [0.0, 0.0, 0.0]

BLEND_MODES = {
    "pass through": "PassThrough",
    "normal": "Normal",
    "dissolve": "Dissolve",
    "darken": "Darken",
    "multiply": "Multiply",
    "burn": "ColorBurn",
    "linear_burn": "LinearBurn",
    "darker color": "DarkerColor",
    "lighter color": "Lighten",
    "screen": "Screen",
    "dodge": "ColorDodge",
    "linear_dodge": "LinearDodge",
    "lighter color": "LighterColor",
    "overlay": "Overlay",
    "soft_light": "SoftLight",
    "hard_light": "HardLight",
    "vivid_light": "VividLight",
    "linear light": "LinearLight",
    "pin_light": "PinLight",
    "hard mix": "HardMix",
    "diff": "Difference",
    "exclusion": "Exclusion",
    "subtract": "Subtract",
    "divide": "Divide",
    "hue": "Hue",
    "saturation": "Saturation",
    "color": "Color",
    "luminize": "Luminosity",
}


class Meta:
    def __init__(self):
        self.name = ""
        self.version = META_VERSION
        self.rigger = ""
        self.artist = ""
        self.rights = None
        self.copyright = ""
        self.licenseURL = ""
        self.contact = ""
        self.reference = ""
        self.thumbailId = NO_TEXTURE
        self.preservePixels = False


class INXDocument:
    puppet = {
        "meta": {},
        "physics": DEFAULT_PHYSICS,
        "nodes": {
            "uuid": MAX_UINT - 1,
            "name": "Root",
            "type": "Node",
            "enabled": True,
            "zsort": 0.0,
            "transform": {
                "trans": [0.0, 0.0, 0.0],
                "rot": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0],
            },
            "lockToRoot": False,
            "children": [],
        },
        "param": None,
        "automation": None,
        "animations": None,
        "groups": [],
    }

    def __init__(self, krita_document, meta=Meta()):
        self.doc_center_x = krita_document.width() / 2
        self.doc_center_y = krita_document.height() / 2
        self.nodes = krita_document.topLevelNodes()
        self.meta = meta

    def save(self, inx_filename):
        def __serialize_node_part(node, index):
            bounds = node.bounds()
            [x, y, width, height] = (
                bounds.x(),
                bounds.y(),
                bounds.width(),
                bounds.height(),
            )
            cut_w = width / 2
            cut_h = height / 2

            verts = [-(cut_w), -(cut_h), -(cut_w), cut_h, cut_w, -(cut_h), cut_w, cut_h]

            trans = [
                (x + cut_w) - self.doc_center_x,
                (y + cut_h) - self.doc_center_y,
                0.0,
            ]

            return {
                "uuid": (MAX_UINT - 2) - index,
                "name": node.name(),
                "type": "Part",
                "enabled": True,
                "zsort": 0.0,
                "transform": {
                    "trans": trans,
                    "rot": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0],
                },
                "lockToRoot": False,
                "mesh": {
                    "verts": verts,
                    "uvs": DEFAULT_UVS,
                    "indices": DEFAULT_INDICES,
                },
                "textures": [index, MAX_UINT, MAX_UINT],
                "blend_mode": BLEND_MODES[node.blendingMode()],
                "tint": DEFAULT_TINT,
                "screenTint": DEFAULT_SCREEN_TINT,
                "emissionStrength": 1.0,
                "mask_threshold": 0.5,
                "opacity": node.opacity() / 255.0,
            }

        self.puppet["nodes"]["children"] = [
            __serialize_node_part(node, i) for i, node in enumerate(self.nodes)
        ]

        self.puppet["meta"] = self.meta.__dict__

        SRGB_PROFILE = "sRGB-elle-V2-srgbtrc.icc"
        PNG_TEXTURE_ENCODING = 0

        with open(inx_filename, "wb") as inx_text_io:
            json_data = json.dumps(self.puppet)
            json_payload_length = len(json_data)
            amount_of_textures = len(self.nodes)

            inx_text_io.seek(0)
            inx_text_io.write("TRNSRTS\0".encode())  # magic bytes
            inx_text_io.write(json_payload_length.to_bytes(4, "big"))
            inx_text_io.write(json_data.encode())
            inx_text_io.write("TEX_SECT".encode())  # texture section header
            inx_text_io.write(amount_of_textures.to_bytes(4, "big"))

            for node in self.nodes:
                bounds = node.bounds()
                [x, y, width, height] = (
                    bounds.x(),
                    bounds.y(),
                    bounds.width(),
                    bounds.height(),
                )

                is_srgb = (
                    node.colorModel() == "RGBA"
                    and node.colorDepth() == "U8"
                    and node.colorProfile().lower() == SRGB_PROFILE.lower()
                )

                if not is_srgb:
                    node.setColorSpace("RGBA", "U8", SRGB_PROFILE)

                pixel_data = node.projectionPixelData(x, y, width, height).data()

                """ Premultiplied. VERY SLOW
                premultipled = bytearray(pixel_data)
                for i in range(0, len(b_data), 4):
                    premultipled[i+2] = (b_data[i+2] * b_data[i+3]) // 255
                    premultipled[i+1] = (b_data[i+1] * b_data[i+3]) // 255
                    premultipled[i+0] = (b_data[i+0] * b_data[i+3]) // 255
                pixel_data = premultipled
                """

                image = QImage(pixel_data, width, height, QImage.Format_ARGB32)
                # Premulplied
                image.convertTo(QImage.Format_ARGB32_Premultiplied)

                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                image.save(buffer, "PNG")

                buffer.seek(0)

                inx_text_io.write((buffer.size()).to_bytes(4, "big"))
                inx_text_io.write(PNG_TEXTURE_ENCODING.to_bytes(1, "big"))
                inx_text_io.write(buffer.data())
