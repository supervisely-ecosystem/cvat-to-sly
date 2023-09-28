import os

from collections import namedtuple
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
sly.logger.debug(f"SLY_APP_DATA_DIR: {SLY_APP_DATA_DIR}")

TEMP_DIR = os.path.join(SLY_APP_DATA_DIR, "temp")

# * Directory, where downloaded as archives CVAT tasks will be stored.
ARCHIVE_DIR = os.path.join(TEMP_DIR, "archives")

# * Directory, where unpacked CVAT tasks will be stored.
UNPACKED_DIR = os.path.join(TEMP_DIR, "unpacked")
sly.fs.mkdir(ARCHIVE_DIR, remove_content_if_exists=True)
sly.fs.mkdir(UNPACKED_DIR, remove_content_if_exists=True)
sly.logger.debug(f"Archive dir: {ARCHIVE_DIR}, unpacked dir: {UNPACKED_DIR}")


class State:
    def __init__(self):
        self.selected_team = sly.io.env.team_id()
        self.selected_workspace = sly.io.env.workspace_id()

        # Will be set to True, if the app will be launched from .env file in Supervisely.
        self.loaded_from_env = False

        # CVAT credentials to access the API.
        self.cvat_server_address = None
        self.cvat_username = None
        self.cvat_password = None

        # Dictionary with project_ids as keys and project_names as values.
        # Example: {1: "project1", 2: "project2", 3: "project3"}
        self.project_names = dict()

        # List of selected project ids to copy.
        # Example: [1, 2, 3]
        self.selected_projects = None

        # Will be set to False if the cancel button will be pressed.
        # Sets to True on every click on the "Copy" button.
        self.continue_copying = True

    def clear_cvat_credentials(self):
        """Clears the CVAT credentials and sets them to None."""

        sly.logger.debug("Clearing CVAT credentials...")
        self.cvat_server_address = None
        self.cvat_username = None
        self.cvat_password = None

    def load_from_env(self):
        """Downloads the .env file from Supervisely and reads the CVAT credentials from it."""

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

# * Local path to the .env file with credentials, after downloading it from Supervisely.
CVAT_ENV_FILE = os.path.join(PARENT_DIR, "cvat.env")
sly.logger.debug(f"Path to the local cvat.env file: {CVAT_ENV_FILE}")

# * Path to the .env file with credentials (on Team Files).
# While local development can be set in local.env file with: context.slyFile = "/.env/cvat.env"
CVAT_ENV_TEAMFILES = sly.env.file(raise_not_found=False)
sly.logger.debug(f"Path to the TeamFiles from environment: {CVAT_ENV_TEAMFILES}")

CopyingStatus = namedtuple("CopyingStatus", ["copied", "error", "waiting", "working"])
COPYING_STATUS = CopyingStatus("✅ Copied", "❌ Error", "⏳ Waiting", "🔄 Working")

if CVAT_ENV_TEAMFILES:
    sly.logger.debug(".env file is provided, will try to download it.")
    STATE.load_from_env()
