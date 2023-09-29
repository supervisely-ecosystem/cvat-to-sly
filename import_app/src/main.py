import os
import supervisely as sly

import import_app.src.globals as g


def main():
    pass


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
    download_data()
