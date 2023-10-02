import os
from typing import List, Tuple
import supervisely as sly

import globals as g
import xml.etree.ElementTree as ET

from cvat.tools import (
    convert_images_annotations,
    convert_video_annotations,
    prepare_images_for_upload,
    upload_images_task,
    update_project_meta,
    images_to_mp4,
)

MARKER = "annotations.xml"


@sly.handle_exceptions
def main():
    sly.logger.debug("Starting main function...")
    data_path = download_data()

    project_name = f"From CVAT {os.path.basename(data_path)}"
    sly.logger.info(f"Will use project name: {project_name}")

    images_tasks = []
    videos_tasks = []

    for cvat_task in sly.fs.dirs_with_marker(
        data_path, MARKER, check_function=check_function, ignore_case=True
    ):
        sly.logger.debug(f"Found CVAT data in {cvat_task}")
        annotations_xml_path = os.path.join(cvat_task, MARKER)
        tree = ET.parse(annotations_xml_path)
        try:
            source = tree.find("meta").find("task").find("source").text
        except Exception:
            source = None

        if not source:
            images_tasks.append((cvat_task, source))
        else:
            videos_tasks.append((cvat_task, source))

    sly.logger.debug(
        f"Found {len(images_tasks)} images tasks and {len(videos_tasks)} videos tasks"
    )

    if images_tasks:
        process_image_tasks(project_name, images_tasks)
    if videos_tasks:
        process_video_tasks(project_name, videos_tasks)

    sly.logger.info("Processed all tasks, exiting...")


def process_image_tasks(project_name: str, images_tasks: List[str]):
    sly.logger.info(f"Started processing {len(images_tasks)} images tasks...")

    images_project = g.api.project.create(
        g.WORKSPACE_ID,
        project_name + "(images)",
        type=sly.ProjectType.IMAGES,
        change_name_if_conflict=True,
    )

    images_project_meta = sly.ProjectMeta.from_json(
        g.api.project.get_meta(images_project.id)
    )

    sly.logger.debug(
        f"Created project {images_project.name} with id {images_project.id}"
    )

    sly.logger.debug(f"Will process {len(images_tasks)} images tasks")

    for task_path, _ in images_tasks:
        images_et, images_paths = read_task_data(task_path)

        sly.logger.debug(f"Read {len(images_paths)} images from {task_path}")

        dataset_name = sly.fs.get_file_name(task_path)
        sly.logger.debug(f"Will use {dataset_name} as dataset name.")

        task_tags, image_objects = convert_images_annotations(
            images_et, images_paths, "imageset"
        )

        sly.logger.debug(
            f"Prepared labels and tags in Supervisely format for {len(image_objects)} images."
        )

        images_names, images_paths, images_anns = prepare_images_for_upload(
            g.api, image_objects, images_project, images_project_meta
        )

        sly.logger.debug(f"Prepared {len(images_names)} images for upload.")

        uploaded_images = upload_images_task(
            g.api,
            dataset_name,
            images_project,
            images_names,
            images_paths,
            images_anns,
            task_tags,
        )

        sly.logger.info(
            f"Successfully uploaded {len(uploaded_images)} images to dataset {dataset_name}"
            f"in project {images_project.name}"
        )

    sly.logger.info(f"Finished processing {len(images_tasks)} images tasks.")


