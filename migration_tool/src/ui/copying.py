import os
import cv2
import shutil
import supervisely as sly
from typing import List, Dict, Optional, Tuple, Union, Literal
from collections import defaultdict, namedtuple

from supervisely.app.widgets import (
    Container,
    Card,
    Table,
    Button,
    Progress,
    Text,
    Flexbox,
)
import xml.etree.ElementTree as ET

import migration_tool.src.globals as g
import migration_tool.src.cvat as cvat
import migration_tool.src.converters as converters

ImageObject = namedtuple("ImageObject", ["name", "path", "size", "labels", "tags"])

COLUMNS = [
    "COPYING STATUS",
    "ID",
    "NAME",
    "STATUS",
    "OWNER",
    "LABELS",
    "CVAT URL",
    "SUPERVISELY URL",
]

projects_table = Table(fixed_cols=3, per_page=20, sort_column_id=1)
projects_table.hide()

copy_button = Button("Copy", icon="zmdi zmdi-copy")
stop_button = Button("Stop", icon="zmdi zmdi-stop", button_type="danger")
stop_button.hide()

buttons_flexbox = Flexbox([copy_button, stop_button])

copying_progress = Progress()
good_results = Text(status="success")
bad_results = Text(status="error")
good_results.hide()
bad_results.hide()

card = Card(
    title="3️⃣ Copying",
    description="Copy selected projects from CVAT to Supervisely.",
    content=Container(
        [projects_table, buttons_flexbox, copying_progress, good_results, bad_results]
    ),
    collapsable=True,
)
card.lock()
card.collapse()


def build_projects_table() -> None:
    """Fills the table with projects from CVAT.
    Uses global g.STATE.selected_projects to get the list of projects to show.
    g.STATE.selected_projects is a list of project IDs from CVAT.
    """
    sly.logger.debug("Building projects table...")
    projects_table.loading = True
    rows = []

    for project in cvat.cvat_data():
        if project.id in g.STATE.selected_projects:
            rows.append(
                [
                    g.COPYING_STATUS.waiting,
                    project.id,
                    project.name,
                    project.status,
                    project.owner_username,
                    project.labels_count,
                    f'<a href="{project.url}" target="_blank">{project.url}</a>',
                    "",
                ]
            )

    sly.logger.debug(f"Prepared {len(rows)} rows for the projects table.")

    projects_table.read_json(
        {
            "columns": COLUMNS,
            "data": rows,
        }
    )

    projects_table.loading = False
    projects_table.show()

    sly.logger.debug("Projects table is built.")


