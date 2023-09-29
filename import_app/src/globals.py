import os

import supervisely as sly

from dotenv import load_dotenv

ABSOLUTE_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(ABSOLUTE_PATH)
sly.logger.debug(f"Absolute path: {ABSOLUTE_PATH}, parent dir: {PARENT_DIR}")

if sly.is_development():
    # * For convinient development, has no effect in the production.
    local_env_path = os.path.join(PARENT_DIR, "local.env")
    supervisely_env_path = os.path.expanduser("~/supervisely.env")
    sly.logger.debug(
        "Running in development mode. Will load .env files... "
        f"Local .env path: {local_env_path}, Supervisely .env path: {supervisely_env_path}"
    )

    if os.path.exists(local_env_path) and os.path.exists(supervisely_env_path):
        sly.logger.debug("Both .env files exists. Will load them.")
        load_dotenv(local_env_path)
        load_dotenv(supervisely_env_path)
    else:
        sly.logger.warning("One of the .env files is missing. It may cause errors.")

api: sly.Api = sly.Api.from_env()
SLY_APP_DATA_DIR = sly.app.get_data_dir()
sly.logger.debug(f"App starting... SLY_APP_DATA_DIR: {SLY_APP_DATA_DIR}")

TEMP_DIR = os.path.join(SLY_APP_DATA_DIR, "temp")

# * Directory, where downloaded as archives CVAT tasks will be stored.
ARCHIVE_DIR = os.path.join(TEMP_DIR, "archives")

# * Directory, where unpacked CVAT tasks will be stored.
UNPACKED_DIR = os.path.join(TEMP_DIR, "unpacked")
sly.fs.mkdir(ARCHIVE_DIR, remove_content_if_exists=True)
sly.fs.mkdir(UNPACKED_DIR, remove_content_if_exists=True)
sly.logger.debug(
    f"App starting... Archive dir: {ARCHIVE_DIR}, unpacked dir: {UNPACKED_DIR}"
)

TEAM_ID = sly.io.env.team_id()
WORKSPACE_ID = sly.io.env.workspace_id()

sly.logger.debug(f"App starting... Team ID: {TEAM_ID}, Workspace ID: {WORKSPACE_ID}")

SLY_FILE = sly.io.env.file(raise_not_found=False)
SLY_FOLDER = sly.io.env.folder(raise_not_found=False)
sly.logger.debug(f"App starting... File: {SLY_FILE}, Folder: {SLY_FOLDER}")

if SLY_FILE:
    sly.logger.info(
        "Path to file is provided, the application will be run in file mode. "
        f"File path: {SLY_FILE}"
    )
elif SLY_FOLDER:
    sly.logger.info(
        "Path to folder is provided, the application will be run in folder mode. "
        f"Folder path: {SLY_FOLDER}"
    )
