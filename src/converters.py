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

    # XML Example:
    # <box label="wheel" occluded="0" xtl="220.67" ytl="213.36" xbr="258.34" ybr="249.50" z_order="0">
    # </box>

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


def convert_polygon(cvat_label: Dict[str, str]) -> sly.Label:
    """Converts a label with "polygon" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"]
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Polygon)

    # XML Example:
    # <polygon label="mirror" points="195.68,191.45;199.91,195.29;196.45,201.06;192.22,199.14" z_order="0">
    # </polygon>

    point_pairs = cvat_label["points"].split(";")
    exterior = []
    for point_pair in point_pairs:
        y, x = point_pair.split(",")
        exterior.append((int(float(x)), int(float(y))))

    sly_label = sly.Label(
        geometry=sly.Polygon(exterior=exterior),
        obj_class=obj_class,
    )

    return sly_label


CONVERT_MAP = {
    "polygon": convert_polygon,
    "box": convert_rectangle,
}