@copy_button.click
def start_copying() -> None:
    """Main function for copying projects from CVAT to Supervisely.
    1. Starts copying progress, changes state of widgets in UI.
    2. Iterates over selected projects from CVAT.
    3. For each project:
        3.1. Updates the status in the projects table to "Copying...".
        3.2. Iterates over tasks in the project.
        3.3. For each task:
            3.3.1. Downloads the task data from CVAT API.
            3.3.2. Saves the task data to the zip archive (using up to 10 retries).
        3.4. If the archive is empty after 10 retries, updates the status in the projects table to "Error".
        3.5. Otherwise converts the task data to Supervisely format and uploads it to Supervisely.
        3.6. If the task was uploaded with errors, updates the status in the projects table to "Error".
        3.7. Otherwise updates the status in the projects table to "Copied".
    4. Updates the status in the projects table to "Copied" or "Error" for each project.
    5. Stops copying progress, changes state of widgets in UI.
    6. Shows the results of copying.
    7. Removes content from download and upload directories (if not in development mode).
    8. Stops the application (if not in development mode).
    """
    sly.logger.debug(
        f"Copying button is clicked. Selected projects: {g.STATE.selected_projects}"
    )

    stop_button.show()
    copy_button.text = "Copying..."
    g.STATE.continue_copying = True

    def save_task_to_zip(task_id: int, task_path: str, retry: int = 0) -> bool:
        """Tries to download the task data from CVAT API and save it to the zip archive.
        Functions tries to download the task data 10 times if the archive is empty and
        returns False if it can't download the data after 10 retries. Otherwise returns True.

        :param task_id: task ID in CVAT
        :type task_id: int
        :param task_path: path for saving task data in zip archive
        :type task_path: str
        :param retry: current number of retries, defaults to 0
        :type retry: int, optional
        :return: download status (True if the archive is not empty, False otherwise)
        :rtype: bool
        """
        sly.logger.debug("Trying to retreive task data from API...")
        task_data = cvat.retreive_dataset(task_id=task.id)

        with open(task_path, "wb") as f:
            shutil.copyfileobj(task_data, f)

        sly.logger.debug(f"Saved data to path: {task_path}, will check it's size...")

        # Check if the archive has non-zero size.
        if os.path.getsize(task_path) == 0:
            sly.logger.debug(f"The archive for task {task_id} is empty, removing it...")
            sly.fs.silent_remove(task_path)
            sly.logger.debug(f"The archive with path {task_path} was removed.")
            if retry < 10:
                # Try to download the task data again.
                retry += 1
                sly.logger.info(f"Retry {retry} to download task {task_id}...")
                save_task_to_zip(task_id, task_path, retry)
            else:
                # If the archive is empty after 10 retries, return False.
                sly.logger.error(f"Can't download task {task_id} after 10 retries.")
                return False
        else:
            sly.logger.debug(f"Archive for task {task_id} was downloaded correctly.")
            return True

    succesfully_uploaded = 0
    uploded_with_errors = 0

    with copying_progress(
        total=len(g.STATE.selected_projects), message="Copying..."
    ) as pbar:
        for project_id in g.STATE.selected_projects:
            sly.logger.debug(f"Copying project with id: {project_id}")
            update_cells(project_id, new_status=g.COPYING_STATUS.working)

            task_ids_with_errors = []
            task_archive_paths = []

            for task in cvat.cvat_data(project_id=project_id):
                data_type = task.data_type

                sly.logger.debug(
                    f"Copying task with id: {task.id}, data type: {data_type}"
                )
                if not g.STATE.continue_copying:
                    sly.logger.debug("Copying is stopped by the user.")
                    continue

                project_name = g.STATE.project_names[project_id]
                project_dir = os.path.join(
                    g.ARCHIVE_DIR, f"{project_id}_{project_name}_{data_type}"
                )
                sly.fs.mkdir(project_dir)
                task_filename = f"{task.id}_{task.name}_{data_type}.zip"

                task_path = os.path.join(project_dir, task_filename)
                download_status = save_task_to_zip(task.id, task_path)
                if download_status is False:
                    task_ids_with_errors.append(task.id)
                else:
                    task_archive_paths.append((task_path, data_type))

            if not task_archive_paths:
                sly.logger.warning(
                    f"No tasks was successfully downloaded for project ID {project_id}. It will be skipped."
                )
                new_status = g.COPYING_STATUS.error
                uploded_with_errors += 1
            else:
                upload_status = convert_and_upload(
                    project_id, project_name, task_archive_paths
                )

                if task_ids_with_errors:
                    sly.logger.warning(
                        f"Project ID {project_id} was downloaded with errors. "
                        "Task IDs with errors: {task_ids_with_errors}."
                    )
                    new_status = g.COPYING_STATUS.error
                    uploded_with_errors += 1
                elif not upload_status:
                    sly.logger.warning(
                        f"Project ID {project_id} was uploaded with errors."
                    )
                    new_status = g.COPYING_STATUS.error
                    uploded_with_errors += 1
                else:
                    sly.logger.info(
                        f"Project ID {project_id} was downloaded successfully."
                    )
                    new_status = g.COPYING_STATUS.copied
                    succesfully_uploaded += 1

            update_cells(project_id, new_status=new_status)

            sly.logger.info(f"Finished processing project ID {project_id}.")

            pbar.update(1)

    if succesfully_uploaded:
        good_results.text = f"Succesfully uploaded {succesfully_uploaded} projects."
        good_results.show()
    if uploded_with_errors:
        bad_results.text = f"Uploaded {uploded_with_errors} projects with errors."
        bad_results.show()

    copy_button.text = "Copy"
    stop_button.hide()

    sly.logger.info(f"Finished copying {len(g.STATE.selected_projects)} projects.")

    if sly.is_development():
        # * For debug purposes it's better to save the data from CVAT.
        sly.logger.debug(
            "Development mode, will not stop the application. "
            "And NOT clean download and upload directories."
        )
        return

    sly.fs.clean_dir(g.ARCHIVE_DIR)
    sly.fs.clean_dir(g.UNPACKED_DIR)

    sly.logger.info(
        f"Removed content from {g.ARCHIVE_DIR} and {g.UNPACKED_DIR}."
        "Will stop the application."
    )

    from src.main import app

    app.stop()


