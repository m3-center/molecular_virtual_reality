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
from chimerax.graphics.camera import Camera
from chimerax.graphics import camera
from OpenGL.GL import glColorMask, GL_TRUE, GL_FALSE

from OpenGL.GL import glColorMask, GL_TRUE, GL_FALSE, glClear, glViewport, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT
from chimerax.geometry import place
from chimerax.graphics.drawing import Drawing
from chimerax.graphics.opengl import Texture, Framebuffer
from numpy import array, float32, int32

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
        print("test1")
        camera = AnaglyphCamera()
       
        if camera is not None:
            camera.position = view.camera.position  # Preserve current camera position
            view.camera.delete()
            view.camera = camera


class AnaglyphCamera(Camera):
    '''Anaglyph stereo rendering camera.'''

    name = 'anaglyph'

    def __init__(self, layout='anaglyph', eye_separation_scene=0.9, swap_eyes=False, convergence=0):
        Camera.__init__(self)
        self.field_of_view = 30  # Horizontal field, degrees
        self.eye_separation_scene = eye_separation_scene  # Angstroms
        self.swap_eyes = swap_eyes  # Used for cross-eye stereo
        self.convergence = convergence  # Used for cross-eye and wall-eye stereo
        self._framebuffer = {'left': None, 'right': None}  # Framebuffer for rendering each eye
        self._drawing = {'left': None, 'right': None}  # Drawing of rectangle with cube map texture
        self.layout = "anaglyph"

    def delete(self):
        for fb in self._framebuffer.values():
            if fb:
                fb.delete(make_current=True)
        self._framebuffer = {}

        for d in self._drawing.values():
            d.delete()
        self._drawing = {}

    def view(self, camera_position, view_num):
        '''
        Return the Place coordinate frame for a specific camera view number.
        As a transform it maps camera coordinates to scene coordinates.
        '''
        if view_num is None:
            v = camera_position
        else:
            # Stereo eyes view in same direction with position shifted along x.
            s = -1 if view_num == 0 else 1
            es = self.eye_separation_scene
            t = place.translation((s * 0.5 * es, 0, 0))
            v = camera_position * t
            if self.convergence != 0:
                r = place.rotation((0, 1, 0), s * self.convergence)
                v = v * r
        return v

    def number_of_views(self):
        '''Number of views rendered by camera mode.'''
        return 2

    def view_all(self, bounds, window_size=None, pad=0):
        '''
        Return the shift that makes the camera completely show models
        having specified bounds.  The camera view direction is not changed.
        '''
        self.position = camera.perspective_view_all(bounds, self.position, self.field_of_view, window_size, pad)

    def ray(self, window_x, window_y, window_size):
        '''
        Return origin and direction in scene coordinates of sight line
        for the specified window pixel position.  Uses the right eye.
        '''
        w, h = window_size
        if self.layout == 'side-by-side':
            wsize = (w / 2, h)
            if window_x > w / 2:
                view_num = 1
                wx, wy = window_x - w / 2, window_y
            else:
                view_num = 0
                wx, wy = window_x, window_y
        else:
            wsize = (w, h / 2)
            if window_y > h / 2:
                view_num = 1
                wx, wy = window_x, window_y - h / 2
            else:
                view_num = 0
                wx, wy = window_x, window_y
        d = camera.perspective_direction(wx, wy, wsize, self.field_of_view)
        p = self.get_position(view_num=1)
        ds = p.transform_vector(d)  # Convert camera to scene coordinates
        return (p.origin(), ds)

    def view_width(self, point):
        return camera.perspective_view_width(point, self.position.origin(), self.field_of_view)

    def set_render_target(self, view_num, render):
        '''Set the OpenGL drawing buffer and viewport to render the scene.'''
        if view_num > 0:
            render.pop_framebuffer()  # Pop left eye framebuffer
        if self.swap_eyes:
            eye = 'right' if view_num == 0 else 'left'
        else:
            eye = 'left' if view_num == 0 else 'right'
        fb = self._eye_framebuffer(eye, render)
        render.push_framebuffer(fb)  # Push eye framebuffer

        # Clear framebuffer and apply color mask based on eye
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if eye == 'left':
            glColorMask(GL_TRUE, GL_FALSE, GL_FALSE, GL_TRUE)  # Red only
        else:
            glColorMask(GL_FALSE, GL_TRUE, GL_TRUE, GL_TRUE)  # Green and Blue (Cyan)

    def combine_rendered_camera_views(self, render):
        '''Render the cube map using a projection.'''
        render.pop_framebuffer()  # Pop the right eye framebuffer.

        # Clear the main framebuffer and reset viewport
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, *render.render_size())

        # Draw left eye
        glColorMask(GL_TRUE, GL_FALSE, GL_FALSE, GL_TRUE)
        drawings = [self._eye_drawing('left')]
        from chimerax.graphics.drawing import draw_overlays
        draw_overlays(drawings, render)

        # Draw right eye
        glColorMask(GL_FALSE, GL_TRUE, GL_TRUE, GL_TRUE)
        drawings = [self._eye_drawing('right')]
        draw_overlays(drawings, render)

        # Reset color mask to default
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

    def _eye_framebuffer(self, eye, render):
        window_size = render.render_size()
        fb = self._framebuffer[eye]
        w, h = window_size
        if fb is None or (w, h) != (fb.width, fb.height):
            if fb:
                fb.delete()
            t = Texture()
            t.initialize_rgba((w, h))
            fb = Framebuffer('stereo camera', render.opengl_context, color_texture=t)
            self._framebuffer[eye] = fb
            d = self._drawing[eye]
            if d:
                d.texture = fb.color_texture  # Update drawing texture
        return fb

    def _eye_drawing(self, eye):
        d = self._drawing[eye]
        if d is None:
            self._drawing[eye] = d = Drawing('%s eye' % eye)
            va = array(((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)), float32)
            ta = array(((0, 1, 2), (0, 2, 3)), int32)
            tc = array(((0, 0), (1, 0), (1, 1), (0, 1)), float32)
            d.set_geometry(va, None, ta)
            d.use_lighting = False
            d.texture_coordinates = tc
            d.texture = self._framebuffer[eye].color_texture
            d.opaque_texture = True
        return d