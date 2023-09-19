from typing import Dict, List, Tuple

import numpy as np
import supervisely as sly

from supervisely.geometry.graph import Node, KeypointsTemplate

# * Imports for sly.Cuboid
# from supervisely.geometry.point_location import PointLocation
# from supervisely.geometry.cuboid import CuboidFace


def convert_rectangle(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """Converts a label with "box" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"] + "_rectangle"
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


def convert_polygon(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """Converts a label with "polygon" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"] + "_polygon"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Polygon)

    # XML Example:
    # <polygon label="mirror" points="195.68,191.45;199.91,195.29;196.45,201.06;192.22,199.14" z_order="0">
    # </polygon>

    exterior = extract_points(cvat_label["points"])

    sly_label = sly.Label(
        geometry=sly.Polygon(exterior=exterior),
        obj_class=obj_class,
    )

    return sly_label


def convert_polyline(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """Converts a label with "polyline" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"] + "_polyline"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Polyline)

    # XML Example:
    # <polyline label="ear" occluded="0" points="527.11,207.00;593.38,182.53;677.99,188.65;698.38,216.17" z_order="0">
    # </polyline>

    exterior = extract_points(cvat_label["points"])

    sly_label = sly.Label(
        geometry=sly.Polyline(exterior=exterior),
        obj_class=obj_class,
    )

    return sly_label


def convert_points(cvat_label: Dict[str, str], **kwargs) -> List[sly.Label]:
    """Converts a label with "points" geometry from CVAT format to Supervisely format.
    Returns a list of labels, because CVAT "points" geometry can contain multiple points.
    Even if there is only one point, it is still a list.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: list of labels in Supervisely format
    :rtype: List[sly.Label]
    """
    class_name = cvat_label["label"] + "_point"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Point)

    # XML Example:
    # <points label="ear" occluded="0" points="221.27,536.29;238.60,544.44;257.97,547.50;" z_order="0">
    # </points>

    points = extract_points(cvat_label["points"])
    sly_labels = []

    for point in points:
        sly_label = sly.Label(
            geometry=sly.Point(row=point[0], col=point[1]),
            obj_class=obj_class,
        )
        sly_labels.append(sly_label)

    return sly_labels


def convert_cuboid(cvat_label: Dict[str, str]) -> sly.Label:
    """NOTE: This function is not implemented yet.
    Converts a label with "cuboid" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :raises NotImplementedError: the function is not implemented yet
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    # class_name = cvat_label["label"] + "_cuboid"
    # obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Cuboid)

    # XML Example:
    # <cuboid label="ear" occluded="0" xtl1="609.02" ytl1="440.04" xbl1="609.02" ybl1="487.05"
    #                                  xtr1="658.46" ytr1="440.03" xbr1="658.46" ybr1="487.05"
    #                                  xtl2="695.71" ytl2="418.16" xbl2="695.71" ybl2="465.14"
    #                                  xtr2="646.30" ytr2="418.17" xbr2="646.30" ybr2="465.15" z_order="0">
    # </cuboid>

    raise NotImplementedError(
        "Converting CVAT cuboid to Supervisely cuboid is not implemented yet."
    )


def convert_mask(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """Converts a label with "mask" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"] + "_mask"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Bitmap)

    image_height = kwargs.get("image_height")
    image_width = kwargs.get("image_width")

    if not image_height or not image_width:
        sly.logger.error(
            f"Image height or width is not provided for mask, the label for {cvat_label} will be skipped."
        )
        return

    # XML Example:
    # <mask label="nose" occluded="0" rle="47, 12, 47, 13, 2, 18, 39, 40, 30, 49, 25, 53, 20, 58, 16"
    #                                 left="955" top="409" width="77" height="58" z_order="0">
    # </mask>

    rle_values = [int(value.strip()) for value in cvat_label["rle"].split(",")]
    ann_left = int(cvat_label["left"])
    ann_top = int(cvat_label["top"])
    ann_width = int(cvat_label["width"])

    binary_mask = cvat_rle_to_binary_mask(
        rle_values, ann_left, ann_top, ann_width, image_height, image_width
    )

    sly_label = sly.Label(
        geometry=sly.Bitmap(data=binary_mask),
        obj_class=obj_class,
    )

    return sly_label


def convert_skeleton(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """Converts a label with "skeleton" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """

    class_name = cvat_label["label"] + "_graph"

    nodes = kwargs.get("nodes")

    if not nodes:
        sly.logger.error(
            f"Points are not provided for skeleton, the label for {cvat_label} will be skipped."
        )
        return

    # XML Example:
    # <skeleton label="person-body" z_order="0">
    #   <points label="neck" outside="0" occluded="0" points="575.91,828.41">
    #   </points>
    #   <points label="chest" outside="0" occluded="0" points="584.93,1032.86">
    #   </points>
    # </skeleton>

    # template = KeypointsTemplate()


def extract_points(points: str) -> List[Tuple[int, int]]:
    """Extracts points from a string in CVAT format after parsing XML.

    :param points: string with points in CVAT format (e.g. "221.27,536.29;238.60,544.44;257.97,547.50;")
    :type points: str
    :return: list of points in Supervisely format (e.g. [(536, 221), (544, 238), (547, 257)])
    :rtype: List[Tuple[int, int]]
    """
    point_pairs = points.split(";")
    coordinates = []
    for point_pair in point_pairs:
        y, x = point_pair.split(",")
        coordinates.append((int(float(x)), int(float(y))))
    return coordinates


def cvat_rle_to_binary_mask(
    rle_values: List[int],
    ann_left: int,
    ann_top: int,
    ann_width: int,
    image_height: int,
    image_width: int,
) -> np.ndarray:
    """_summary_

    :param rle_values: list of CVAT RLE values (from XML parser)
    :type rle_values: List[int]
    :param ann_left: left coordinate of the CVAT mask annotation
    :type ann_left: int
    :param ann_top: top coordinate of the CVAT mask annotation
    :type ann_top: int
    :param ann_width: width of the CVAT mask annotation
    :type ann_width: int
    :param image_height: height of the image
    :type image_height: int
    :param image_width: width of the image
    :type image_width: int
    :return: binary image mask to be used in Supervisely format
    :rtype: np.ndarray
    """
    mask = np.zeros((image_height, image_width), dtype=np.uint8)
    value = 0
    offset = 0
    for rle_count in rle_values:
        while rle_count > 0:
            y, x = divmod(offset, ann_width)
            mask[y + ann_top][x + ann_left] = value
            rle_count -= 1
            offset += 1
        value = 1 - value

    return mask


def convert_tag(cvat_tag: Dict[str, str]) -> sly.Tag:
    """Converts a tag from CVAT format to Supervisely format.

    :param cvat_tag: tag in CVAT format (from XML parser)
    :type cvat_tag: Dict[str, str]
    :return: tag in Supervisely format
    :rtype: sly.Tag
    """
    # XML Example:
    # <tag label="woman" source="manual">
    # </tag>

    tag_name = cvat_tag["label"]
    tag_meta = sly.TagMeta(tag_name, value_type=sly.TagValueType.NONE)
    sly_tag = sly.Tag(tag_meta)

    return sly_tag


CONVERT_MAP = {
    "box": convert_rectangle,
    "polygon": convert_polygon,
    "polyline": convert_polyline,
    "points": convert_points,
    # "cuboid": convert_cuboid, # ! Do not uncomment this line until the function is implemented.
    "mask": convert_mask,
    "skeleton": convert_skeleton,
}