def process_video_tasks(project_name: str, videos_tasks: List[str]):
    sly.logger.info(f"Started processing {len(videos_tasks)} videos tasks...")

    videos_project = g.api.project.create(
        g.WORKSPACE_ID,
        project_name + "(videos)",
        type=sly.ProjectType.VIDEOS,
        change_name_if_conflict=True,
    )

    videos_project_meta = sly.ProjectMeta.from_json(
        g.api.project.get_meta(videos_project.id)
    )

    sly.logger.debug(
        f"Created project {videos_project.name} with id {videos_project.id}"
    )

    sly.logger.debug(f"Will process {len(videos_tasks)} videos tasks")

    for task_path, source in videos_tasks:
        images_et, images_paths = read_task_data(task_path)

        sly.logger.debug(f"Read {len(images_paths)} images from {task_path}")

        dataset_name = sly.fs.get_file_name(task_path)
        sly.logger.debug(f"Will use {dataset_name} as dataset name.")
        (
            video_size,
            video_frames,
            video_objects,
            video_tags,
        ) = convert_video_annotations(images_et, images_paths)

        sly.logger.debug(f"Found {len(video_frames)} frames in the video.")

        update_project_meta(
            g.api,
            videos_project_meta,
            videos_project.id,
            labels=video_objects,
            tags=video_tags,
        )

        source_name = f"{sly.fs.get_file_name(source)}.mp4"
        video_path = os.path.join(task_path, source_name)
        sly.logger.debug(f"Will save video to {video_path}.")
        images_to_mp4(video_path, images_paths, video_size)

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

        sly.logger.debug(
            f"Successfully uploaded video {uploaded_video.name} to dataset {dataset_info.name}"
            f"in project {videos_project.name}."
        )

    sly.logger.info(f"Finished processing {len(videos_tasks)} videos tasks.")


def check_function(folder_path: str) -> bool:
    images_dir = os.path.join(folder_path, "images")
    return os.path.isdir(images_dir) and sly.fs.list_files(images_dir)


def read_task_data(task_path: str) -> Tuple[List[ET.Element], List[str]]:
    annotations_xml_path = os.path.join(task_path, "annotations.xml")
    tree = ET.parse(annotations_xml_path)
    images_et = tree.findall("image")

    images_dir = os.path.join(task_path, "images")

    images_paths = [
        os.path.join(images_dir, image_et.attrib["name"]) for image_et in images_et
    ]

    return images_et, images_paths


def download_data() -> str:
    sly.logger.info("Starting download data...")
    if g.SLY_FILE:
        sly.logger.info(f"Was provided a path to file: {g.SLY_FILE}")
        data_path = _download_archive(g.SLY_FILE)

    elif g.SLY_FOLDER:
        sly.logger.info(f"Was provided a path to folder: {g.SLY_FOLDER}")
        files_list = g.api.file.list(g.TEAM_ID, g.SLY_FOLDER)
        if len(files_list) == 1:
            sly.logger.debug(
                f"Provided folder contains only one file: {files_list[0].name}. "
                "Will handle it as an archive."
            )
            data_path = _download_archive(files_list[0].path)
        else:
            sly.logger.debug(
                f"Provided folder contains more than one file: {files_list}. "
                "Will handle it as a folder with unpacked CVAT data."
            )

            data_path = _download_folder(g.SLY_FOLDER)

    sly.logger.debug(f"Data downloaded and prepared in {data_path}.")

    return data_path


def _download_folder(remote_path: str) -> str:
    sly.logger.info(f"Starting download folder from {remote_path}...")
    folder_name = sly.fs.get_file_name(remote_path)
    save_path = os.path.join(g.UNPACKED_DIR, folder_name)
    sly.logger.debug(f"Will download folder to {save_path}.")
    g.api.file.download_directory(g.TEAM_ID, remote_path, save_path)
    sly.logger.debug(f"Folder downloaded to {save_path}.")
    return save_path


def _download_archive(remote_path: str) -> str:
    sly.logger.info(f"Starting download archive from {remote_path}...")
    archive_name = sly.fs.get_file_name_with_ext(remote_path)
    save_path = os.path.join(g.ARCHIVE_DIR, archive_name)
    sly.logger.debug(f"Will download archive to {save_path}.")
    g.api.file.download(g.TEAM_ID, remote_path, save_path)
    sly.logger.debug(f"Archive downloaded to {save_path}.")

    file_name = sly.fs.get_file_name(remote_path)
    unpack_path = os.path.join(g.UNPACKED_DIR, file_name)
    sly.logger.debug(f"Will unpack archive to {unpack_path}.")
    try:
        sly.fs.unpack_archive(save_path, unpack_path)
    except Exception as e:
        raise RuntimeError(
            f"Can't unpack archive from {remote_path}. "
            f"Provided file must be a valid archive. {e}"
        )
    sly.logger.debug(f"Archive unpacked to {unpack_path}.")
    return unpack_path


if __name__ == "__main__":
    main()
