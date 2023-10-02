import cv2
import os
import numpy as np

from typing import Dict, List, Optional, Tuple, Union, Literal
from collections import namedtuple, defaultdict

import supervisely as sly
import xml.etree.ElementTree as ET

from supervisely.geometry.graph import KeypointsTemplate
from supervisely.geometry.point_location import PointLocation
from supervisely.geometry.cuboid import CuboidFace

# from converters import convert_tag, CONVERT_MAP

ImageObject = namedtuple("ImageObject", ["name", "path", "size", "labels", "tags"])


def convert_rectangle(
    cvat_label: Dict[str, str], **kwargs
) -> Union[sly.Label, sly.VideoFigure]:
    """Converts a label with "box" geometry from CVAT format to Supervisely format.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: Supervisely Label or VideoFigure (depending on kwargs)
    :rtype: Union[sly.Label, sly.VideoFigure]
    """
    class_name = cvat_label["label"] + "_rectangle"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Rectangle)

    # XML Example:
    # <box label="wheel" occluded="0" xtl="220.67" ytl="213.36" xbr="258.34" ybr="249.50" z_order="0">
    # </box>

    geometry = sly.Rectangle(
        top=int(float(cvat_label["ytl"])),
        left=int(float(cvat_label["xtl"])),
        bottom=int(float(cvat_label["ybr"])),
        right=int(float(cvat_label["xbr"])),
    )

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        sly_label = sly.VideoFigure(video_object, geometry, frame_idx)
    else:
        sly_label = sly.Label(
            geometry=geometry,
            obj_class=obj_class,
        )

    return sly_label


def convert_polygon(
    cvat_label: Dict[str, str], **kwargs
) -> Union[sly.Label, sly.VideoFigure]:
    """Converts a label with "polygon" geometry from CVAT format to Supervisely format.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: Supervisely Label or VideoFigure (depending on kwargs)
    :rtype: Union[sly.Label, sly.VideoFigure]
    """
    class_name = cvat_label["label"] + "_polygon"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Polygon)

    # XML Example:
    # <polygon label="mirror" points="195.68,191.45;199.91,195.29;196.45,201.06;192.22,199.14" z_order="0">
    # </polygon>

    exterior = extract_points(cvat_label["points"])
    geometry = sly.Polygon(exterior=exterior)

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        sly_label = sly.VideoFigure(video_object, geometry, frame_idx)
    else:
        sly_label = sly.Label(
            geometry=geometry,
            obj_class=obj_class,
        )

    return sly_label


def convert_polyline(
    cvat_label: Dict[str, str], **kwargs
) -> Union[sly.Label, sly.VideoFigure]:
    """Converts a label with "polyline" geometry from CVAT format to Supervisely format.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: Supervisely Label or VideoFigure (depending on kwargs)
    :rtype: Union[sly.Label, sly.VideoFigure]
    """
    class_name = cvat_label["label"] + "_polyline"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Polyline)

    # XML Example:
    # <polyline label="ear" occluded="0" points="527.11,207.00;593.38,182.53;677.99,188.65;698.38,216.17" z_order="0">
    # </polyline>

    exterior = extract_points(cvat_label["points"])
    geometry = sly.Polyline(exterior=exterior)

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        sly_label = sly.VideoFigure(video_object, geometry, frame_idx)
    else:
        sly_label = sly.Label(
            geometry=sly.Polyline(exterior=exterior),
            obj_class=obj_class,
        )

    return sly_label