def convert_and_upload(
    project_id: id, project_name: str, task_archive_paths: List[Tuple[str, str]]
) -> bool:
    """Unpacks the task archive, parses it's content, converts it to Supervisely format
    and uploads it to Supervisely.

    1. Checks if the task archive contains images or video.
    2. Creates projects with corresponding data types in Supervisely (images or videos).
    3. For each task:
        3.1. Unpacks the task archive in a separate directory in project directory.
        3.2. Parses annotations.xml and reads list of images.
        3.3. Converts CVAT annotations to Supervisely format.
        3.4. Depending on data type (images or video) creates specific annotations.
        3.5. Uploads images or video to Supervisely.
        3.6. Uploads annotations to Supervisely.
    4. Updates the project in the projects table with new URLs.
    5. Returns True if the upload was successful, False otherwise.

    :param project_id: ID of the project in CVAT
    :type project_id: id
    :param project_name: name of the project in CVAT
    :type project_name: str
    :param task_archive_paths: list of tuples for each task, which containing path to the task archive and data type
        possible data types: 'imageset', 'video'
    :type task_archive_paths: List[Tuple[str, str]]
    :return: status of the upload (True if the upload was successful, False otherwise)
    :rtype: bool
    """
    unpacked_project_path = os.path.join(g.UNPACKED_DIR, f"{project_id}_{project_name}")
    sly.logger.debug(f"Unpacked project path: {unpacked_project_path}")

    images_project = None
    videos_project = None

    if any(task_data_type == "imageset" for _, task_data_type in task_archive_paths):
        images_project = g.api.project.create(
            g.STATE.selected_workspace,
            f"From CVAT {project_name} (images)",
            change_name_if_conflict=True,
        )
        sly.logger.debug(f"Created project {images_project.name} in Supervisely.")

        images_project_meta = sly.ProjectMeta.from_json(
            g.api.project.get_meta(images_project.id)
        )

        sly.logger.debug(f"Retrieved images project meta for {images_project.name}.")

    if any(task_data_type == "video" for _, task_data_type in task_archive_paths):
        videos_project = g.api.project.create(
            g.STATE.selected_workspace,
            f"From CVAT {project_name} (videos)",
            type=sly.ProjectType.VIDEOS,
            change_name_if_conflict=True,
        )
        sly.logger.debug(f"Created project {videos_project.name} in Supervisely.")

        videos_project_meta = sly.ProjectMeta.from_json(
            g.api.project.get_meta(videos_project.id)
        )

        sly.logger.debug(f"Retrieved videos project meta for {videos_project.name}.")

    succesfully_uploaded = True

    for task_archive_path, task_data_type in task_archive_paths:
        sly.logger.debug(
            f"Processing task archive {task_archive_path} with data type {task_data_type}."
        )
        # * Unpacking archive, parsing annotations.xml and reading list of images.
        images_et, images_paths, source = unpack_and_read_task(
            task_archive_path, unpacked_project_path
        )

        sly.logger.debug(f"Parsed annotations and found {len(images_et)} images.")

        # * Using archive name as dataset name.
        dataset_name = sly.fs.get_file_name(task_archive_path)
        sly.logger.debug(f"Will use {dataset_name} as dataset name.")

        if task_data_type == "imageset":
            # Working with Supervisely Images Project.
            sly.logger.debug(
                "Data type is imageset, will convert annotations to Supervisely format."
            )
            task_tags = dict()
            image_objects = []

            # * Convert all annotations to Supervisely format.
            for image_et, image_path in zip(images_et, images_paths):
                image_name = image_et.attrib["name"]
                image_size, image_labels, image_tags = convert_labels(
                    image_et, image_name, task_data_type
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

            # * Prepare lists of paths, names and build annotations from labels.
            images_names, images_paths, images_anns = prepare_images_for_upload(
                image_objects, images_project, images_project_meta
            )

            sly.logger.debug(f"Task data type is {task_data_type}, will upload images.")

            upload_images_task(
                dataset_name,
                images_project,
                images_names,
                images_paths,
                images_anns,
                task_tags,
            )

            sly.logger.info(
                f"Finished processing task archive {task_archive_path} with data type {task_data_type}."
            )
        elif task_data_type == "video":
            # Working with Supervisely Videos Project.
            sly.logger.debug(
                "Task data type is video, will convert annotations to Supervisely format."
            )

            video_frames = []
            video_tags = []
            video_objects = []

            for image_et, image_path in zip(images_et, images_paths):
                video_size, frame_figures, frame_tags = convert_labels(
                    image_et, image_path, task_data_type
                )
                frame_idx = int(image_et.attrib["id"])
                video_frames.append(sly.Frame(frame_idx, figures=frame_figures))
                video_tags.extend(frame_tags)

                for figure in frame_figures:
                    video_object = figure.video_object
                    if video_object not in video_objects:
                        video_objects.append(video_object)

            sly.logger.debug(f"Found {len(video_frames)} frames in the video.")

            update_project_meta(
                videos_project_meta,
                videos_project.id,
                labels=video_objects,
                tags=video_tags,
            )

            # Prepare the name for output video using source name from CVAT annotation.
            # Prepare the path for output video using project directory and source name.
            # Save the video to the path.
            source_name = f"{sly.fs.get_file_name(source)}.mp4"
            video_path = os.path.join(unpacked_project_path, source_name)
            sly.logger.debug(f"Will save video to {video_path}.")
            images_to_mp4(video_path, images_paths, video_size)

            # Create Supervisely VideoAnnotation object using data from CVAT annotation.
            frames = sly.FrameCollection(video_frames)
            objects = sly.VideoObjectCollection(video_objects)
            tag_collection = sly.VideoTagCollection(video_tags)

            sly.logger.debug(
                f"Will create VideoAnnotation object with: {video_size} size, "
                f"{len(frames)} frames, {len(objects)} objects, {len(tag_collection)} tags."
            )

            ann = sly.VideoAnnotation(
                video_size, len(frames), objects, frames, tag_collection
            )

            sly.logger.debug("VideoAnnotation successfully created.")

            dataset_info = g.api.dataset.create(
                videos_project.id, dataset_name, change_name_if_conflict=True
            )

            sly.logger.debug(
                f"Created dataset {dataset_info.name} in project {videos_project.name}."
                "Uploading video..."
            )

            uploaded_video: sly.api.video_api.VideoInfo = g.api.video.upload_path(
                dataset_info.id, source_name, video_path
            )

            sly.logger.debug(
                f"Uploaded video {source_name} to dataset {dataset_info.name}."
            )

            g.api.video.annotation.append(uploaded_video.id, ann)

            sly.logger.debug(f"Added annotation to video with ID {uploaded_video.id}.")

            sly.logger.info(
                f"Finished processing task archive {task_archive_path} with data type {task_data_type}."
            )

    sly.logger.info(
        f"Finished copying project {project_name} from CVAT to Supervisely."
    )

    if images_project:
        update_cells(project_id, new_url=images_project.url)
    if videos_project:
        update_cells(project_id, new_url=videos_project.url)

    sly.logger.debug(f"Updated project {project_name} in the projects table.")

    return succesfully_uploaded


def prepare_images_for_upload(
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
        if not os.path.exists(image_path):
            image_path = f"{image_path}.png"
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
        sly_tag = converters.convert_tag(cvat_tag.attrib, frame_idx=frame_idx)
        sly_tags.append(sly_tag)

        sly.logger.debug(f"Adding converted sly tag to the list of {image_name}.")

    geometries = list(converters.CONVERT_MAP.keys())
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
            sly_label = converters.CONVERT_MAP[geometry](
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


def unpack_and_read_task(
    task_archive_path: str, unpacked_project_path: str
) -> Tuple[List[ET.Element], List[str], str]:
    """Unpacks the task archive from CVAT and reads it's content.
    Parses annotations.xml and reads list of images in it.
    Reads contents of the images directory and prepares a list of paths to the images.
    Reads the "source" parameter in annotations.xml, it's needed to retrieve the
    original name of the video file in CVAT.

    :param task_archive_path: path to the task archive on the local machine
    :type task_archive_path: str
    :param unpacked_project_path: path to the directory where the task archive will be unpacked
    :type unpacked_project_path: str
    :return: list of images in annotations.xml, list of paths to the images, value of the "source" parameter
    :rtype: Tuple[List[ET.Element], List[str], str]
    """
    unpacked_task_dir = sly.fs.get_file_name(task_archive_path)
    unpacked_task_path = os.path.join(unpacked_project_path, unpacked_task_dir)

    sly.fs.unpack_archive(task_archive_path, unpacked_task_path, remove_junk=True)
    sly.logger.debug(f"Unpacked from {task_archive_path} to {unpacked_task_path}")

    images_dir = os.path.join(unpacked_task_path, "images")
    images_list = sly.fs.list_files(images_dir)

    sly.logger.debug(f"Found {len(images_list)} images in {images_dir}.")

    if not images_list:
        sly.logger.warning(f"No images found in {images_dir}, task will be skipped.")
        return

    annotations_xml_path = os.path.join(unpacked_task_path, "annotations.xml")
    if not os.path.exists(annotations_xml_path):
        sly.logger.warning(
            f"Can't find annotations.xml file in {unpacked_task_path}, will upload images without labels."
        )

    tree = ET.parse(annotations_xml_path)
    sly.logger.debug(f"Parsed annotations.xml from {annotations_xml_path}.")

    # * Getting source parameter, which nested in "meta" -> "task" -> "source".
    try:
        source = tree.find("meta").find("task").find("source").text
    except Exception:
        sly.logger.debug(f"Source parameter was not found in {annotations_xml_path}.")
        source = None

    images_et = tree.findall("image")
    sly.logger.debug(f"Found {len(images_et)} images in annotations.xml.")

    images_paths = [
        os.path.join(images_dir, image_et.attrib["name"]) for image_et in images_et
    ]

    return images_et, images_paths, source


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


def upload_images_task(
    dataset_name: str,
    sly_project: sly.ProjectInfo,
    image_names: List[str],
    image_paths: List[str],
    anns: List[sly.Annotation],
    sly_tags: Dict[str, List[sly.Tag]],
) -> List[sly.ImageInfo]:
    """Uploads images, annotations and tags to Supervisely by batches.

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
    sly_dataset = g.api.dataset.create(
        sly_project.id, dataset_name, change_name_if_conflict=True
    )

    sly.logger.debug(
        f"Created dataset {sly_dataset.name} in project {sly_project.name}."
    )

    sly.logger.info(f"Uploading {len(image_names)} images to Supervisely.")

    for batched_image_names, batched_image_paths, batched_anns in zip(
        sly.batched(image_names), sly.batched(image_paths), sly.batched(anns)
    ):
        uploaded_image_infos = g.api.image.upload_paths(
            sly_dataset.id, batched_image_names, batched_image_paths
        )

        uploaded_image_ids = [image_info.id for image_info in uploaded_image_infos]

        sly.logger.info(
            f"Uploaded {len(uploaded_image_ids)} images to Supervisely to dataset {sly_dataset.name}."
        )

        g.api.annotation.upload_anns(uploaded_image_ids, batched_anns)

        sly.logger.info(f"Uploaded {len(batched_anns)} annotations to Supervisely.")

    sly.logger.info(
        f"Finished uploading images and annotations for dataset {sly_dataset.name} to Supervisely."
    )

    if sly_tags:
        sly.logger.debug("There were tags in the current task, will upload them.")
        upload_images_tags(uploaded_image_infos, sly_project.id, sly_tags)
    else:
        sly.logger.debug("No tags were found in the current task, nothing to upload.")

    return uploaded_image_infos


def upload_images_tags(
    uploaded_images: List[sly.ImageInfo],
    sly_project_id: int,
    sly_tags: Dict[str, List[sly.Tag]],
) -> None:
    """Upload tags for the uploaded images to Supervisely.

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
        tag_id = get_tag_meta(sly_project_id, tag_name).sly_id
        g.api.image.add_tag_batch(image_ids, tag_id)

    sly.logger.info("Tags successfully uploaded to Supervisely.")


def get_tag_meta(sly_project_id: int, tag_name: str) -> sly.TagMeta:
    """Returns active tag meta from API for the given project ID and tag name.
    Important: this function makes an API call, because local project meta does not contain tag IDs.

    :param sly_project_id: project ID in Supervisely
    :type sly_project_id: int
    :param tag_name: tag name to get meta for
    :type tag_name: str
    :return: tag meta from API
    :rtype: sly.TagMeta
    """
    project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(sly_project_id))
    return project_meta.get_tag_meta(tag_name)


def update_project_meta(
    project_meta: sly.ProjectMeta,
    project_id: int,
    labels: Optional[List[sly.Label]] = None,
    tags: Optional[Union[List[sly.Tag], List[sly.VideoObject]]] = None,
) -> sly.ProjectMeta:
    """Updates Supervisely projects meta with new labels or tags on instance and returns updated meta.

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
                    g.api.project.update_meta(project_id, project_meta)
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
                g.api.project.update_meta(project_id, project_meta)
                sly.logger.debug(
                    f"Tag meta {tag.meta.name} added, meta updated on Supervisely."
                )

    sly.logger.debug("Update project meta finished.")

    return project_meta


def update_cells(project_id: int, **kwargs) -> None:
    """Updates cells in the projects table by project ID.
    Possible kwargs:
        - new_status: new status for the project
        - new_url: new Supervisely URL for the project

    :param project_id: project ID in CVAT for projects table to update
    :type project_id: int
    """
    key_cell_value = project_id
    key_column_name = "ID"
    if kwargs.get("new_status"):
        column_name = "COPYING STATUS"
        new_value = kwargs["new_status"]
    elif kwargs.get("new_url"):
        column_name = "SUPERVISELY URL"
        url = kwargs["new_url"]

        # When updating the cell with the URL we need to append the new URL to the old value
        # for cases when one CVAT project was converted to multiple Supervisely projects.
        # This usually happens when CVAT project contains both images and videos
        # while Supervisely supports one data type per project.
        old_value = get_cell_value(project_id)
        if old_value:
            old_value += "<br>"
        new_value = old_value + f"<a href='{url}' target='_blank'>{url}</a>"

    projects_table.update_cell_value(
        key_column_name, key_cell_value, column_name, new_value
    )


def get_cell_value(
    project_id: int, column: str = "SUPERVISELY URL"
) -> Union[str, None]:
    """Returns value of the cell in the projects table by project ID and column name.
    By default returns value of the "SUPERVISELY URL" column.

    :param project_id: project ID in CVAT to find the table row
    :type project_id: int
    :param column: name of the columnm where to get the value, defaults to "SUPERVISELY URL"
    :type column: str, optional
    :return: value of the cell in the projects table or None if not found
    :rtype: Union[str, None]
    """
    table_json_data = projects_table.get_json_data()["table_data"]

    # Find column index by column name.
    cell_column_idx = None
    for column_idx, column_name in enumerate(table_json_data["columns"]):
        if column_name == column:
            cell_column_idx = column_idx
            break

    for row_idx, row_content in enumerate(table_json_data["data"]):
        if row_content[1] == project_id:
            return row_content[cell_column_idx]


@stop_button.click
def stop_copying() -> None:
    """Stops copying process by setting continue_copying flag to False."""
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()
