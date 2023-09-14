import supervisely as sly

from supervisely.app.widgets import Container

import src.globals as g
import src.ui.keys as keys
import src.ui.selection as selection

layout = Container(widgets=[keys.card, selection.card])

app = sly.Application(layout=layout, static_dir=g.STATIC_DIR)