def convert_points(
    cvat_label: Dict[str, str], **kwargs
) -> Union[List[sly.Label], List[sly.VideoFigure]]:
    """Converts a label with "points" geometry from CVAT format to Supervisely format.
    Returns a list of labels, because CVAT "points" geometry can contain multiple points.
    Even if there is only one point, it is still a list.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: list of Supervisely Labels or VideoFigures (depending on kwargs)
    :rtype: Union[List[sly.Label], List[sly.VideoFigure]]
    """
    class_name = cvat_label["label"] + "_point"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Point)

    # XML Example:
    # <points label="ear" occluded="0" points="221.27,536.29;238.60,544.44;257.97,547.50;" z_order="0">
    # </points>

    points = extract_points(cvat_label["points"])
    sly_labels = []

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        for point in points:
            sly_label = sly.VideoFigure(
                video_object, sly.Point(row=point[0], col=point[1]), frame_idx
            )
            sly_labels.append(sly_label)
    else:
        for point in points:
            sly_label = sly.Label(
                geometry=sly.Point(row=point[0], col=point[1]),
                obj_class=obj_class,
            )
            sly_labels.append(sly_label)

    return sly_labels


def convert_cuboid(cvat_label: Dict[str, str], **kwargs) -> sly.Label:
    """NOTE: This function is not implemented yet.
    Converts a label with "cuboid" geometry from CVAT format to Supervisely format.

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: label in Supervisely format
    :rtype: sly.Label
    """
    class_name = cvat_label["label"] + "_cuboid"
    obj_class = sly.ObjClass(name=class_name, geometry_type=sly.Cuboid)

    # XML Example:
    # <cuboid label="ear" occluded="0" xtl1="609.02" ytl1="440.04" xbl1="609.02" ybl1="487.05"
    #                                  xtr1="658.46" ytr1="440.03" xbr1="658.46" ybr1="487.05"
    #                                  xtl2="695.71" ytl2="418.16" xbl2="695.71" ybl2="465.14"
    #                                  xtr2="646.30" ytr2="418.17" xbr2="646.30" ybr2="465.15" z_order="0">
    # </cuboid>

    # Supervisely cuboid coordinate system to CVAT cuboid coordinate system:
    #
    # *          4-------5      POINT 0: top left front           (ytl1, xtl1)
    # *         /|      /|      POINT 1: top right front          (ytr1, xtr1)
    # *        / |     / |      POINT 2: bottom right front       (ybr1, xbr1)
    # *       0-------1  |      POINT 3: bottom left front        (ybl1, xbl1)
    # *       |  7----|--6      POINT 4: top left back            (ytl2, xtl2)
    # *       | /     | /       POINT 5: top right back           (ytr2, xtr2)
    # *       |/      |/        POINT 6: bottom right back        (ybr2, xbr2)
    # *       3-------2         POINT 7: bottom left back         (ybl2, xbl2)
    #                           NOTE: POINT 7 is not used in Supervisely

    return  # TODO: Remove this line after implementing the function on the API side.
    # NOTE: It also needs Video implementation (as other converters).

    point_keys = [
        ("ytl1", "xtl1"),  # POINT 0
        ("ytr1", "xtr1"),  # POINT 1
        ("ybr1", "xbr1"),  # POINT 2
        ("ybl1", "xbl1"),  # POINT 3
        ("ytl2", "xtl2"),  # POINT 4
        ("ytr2", "xtr2"),  # POINT 5
        ("ybr2", "xbr2"),  # POINT 6
    ]

    # points - an array of points that form the cuboid. There are always 7 points in a cuboid.
    # Each point is presented as an array of X and Y coordinates.
    points = []

    for key in point_keys:
        points.append(
            PointLocation(
                row=int(float(cvat_label[key[0]])),
                col=int(float(cvat_label[key[1]])),
            )
        )

    # faces - an array of faces that indicates how points from the points array are connected.
    # There are always 3 faces in a cuboid.
    faces = [
        CuboidFace(0, 1, 2, 3),
        CuboidFace(0, 4, 5, 1),
        CuboidFace(1, 5, 6, 2),
    ]

    sly_label = sly.Label(
        geometry=sly.Cuboid(points=points, faces=faces),
        obj_class=obj_class,
    )

    return sly_label

    # TODO: Implement this function on the API side.
    # * It looks like the converter works fine, but the API raises error about
    # * faces is not provided, while it's obviously provided and can be accessed
    # * after .to_json() method, where all faces are exist and correct.
    # Example of label.to_json() output:
    #  "faces": [
    #     [
    #         0,
    #         1,
    #         2,
    #         3
    #     ],
    #     [
    #         0,
    #         4,
    #         5,
    #         1
    #     ],
    #     [
    #         1,
    #         5,
    #         6,
    #         2
    #     ]
    # ],
    #
    # The error message from the API:
    # requests.exceptions.HTTPError: 400 Client Error: Bad Request for url:
    # https://dev.supervise.ly/public/api/v3/annotations.bulk.add
    # ({"error":"Field 'faces' not found in Cuboid JSON data.","details":
    # [{"message":"Field 'faces' not found in Cuboid JSON data.","index":0,"entityId":23770819}]})


