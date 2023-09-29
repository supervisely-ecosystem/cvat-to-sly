import supervisely as sly

from supervisely.app.widgets import Card, Text, Input, Field, Button, Container

import migration_tool.src.globals as g
import migration_tool.src.ui.selection as selection

from cvat.api import check_connection

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
change_connection_button = Button("Change settings")
change_connection_button.hide()

load_from_env_text = Text(
    "Connection settings was loaded from .env file.", status="info"
)
load_from_env_text.hide()
connection_status_text = Text()
connection_status_text.hide()

widgets = [
    cvat_server_address_input,
    cvat_username_input,
    cvat_password_input,
    connect_button,
]

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


def connected() -> None:
    """Changes the state of the widgets if the app successfully connected to the CVAT server.
    Launches the process of filling the transfer with projects from CVAT API."""

    sly.logger.debug("Status changed to connected, will change widget states.")
    for widget in widgets:
        widget.disable()

    selection.card.unlock()
    selection.card.uncollapse()

    change_connection_button.show()
    connection_status_text.status = "success"
    connection_status_text.text = (
        f"Successfully connected to {formatted_connection_settings()}."
    )

    connection_status_text.show()
    selection.fill_transfer_with_projects()


def disconnected(with_error=False) -> None:
    """Changes the state of the widgets if the app disconnected from the CVAT server.
    Depending on the value of the with_error parameter, the status text will be different.

    :param with_error: if the app was disconnected from server or by a pressing change button, defaults to False
    :type with_error: bool, optional
    """

    sly.logger.debug(
        f"Status changed to disconnected with error: {with_error}, will change widget states."
    )
    for widget in widgets:
        widget.enable()

    card.uncollapse()
    selection.card.lock()
    selection.card.collapse()

    change_connection_button.hide()

    if with_error:
        connection_status_text.status = "error"
        connection_status_text.text = (
            f"Failed to connect to {formatted_connection_settings()}."
        )

    else:
        connection_status_text.status = "warning"
        connection_status_text.text = (
            f"Disconnected from {formatted_connection_settings()}."
        )

    g.STATE.clear_cvat_credentials()
    connection_status_text.show()


def formatted_connection_settings() -> str:
    """Returns HTML-formatted string with the CVAT connection settings (server address, username).

    :return: HTML-formatted string
    :rtype: str
    """
    return (
        f'<a href="{g.STATE.cvat_server_address}">{g.STATE.cvat_server_address}</a> '
        f"as <b>{g.STATE.cvat_username}</b>"
    )


def change_connect_button_state(_: str) -> None:
    """Enables the connect button if all the required fields are filled,
    otherwise disables it.

    :param _: Unused (value from the widget)
    :type input_value: str
    """
    if all(
        [
            cvat_server_address_input.get_value(),
            cvat_username_input.get_value(),
            cvat_password_input.get_value(),
        ]
    ):
        connect_button.enable()

    else:
        connect_button.disable()


cvat_server_address_input.value_changed(change_connect_button_state)
cvat_username_input.value_changed(change_connect_button_state)
cvat_password_input.value_changed(change_connect_button_state)


@connect_button.click
def try_to_connect() -> None:
    """Save the CVAT credentials from the widgets to the global State and try to connect to the CVAT server.
    Depending on the result of the connection, the state of the widgets will change."""
    g.STATE.cvat_server_address = cvat_server_address_input.get_value()
    g.STATE.cvat_username = cvat_username_input.get_value()
    g.STATE.cvat_password = cvat_password_input.get_value()

    sly.logger.debug(
        f"Saved CVAT credentials in global State. "
        f"Server address: {g.STATE.cvat_server_address}, "
        f"username: {g.STATE.cvat_username}."
    )

    connection_status = check_connection()

    if connection_status:
        connected()
    else:
        disconnected(with_error=True)


if g.STATE.loaded_from_env:
    sly.logger.debug('The application was started with the "Load from .env" option.')

    load_from_env_text.show()

    cvat_server_address_input.set_value(g.STATE.cvat_server_address)
    cvat_username_input.set_value(g.STATE.cvat_username)
    cvat_password_input.set_value(g.STATE.cvat_password)
    connect_button.enable()

    connection_status = check_connection()

    if connection_status:
        sly.logger.info(
            f"Connection to CVAT server {g.STATE.cvat_server_address} was successful."
        )

        connected()

    else:
        sly.logger.warning(
            f"Connection to CVAT server {g.STATE.cvat_server_address} failed."
        )

        disconnected(with_error=True)
