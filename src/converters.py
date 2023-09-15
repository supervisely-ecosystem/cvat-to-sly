from typing import Dict

import supervisely as sly


def convert_rectangle(cvat_label: Dict[str, str]) -> sly.Label:
    """Converts a label with "box" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"]
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Rectangle)

    sly_label = sly.Label(
        geometry=sly.Rectangle(
            top=int(float(cvat_label["ytl"])),
            left=int(float(cvat_label["xtl"])),
            bottom=int(float(cvat_label["ybr"])),
            right=int(float(cvat_label["xbr"])),
        ),
        obj_class=obj_class,
    )

    return sly_label


CONVERT_MAP = {
    # "polygon": convert_polygon,
    "box": convert_rectangle,
}