def convert_mask(
    cvat_label: Dict[str, str], **kwargs
) -> Union[sly.Label, sly.VideoFigure]:
    """Converts a label with "mask" geometry from CVAT format to Supervisely format.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: Supervisely Label or VideoFigure (depending on kwargs)
    :rtype: Union[sly.Label, sly.VideoFigure]
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

    geometry = sly.Bitmap(data=binary_mask)

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        sly_label = sly.VideoFigure(video_object, geometry, frame_idx)
    else:
        sly_label = sly.Label(
            geometry=geometry,
            obj_class=obj_class,
        )

    return sly_label


def convert_skeleton(
    cvat_label: Dict[str, str], **kwargs
) -> Union[sly.Label, sly.VideoFigure]:
    """Converts a label with "skeleton" geometry from CVAT format to Supervisely format.

    Available kwargs:
        - frame_idx: int, if passed, the label will be converted to VideoFigure

    :param cvat_label: label in CVAT format (from XML parser)
    :type cvat_label: Dict[str, str]
    :return: Supervisely Label or VideoFigure (depending on kwargs)
    :rtype: Union[sly.Label, sly.VideoFigure]
    """

    class_name = cvat_label["label"] + "_graph"

    nodes = kwargs.get("nodes")
    nodes = sorted(nodes, key=lambda node: node.get("label"))

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

    MULTIPLIER = 10

    template = KeypointsTemplate()
    sly_nodes = []
    for idx, node in enumerate(nodes):
        label = node.get("label")
        points = [int(float(point)) for point in node.get("points").split(",")]
        col, row = points
        template.add_point(label=label, row=idx * MULTIPLIER, col=idx * MULTIPLIER)
        sly_nodes.append(sly.Node(label=label, row=row, col=col))

    obj_class = sly.ObjClass(
        name=class_name,
        geometry_type=sly.GraphNodes,
        geometry_config=template,
    )

    geometry = sly.GraphNodes(sly_nodes)

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        video_object = sly.VideoObject(obj_class)
        sly_label = sly.VideoFigure(video_object, geometry, frame_idx)
    else:
        sly_label = sly.Label(geometry=geometry, obj_class=obj_class)

    return sly_label


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


def convert_tag(cvat_tag: Dict[str, str], **kwargs) -> sly.Tag:
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

    frame_idx = kwargs.get("frame_idx")
    if frame_idx is not None:
        sly_tag = sly.VideoTag(tag_meta, frame_range=(frame_idx, frame_idx))
    else:
        sly_tag = sly.Tag(tag_meta)

    return sly_tag


CONVERT_MAP = {
    "box": convert_rectangle,
    "polygon": convert_polygon,
    "polyline": convert_polyline,
    "points": convert_points,
    "cuboid": convert_cuboid,
    "mask": convert_mask,
    "skeleton": convert_skeleton,
}


def convert_video_annotations(
    images_et: List[ET.Element],
    images_paths: List[str],
) -> Tuple[Tuple[int, int], List[sly.VideoFigure], List[sly.VideoTag]]:
    video_frames = []
    video_objects = []
    video_tags = []

    for image_et, image_path in zip(images_et, images_paths):
        video_size, frame_figures, frame_tags = convert_labels(
            image_et, image_path, "video"
        )
        frame_idx = int(image_et.attrib["id"])
        video_frames.append(sly.Frame(frame_idx, figures=frame_figures))
        video_tags.extend(frame_tags)

        for figure in frame_figures:
            video_object = figure.video_object
            if video_object not in video_objects:
                video_objects.append(video_object)

    return video_size, video_frames, video_objects, video_tags


def convert_images_annotations(
    images_et: List[ET.Element],
    images_paths: List[str],
) -> Tuple[Dict[str, List[sly.Tag]], List[ImageObject]]:
    task_tags = dict()
    image_objects = []
    for image_et, image_path in zip(images_et, images_paths):
        image_name = image_et.attrib["name"]
        image_size, image_labels, image_tags = convert_labels(
            image_et, image_name, "imageset"
        )
        task_tags[image_name] = image_tags
        image_objects.append(
            ImageObject(
                name=image_name,
                path=image_path,
                size=image_size or image_size_from_file(image_path),
                labels=image_labels,
                tags=image_tags,
            )
        )

    return task_tags, image_objects


def prepare_images_for_upload(
    api: sly.Api,
    images_objects: List[ImageObject],
    images_project: sly.ProjectInfo,
    images_project_meta: sly.ProjectMeta,
) -> Tuple[List[str], List[str], List[sly.Annotation]]:
    """Generates lists of images names, paths and annotations from the list of ImageObjects
    for convenient uploading to Supervisely later using upload_paths() function.
    Updates project meta with tags from ImageObjects.

    :param images_objects: list of ImageObjects, each ImageObject contains:
        - name of the image
        - path to the image on the local machine
        - size of the image (height, width) in pixels
        - list of labels in Supervisely format
        - list of tags in Supervisely format

    :param api: Supervisely API object
    :type api: sly.Api
    :type images_objects: List[ImageObject]
    :param images_project: ProjectInfo object for the project in Supervisely where images will be uploaded
    :type images_project: sly.ProjectInfo
    :param images_project_meta: project meta which will be updated with tags from ImageObjects
    :type images_project_meta: sly.ProjectMeta
    :return: list of images names, list of images paths, list of annotations
    :rtype: Tuple[List[str], List[str], List[sly.Annotation]]
    """
    images_names = []
    images_paths = []
    images_anns = []

    for image_object in images_objects:
        images_names.append(image_object.name)
        images_paths.append(image_object.path)

        sly.logger.debug(
            f"Image {image_object.name} has size (height, width): {image_object.size}."
        )

        ann = create_image_annotation(
            image_object.labels,
            image_object.size,
            image_object.name,
        )
        images_anns.append(ann)

        images_project_meta = update_project_meta(
            api,
            images_project_meta,
            images_project.id,
            tags=image_object.tags,
            labels=image_object.labels,
        )

    return images_names, images_paths, images_anns


def images_to_mp4(
    video_path: str, image_paths: List[str], video_size: Tuple[int, int], fps: int = 30
) -> None:
    """Saves the list of images to the video file.
    NOTE: CVAT doesn't store original FPS of the video, so we use 30 FPS by default.

    :param video_path: path, where video will be saved on the local machine
    :type video_path: str
    :param image_paths: list of paths to the images on the local machine
        NOTE: order of the elements in list will be the order of the frames in the video
    :type image_paths: List[str]
    :param video_size: size of the video (height, width) in pixels
        NOTE: (height, width) order IS NOT DEFAULT FOR CV2, it will be reversed in the function
    :type image_size: Tuple[int, int]
    :param fps: frames per second in the result video, defaults to 30
    :type fps: int, optional
    """
    sly.logger.debug(f"Starting to save images to video {video_path}...")
    sly.logger.debug(f"Height, width: {video_size}, fps: {fps}")

    video = cv2.VideoWriter(
        video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        # * CV2 uses (width, height) order for video size, while Supervisely uses (height, width).
        video_size[::-1],
    )

    sly.logger.debug(f"Adding {len(image_paths)} images to the video...")

    for image_path in image_paths:
        image_path = f"{image_path}.PNG"
        image = cv2.imread(image_path)
        video.write(image)
    video.release()

    # * Check if the video file is not corrupted for logging and debugging purposes.
    # Can be safely removed.
    file_size = round(os.path.getsize(video_path) / 1024 / 1024, 3)
    if file_size == 0:
        sly.logger.warning(f"Video {video_path} has size 0 MB, it may be corrupted.")

    sly.logger.debug(f"Finished saving video, result size: {file_size} MB.")


def convert_labels(
    image_et: ET.Element, image_name: str, data_type: Literal["imageset", "video"]
) -> Union[
    Tuple[Tuple[int, int], List[sly.Label], List[sly.Tag]],
    Tuple[Tuple[int, int], List[sly.VideoFigure], List[sly.VideoTag]],
]:
    """Converts CVAT annotations to Supervisely format both for images and videos
    using cobvert map with specific convert functions for each geometry.
    Returns different objects depending on the data type:
    for "imageset" - Sly.Labels and Sly.Tags
    for "video" - Sly.VideoFigures and Sly.VideoTags

    :param image_et: image data parsed from CVAT XML annotation
    :type image_et: ET.Element
    :param image_name: name of the image
    :type image_name: str
    :param data_type: type of the task, possible values: "imageset", "video"
    :type data_type: Literal["imageset", "video"]
    :return: size of the image or video (height, width), list of labels or video figures, list of tags or video tags
    :rtype: Union[
        Tuple[Tuple[int, int], List[sly.Label], List[sly.Tag]],
        Tuple[Tuple[int, int], List[sly.VideoFigure], List[sly.VideoTag]],
        ]
    """
    image_height = int(image_et.attrib["height"])
    image_width = int(image_et.attrib["width"])
    image_size = (image_height, image_width)

    if data_type == "video":
        # * If data type is video, we need to get frame index from the image.
        frame_idx = image_et.attrib.get("id")
        if frame_idx is not None:
            frame_idx = int(frame_idx)
    else:
        # Otherwise we set frame index to None and don't use it.
        # * This is important because convert functions will handle data
        # * as video if frame index is not None.
        frame_idx = None

    cvat_tags = image_et.findall("tag") or []

    if cvat_tags:
        sly.logger.debug(f"Found {len(cvat_tags)} tags in {image_name}.")

    sly_tags = []
    for cvat_tag in cvat_tags:
        sly_tag = convert_tag(cvat_tag.attrib, frame_idx=frame_idx)
        sly_tags.append(sly_tag)

        sly.logger.debug(f"Adding converted sly tag to the list of {image_name}.")

    geometries = list(CONVERT_MAP.keys())
    sly_labels = []
    for geometry in geometries:
        cvat_labels = image_et.findall(geometry) or []

        if cvat_labels:
            sly.logger.debug(
                f"Found {len(cvat_labels)} with {geometry} geometry in {image_name}."
            )

        for cvat_label in cvat_labels:
            # * Nodes variable only exists for points geometry.
            nodes = cvat_label.findall("points") or []
            sly_label = CONVERT_MAP[geometry](
                cvat_label.attrib,
                image_height=image_height,
                image_width=image_width,
                nodes=nodes,
                frame_idx=frame_idx,
            )

            if isinstance(sly_label, list):
                # * If CVAT label was converted to multiple Supervisely labels (e.g. for points)
                # * we need to extend the list of labels for the image.
                sly_labels.extend(sly_label)
            else:
                # Otherwise we just append the label to the list.
                sly_labels.append(sly_label)
            sly.logger.debug(
                f"Adding converted sly label with geometry {geometry} to the list of {image_name}."
            )

    return image_size, sly_labels, sly_tags


def update_project_meta(
    api: sly.Api,
    project_meta: sly.ProjectMeta,
    project_id: int,
    labels: Optional[List[sly.Label]] = None,
    tags: Optional[Union[List[sly.Tag], List[sly.VideoObject]]] = None,
) -> sly.ProjectMeta:
    """Updates Supervisely projects meta with new labels or tags on instance and returns updated meta.

    :param api: Supervisely API object
    :type api: sly.Api
    :param project_meta: project meta to update
    :type project_meta: sly.ProjectMeta
    :param project_id: project ID in Supervisely
    :type project_id: int
    :param labels: list of Supervisely labels to add to the project meta, defaults to None
    :type labels: Optional[List[sly.Label]], optional
    :param tags: list of Supervisely tags to add to the project meta, defaults to None
    :type tags: Optional[List[sly.Tag]], optional
    :return: updated project meta (or the same if no changes were made)
    :rtype: sly.ProjectMeta
    """

    sly.logger.debug("Update project meta initiated.")

    if labels:
        sly.logger.debug(f"Will update {len(labels)} labels.")
        for label in labels:
            label: Union[sly.Label, sly.VideoObject]
            if label is not None:
                if label.obj_class not in project_meta.obj_classes:
                    sly.logger.debug(
                        f"Object class {label.obj_class.name} not found in project meta, will add it."
                    )
                    project_meta = project_meta.add_obj_class(label.obj_class)
                    api.project.update_meta(project_id, project_meta)
                    sly.logger.debug(
                        f"Object class {label.obj_class.name} added, meta updated on Supervisely."
                    )

    if tags:
        sly.logger.debug(f"Will update {len(tags)} tags.")
        for tag in tags:
            tag: sly.Tag
            if tag.meta not in project_meta.tag_metas:
                sly.logger.debug(
                    f"Tag meta {tag.meta.name} not found in project meta, will add it."
                )
                project_meta = project_meta.add_tag_meta(tag.meta)
                api.project.update_meta(project_id, project_meta)
                sly.logger.debug(
                    f"Tag meta {tag.meta.name} added, meta updated on Supervisely."
                )

    sly.logger.debug("Update project meta finished.")

    return project_meta


def upload_images_task(
    api: sly.Api,
    dataset_name: str,
    sly_project: sly.ProjectInfo,
    image_names: List[str],
    image_paths: List[str],
    anns: List[sly.Annotation],
    sly_tags: Dict[str, List[sly.Tag]],
) -> List[sly.ImageInfo]:
    """Uploads images, annotations and tags to Supervisely by batches.

    :param api: Supervisely API object
    :type api: sly.Api
    :param dataset_name: name of the dataset in Supervisely which will be created
    :type dataset_name: str
    :param sly_project: project in Supervisely where images will be uploaded
    :type sly_project: sly.ProjectInfo
    :param image_names: list of image names
    :type image_names: List[str]
    :param image_paths: list of paths to the images on the local machine
    :type image_paths: List[str]
    :param anns: list of Annotation objects for images
    :type anns: List[sly.Annotation]
    :param sly_tags: dictionary with tags for each image by image name
    :type sly_tags: Dict[str, List[sly.Tag]]
    :return: list of uploaded images as ImageInfo objects
    :rtype: List[sly.ImageInfo]
    """
    sly_dataset = api.dataset.create(
        sly_project.id, dataset_name, change_name_if_conflict=True
    )

    sly.logger.debug(
        f"Created dataset {sly_dataset.name} in project {sly_project.name}."
    )

    sly.logger.info(f"Uploading {len(image_names)} images to Supervisely.")

    for batched_image_names, batched_image_paths, batched_anns in zip(
        sly.batched(image_names), sly.batched(image_paths), sly.batched(anns)
    ):
        uploaded_image_infos = api.image.upload_paths(
            sly_dataset.id, batched_image_names, batched_image_paths
        )

        uploaded_image_ids = [image_info.id for image_info in uploaded_image_infos]

        sly.logger.info(
            f"Uploaded {len(uploaded_image_ids)} images to Supervisely to dataset {sly_dataset.name}."
        )

        api.annotation.upload_anns(uploaded_image_ids, batched_anns)

        sly.logger.info(f"Uploaded {len(batched_anns)} annotations to Supervisely.")

    sly.logger.info(
        f"Finished uploading images and annotations for dataset {sly_dataset.name} to Supervisely."
    )

    if sly_tags:
        sly.logger.debug("There were tags in the current task, will upload them.")
        upload_images_tags(api, uploaded_image_infos, sly_project.id, sly_tags)
    else:
        sly.logger.debug("No tags were found in the current task, nothing to upload.")

    return uploaded_image_infos


def upload_images_tags(
    api: sly.Api,
    uploaded_images: List[sly.ImageInfo],
    sly_project_id: int,
    sly_tags: Dict[str, List[sly.Tag]],
) -> None:
    """Upload tags for the uploaded images to Supervisely.

    :param api: Supervisely API object
    :type api: sly.Api
    :param uploaded_images: list of uploaded images as ImageInfo objects
    :type uploaded_images: List[sly.ImageInfo]
    :param sly_project_id: project ID in Supervisely
    :type sly_project_id: int
    :param sly_tags: dictionary with tags for each image by image name
    :type sly_tags: Dict[str, List[sly.Tag]]
    """
    tag_data_for_upload = defaultdict(list)

    sly.logger.debug(
        f"Started building tags dictionary for {len(uploaded_images)} images."
    )

    for image_info in uploaded_images:
        tags = sly_tags.get(image_info.name)
        if tags:
            for tag in tags:
                tag_data_for_upload[tag.name].append(image_info.id)

    sly.logger.debug(
        f"Prepared dictionary with {len(tag_data_for_upload)} tags. "
        "Starting to upload tags to Supervisely."
    )

    for tag_name, image_ids in tag_data_for_upload.items():
        # * For some reason using local project meta leads to None from sly_id,
        # * which creates an error when uploading tags. So we need to get active
        # * tag meta from API for each tag.
        tag_id = get_tag_meta(api, sly_project_id, tag_name).sly_id
        api.image.add_tag_batch(image_ids, tag_id)

    sly.logger.info("Tags successfully uploaded to Supervisely.")


def get_tag_meta(api: sly.Api, sly_project_id: int, tag_name: str) -> sly.TagMeta:
    """Returns active tag meta from API for the given project ID and tag name.
    Important: this function makes an API call, because local project meta does not contain tag IDs.

    :param api: Supervisely API object
    :type api: sly.Api
    :param sly_project_id: project ID in Supervisely
    :type sly_project_id: int
    :param tag_name: tag name to get meta for
    :type tag_name: str
    :return: tag meta from API
    :rtype: sly.TagMeta
    """
    project_meta = sly.ProjectMeta.from_json(api.project.get_meta(sly_project_id))
    return project_meta.get_tag_meta(tag_name)


def image_size_from_file(image_path: str) -> Tuple[int, int]:
    """Reads the image from the file and returns its size as a tuple (height, width).

    :param image_path: path to the image on the local machine
    :type image_path: str
    :return: size of the image (height, width) in pixels
    :rtype: Tuple[int, int]
    """
    sly.logger.debug(
        f"Can't find images dimension for image {image_path} from annotation, "
        "will read the file image..."
    )
    image_np = sly.image.read(image_path)
    height, width, _ = image_np.shape
    image_size = (height, width)
    del image_np

    return image_size


def create_image_annotation(
    labels: List[sly.Label],
    image_size: Tuple[int, int],
    image_name: str,
) -> sly.Annotation:
    """Creates Supervisely Annotation object for the image from given labels.

    :param labels: list of Supervisely Label objects
    :type labels: List[sly.Label]
    :param image_size: size of the image (height, width)
    :type image_size: Tuple[int, int]
    :param image_name: name of the image
    :type image_name: str
    :return: Supervisely Annotation object
    :rtype: sly.Annotation
    """
    if not labels:
        ann = sly.Annotation(img_size=image_size)
        sly.logger.debug(
            f"Created empty annotation for {image_name}, since no labels were found."
        )
    else:
        # * Remove None values from the list of labels to avoid errors.
        labels = [label for label in labels if label is not None]

        ann = sly.Annotation(img_size=image_size, labels=labels)
        sly.logger.debug(f"Created annotation for {image_name} with labels.")

    return ann
