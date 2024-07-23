# vim: set expandtab shiftwidth=4 softtabstop=4:
import os
import glob
from Qt.QtCore import Qt
from Qt.QtWidgets import (
    QPushButton, QCheckBox, QHBoxLayout, QFileDialog, QVBoxLayout, QComboBox, QLabel
)

# === UCSF ChimeraX Copyright ===

# Copyright 2016 Regents of the University of California.

# All rights reserved.  This software provided pursuant to a

# license agreement containing restrictions on its disclosure,

# duplication and use.  For details see:

# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html

# This notice must be embedded in or attached to all copies,

# including partial copies, of the software or any revisions

# or derivations thereof.

# === UCSF ChimeraX Copyright ===

from chimerax.core.tools import ToolInstance
from chimerax.core.commands import run
#import default chimerax camera class
from . import anaglyphCamera

class Anaglyph(ToolInstance):
    SESSION_ENDURING = True
    SESSION_SAVE = True
    
    def __init__(self, session, tool_name):
        super().__init__(session, tool_name)
        #self.session.logger.info("init test")
        self.display_name = "Anaglyph"
        self.menu_name = "Anaglyph"

        view = session.main_view
        has_arg = False

        camera = None
        camera = anaglyphCamera.AnaglyphCamera(swap_eyes = True, convergence = 10, eye_separation_scene = 50)
        print("test 1")
        if camera is not None:
            camera.position = view.camera.position  # Preserve current camera position
            view.camera.delete()
            view.camera = camera
        print("test 2")

        cam = session.main_view.camera
        if field_of_view is not None:
            has_arg = True
            cam.field_of_view = field_of_view
            cam.redraw_needed = True
        if eye_separation is not None:
            has_arg = True
            cam.eye_separation_scene = eye_separation
            cam.redraw_needed = True
        if pixel_eye_separation is not None:
            if cam.name != 'stereo':
                from chimerax.core.errors import UserError
                raise UserError('camera pixelEyeSeparation option only applies to stereo camera mode.')
            has_arg = True
            cam.eye_separation_pixels = pixel_eye_separation
            cam.redraw_needed = True
            b = view.drawing_bounds()
            if b:
                cam.set_focus_depth(b.center(), view.window_size[0])
        if convergence is not None:
            has_arg = True
            cam.convergence = convergence
            cam.redraw_needed = True
        print("test 3")
        if not has_arg:
            lines = [
                'Camera parameters:',
                '    type: %s' % cam.name,
                '    position: %.5g %.5g %.5g' % tuple(cam.position.origin()),
                '    view direction: %.5g %.5g %.5g' % tuple(cam.view_direction())
                ]
            if hasattr(cam, 'field_of_view'):
                lines.append('    field of view: %.5g degrees' % cam.field_of_view)
            if hasattr(cam, 'field_width'):
                lines.append('    field width: %.5g' % cam.field_width)
            if hasattr(cam, 'eye_separation_scene'):
                lines.append('    eye separation in scene: %.5g' % cam.eye_separation_scene)
            if hasattr(cam, 'eye_separation_pixels'):
                lines.append('    eye separation in screen pixels: %.5g' % cam.eye_separation_pixels)
            if hasattr(cam, 'convergence'):
                lines.append('    convergence (degrees): %.5g' % cam.convergence)
            session.logger.info('\n'.join(lines))

            fields = ['%s camera' % cam.name]
            if hasattr(cam, 'field_of_view'):
                fields.append('%.5g degree field of view' % cam.field_of_view)
            session.logger.status(', '.join(fields))


    


# Register the tool with ChimeraX
# from chimerax.core.toolshed import register_tool
# register_tool("Collagen", FetcherTool)
