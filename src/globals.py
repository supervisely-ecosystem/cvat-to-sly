import os

from collections import namedtuple
import supervisely as sly

from dotenv import load_dotenv

if sly.is_development():
    # * For convinient development, has no effect in the production.
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api: sly.Api = sly.Api.from_env()
SLY_APP_DATA_DIR = sly.app.get_data_dir()
sly.logger.debug(f"SLY_APP_DATA_DIR: {SLY_APP_DATA_DIR}")

TEMP_DIR = os.path.join(SLY_APP_DATA_DIR, "temp")
sly.fs.mkdir(TEMP_DIR, remove_content_if_exists=True)
sly.logger.debug(f"TEMP_DIR: {TEMP_DIR}")


class State:
    def __init__(self):
        self.selected_team = sly.io.env.team_id()
        self.selected_workspace = sly.io.env.workspace_id()

        self.loaded_from_env = False

        self.cvat_server_address = None
        self.cvat_username = None
        self.cvat_password = None

        self.project_names = dict()
        self.selected_projects = None

        self.continue_copying = True

    def clear_cvat_credentials(self):
        sly.logger.debug("Clearing CVAT credentials...")
        self.cvat_server_address = None
        self.cvat_username = None
        self.cvat_password = None

    def load_from_env(self):
        api.file.download(STATE.selected_team, CVAT_ENV_TEAMFILES, CVAT_ENV_FILE)
        sly.logger.debug(
            ".env file downloaded successfully. Will read the credentials."
        )
        load_dotenv(CVAT_ENV_FILE)
        self.cvat_server_address = os.getenv("CVAT_SERVER_ADDRESS")
        self.cvat_username = os.getenv("CVAT_USERNAME")
        self.cvat_password = os.getenv("CVAT_PASSWORD")
        sly.logger.debug(
            "CVAT credentials readed successfully. "
            f"Server address: {STATE.cvat_server_address}, username: {STATE.cvat_username}. "
            "Will check the connection."
        )
        self.loaded_from_env = True


STATE = State()
sly.logger.debug(
    f"Selected team: {STATE.selected_team}, selected workspace: {STATE.selected_workspace}"
)

ABSOLUTE_PATH = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(ABSOLUTE_PATH)
sly.logger.debug(f"Absolute path: {ABSOLUTE_PATH}, parent dir: {PARENT_DIR}")

CVAT_ENV_FILE = os.path.join(PARENT_DIR, "cvat.env")
sly.logger.debug(f"Path to the local cvat.env file: {CVAT_ENV_FILE}")
CVAT_ENV_TEAMFILES = sly.env.file(raise_not_found=False)
sly.logger.debug(f"Path to the TeamFiles from environment: {CVAT_ENV_TEAMFILES}")

CopyingStatus = namedtuple("CopyingStatus", ["copied", "error", "waiting", "working"])
COPYING_STATUS = CopyingStatus("✅ Copied", "❌ Error", "⏳ Waiting", "🔄 Working")

if CVAT_ENV_TEAMFILES:
    sly.logger.debug(".env file is provided, will try to download it.")
    STATE.load_from_env()
