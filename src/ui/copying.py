import os
import shutil
import supervisely as sly
from typing import List, Dict, Optional
from collections import defaultdict

from supervisely.app.widgets import Container, Card, Table, Button, Progress, Text
import xml.etree.ElementTree as ET

import src.globals as g
import src.cvat as cvat
import src.converters as converters

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

copying_progress = Progress()
good_results = Text(status="success")
bad_results = Text(status="error")
good_results.hide()
bad_results.hide()

card = Card(
    title="3️⃣ Copying",
    description="Copy selected projects from CVAT to Supervisely.",
    content=Container(
        [projects_table, copy_button, copying_progress, good_results, bad_results]
    ),
    content_top_right=stop_button,
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
                sly.logger.debug(f"Copying task with id: {task.id}")
                if not g.STATE.continue_copying:
                    sly.logger.debug("Copying is stopped by the user.")
                    continue

                project_name = g.STATE.project_names[project_id]
                project_dir = os.path.join(
                    g.ARCHIVE_DIR, f"{project_id}_{project_name}"
                )
                sly.fs.mkdir(project_dir)
                task_filename = f"{task.id}_{task.name}.zip"

                task_path = os.path.join(project_dir, task_filename)
                download_status = save_task_to_zip(task.id, task_path)
                if download_status is False:
                    task_ids_with_errors.append(task.id)
                else:
                    task_archive_paths.append(task_path)

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
    project_id: id, project_name: str, task_archive_paths: List[str]
) -> bool:
    unpacked_project_path = os.path.join(g.UNPACKED_DIR, f"{project_id}_{project_name}")
    sly.logger.debug(f"Unpacked project path: {unpacked_project_path}")

    sly_project = g.api.project.create(
        g.STATE.selected_workspace,
        f"From CVAT {project_name}",
        change_name_if_conflict=True,
    )
    sly.logger.debug(f"Created project {sly_project.name} in Supervisely.")

    project_meta = sly.ProjectMeta.from_json(g.api.project.get_meta(sly_project.id))
    sly.logger.debug(f"Retrieved project meta for {sly_project.name}.")

    succesfully_uploaded = True
    uploaded_images = []

    for task_archive_path in task_archive_paths:
        unpacked_task_dir = sly.fs.get_file_name(task_archive_path)
        unpacked_task_path = os.path.join(unpacked_project_path, unpacked_task_dir)

        sly.fs.unpack_archive(task_archive_path, unpacked_task_path, remove_junk=True)
        sly.logger.debug(f"Unpacked from {task_archive_path} to {unpacked_task_path}")

        images_dir = os.path.join(unpacked_task_path, "images")
        images_list = sly.fs.list_files(images_dir)

        sly.logger.debug(f"Found {len(images_list)} images in {images_dir}.")

        if not images_list:
            sly.logger.warning(
                f"No images found in {images_dir}, task will be skipped."
            )
            continue

        annotations_xml_path = os.path.join(unpacked_task_path, "annotations.xml")
        if not os.path.exists(annotations_xml_path):
            sly.logger.warning(
                f"Can't find annotations.xml file in {unpacked_task_path}, will upload images without labels."
            )

        tree = ET.parse(annotations_xml_path)
        sly.logger.debug(f"Parsed annotations.xml from {annotations_xml_path}.")

        images = tree.findall("image")
        sly.logger.debug(f"Found {len(images)} images in annotations.xml.")

        sly_labels_in_task = defaultdict(list)
        sly_tags_in_task = defaultdict(list)

        for image in images:
            image_name = image.attrib["name"]
            image_height = int(image.attrib["height"])
            image_width = int(image.attrib["width"])

            cvat_tags = image.findall("tag") or []

            sly.logger.debug(f"Found {len(cvat_tags)} tags in {image_name}.")

            for cvat_tag in cvat_tags:
                sly_tag = converters.convert_tag(cvat_tag.attrib)
                sly_tags_in_task[image_name].append(sly_tag)

                sly.logger.debug(
                    f"Adding converted sly tag to the list of {image_name}."
                )

            geometries = list(converters.CONVERT_MAP.keys())
            for geometry in geometries:
                cvat_labels = image.findall(geometry) or []

                sly.logger.debug(
                    f"Found {len(cvat_labels)} with {geometry} geometry in {image_name}."
                )

                for cvat_label in cvat_labels:
                    sly_label = converters.CONVERT_MAP[geometry](
                        cvat_label.attrib,
                        image_height=image_height,
                        image_width=image_width,
                    )

                    if isinstance(sly_label, list):
                        # * If CVAT label was converted to multiple Supervisely labels (e.g. for points)
                        # * we need to extend the list of labels for the image.
                        sly_labels_in_task[image_name].extend(sly_label)
                    else:
                        # Otherwise we just append the label to the list.
                        sly_labels_in_task[image_name].append(sly_label)
                    sly.logger.debug(
                        f"Adding converted sly label with geometry {geometry} to the list of {image_name}."
                    )

        sly.logger.debug(
            f"Prepared {len(sly_labels_in_task)} images with labels for upload."
        )

        image_names = []
        image_paths = []
        anns = []

        for image in images_list:
            image_name = sly.fs.get_file_name_with_ext(image)
            image_path = os.path.join(images_dir, image_name)
            image_names.append(image_name)
            image_paths.append(image_path)

            image_np = sly.image.read(image_path)
            height, width, _ = image_np.shape
            image_size = (height, width)
            del image_np

            sly.logger.debug(
                f"Image {image_name} has size (height, width): {image_size}."
            )

            labels = sly_labels_in_task.get(image_name)

            if not labels:
                ann = sly.Annotation(img_size=image_size)
                sly.logger.debug(
                    f"Created empty annotation for {image_name}, since no labels were found."
                )
            else:
                # * Remove None values from the list of labels to avoid errors.
                labels = [label for label in labels if label is not None]

                project_meta = update_project_meta(
                    project_meta, sly_project.id, labels=labels
                )
                ann = sly.Annotation(img_size=image_size, labels=labels)
                sly.logger.debug(f"Created annotation for {image_name} with labels.")

            anns.append(ann)

            tags = sly_tags_in_task.get(image_name)
            if tags:
                sly.logger.debug(
                    f"Image {image_name} has tags, will try to update project meta."
                )

                project_meta = update_project_meta(
                    project_meta, sly_project.id, tags=tags
                )

        if len(image_names) != len(image_paths) != len(anns):
            sly.logger.error(
                f"Lengths of image_names, image_paths and anns are not equal. "
                f"Task with data {task_archive_path} will be skipped."
            )
            succesfully_uploaded = False
            continue

        archive_name = sly.fs.get_file_name(task_archive_path)
        sly_dataset = g.api.dataset.create(
            sly_project.id, archive_name, change_name_if_conflict=True
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

            uploaded_images.extend(uploaded_image_infos)

            uploaded_image_ids = [image_info.id for image_info in uploaded_image_infos]

            sly.logger.info(
                f"Uploaded {len(uploaded_image_ids)} images to Supervisely to dataset {sly_dataset.name}."
            )

            g.api.annotation.upload_anns(uploaded_image_ids, batched_anns)

            sly.logger.info(f"Uploaded {len(batched_anns)} annotations to Supervisely.")

        sly.logger.info(
            f"Finished uploading images and annotations from arhive {task_archive_path} to Supervisely."
        )

    if sly_tags_in_task:
        sly.logger.debug("There were tags in the current task, will upload them.")
        upload_tags(uploaded_images, sly_project.id, sly_tags_in_task)
    else:
        sly.logger.debug("No tags were found in the current task, nothing to upload.")

    sly.logger.info(
        f"Finished copying project {project_name} from CVAT to Supervisely."
    )

    update_cells(project_id, new_url=sly_project.url)

    sly.logger.debug(f"Updated project {project_name} in the projects table.")

    return succesfully_uploaded


def upload_tags(
    uploaded_images: List[sly.ImageInfo],
    sly_project_id: int,
    sly_tags_in_task: Dict[str, List[sly.Tag]],
) -> None:
    """Upload tags for the uploaded images to Supervisely.

    :param uploaded_images: list of uploaded images as ImageInfo objects
    :type uploaded_images: List[sly.ImageInfo]
    :param sly_project_id: project ID in Supervisely
    :type sly_project_id: int
    :param sly_tags_in_task: dictionary with tags for each image by image name
    :type sly_tags_in_task: Dict[str, List[sly.Tag]]
    """
    tag_data_for_upload = defaultdict(list)

    sly.logger.debug(
        f"Started building tags dictionary for {len(uploaded_images)} images."
    )

    for image_info in uploaded_images:
        tags = sly_tags_in_task.get(image_info.name)
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
    tags: Optional[List[sly.Tag]] = None,
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

    if labels:
        for label in labels:
            label: sly.Label
            if label.obj_class not in project_meta.obj_classes:
                sly.logger.debug(
                    f"Object class {label.obj_class.name} not found in project meta, will add it."
                )
                project_meta = project_meta.add_obj_class(label.obj_class)
                g.api.project.update_meta(project_id, project_meta)
                sly.logger.debug(
                    f"Object class {label.obj_class.name} added, meta updated on Supervisely."
                )
    elif tags:
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
        new_value = f"<a href='{url}' target='_blank'>{url}</a>"

    projects_table.update_cell_value(
        key_column_name, key_cell_value, column_name, new_value
    )


@stop_button.click
def stop_copying() -> None:
    """Stops copying process by setting continue_copying flag to False."""
    sly.logger.debug("Stop button is clicked.")

    g.STATE.continue_copying = False
    copy_button.text = "Stopping..."

    stop_button.hide()
