import supervisely as sly

from supervisely.app.widgets import Card, Text, Input, Field, Button, Container

import src.globals as g
import src.ui.selection as selection

cvat_server_address_input = Input(
    minlength=10, placeholder="for example: http://localhost:8080"
)
cvat_server_address_field = Field(
    title="CVAT server address",
    description="Address of the CVAT server to connect to, including port.",
    content=cvat_server_address_input,
)

cvat_username_input = Input(minlength=1, placeholder="for example: admin")
cvat_username_field = Field(
    title="CVAT username",
    description="Username of the CVAT user to connect as.",
    content=cvat_username_input,
)

cvat_password_input = Input(
    minlength=1, type="password", placeholder="for example: admin"
)
cvat_password_field = Field(
    title="CVAT password",
    description="Password of the CVAT user to connect as.",
    content=cvat_password_input,
)

connect_button = Button("Connect to CVAT")
connect_button.disable()
change_connection_button = Button("Change connection settings")
change_connection_button.hide()

load_from_env_text = Text(
    "Connection settings was loaded from .env file.", status="info"
)
load_from_env_text.hide()
connection_status_text = Text()
connection_status_text.hide()

card = Card(
    title="1️⃣ CVAT connection",
    description="Enter your CVAT connection settings and check the connection.",
    content=Container(
        [
            cvat_server_address_field,
            cvat_username_field,
            cvat_password_field,
            connect_button,
            load_from_env_text,
            connection_status_text,
        ]
    ),
    content_top_right=change_connection_button,
    collapsable=True,
)


def connected():
    sly.logger.debug("Status changed to connected, will change widget states.")
    card.lock()
    card.collapse()

    selection.card.unlock()
    selection.card.uncollapse()

    change_connection_button.show()
    connection_status_text.status = "success"
    connection_status_text.text = (
        f"Successfully connected to {g.STATE.cvat_server_address} "
        f"as {g.STATE.cvat_username}."
    )

    connection_status_text.show()


def disconnected(with_error=False):
    sly.logger.debug(
        f"Status changed to disconnected with error: {with_error}, will change widget states."
    )
    card.unlock()
    card.uncollapse()

    selection.card.lock()
    selection.card.collapse()

    change_connection_button.hide()

    if with_error:
        connection_status_text.status = "error"
        connection_status_text.text = (
            f"Failed to connect to {g.STATE.cvat_server_address} "
            f"as {g.STATE.cvat_username}."
        )
    else:
        g.STATE.clear_cvat_credentials()

        connection_status_text.status = "warning"
        connection_status_text.text = f"Disconnected from {g.STATE.cvat_server_address} as {g.STATE.cvat_username}."

    connection_status_text.show()
