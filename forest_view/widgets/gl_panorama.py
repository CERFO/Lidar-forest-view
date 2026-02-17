import ctypes
import math
import os

import numpy as np
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_FLOAT,
    GL_LINEAR,
    GL_RGB,
    GL_STATIC_DRAW,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TRIANGLES,
    GL_UNSIGNED_BYTE,
    GL_VERTEX_ARRAY,
    glBindBuffer,
    glBindTexture,
    glBindVertexArray,
    glBufferData,
    glClear,
    glDrawArrays,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenTextures,
    glGenVertexArrays,
    glGetString,
    glTexImage2D,
    glTexParameteri,
    glVertexAttribPointer,
    glViewport,
)
from PIL import Image
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QMatrix4x4
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from forest_view.logger import get_logger

logger = get_logger(__name__)


def _sizeof(ctype):
    return ctypes.sizeof(ctype)


class GLWidget(QOpenGLWidget):
    """Visionneuse de photos 3D (équirectangulaire) utilisant OpenGL."""
    new_camera_direction = pyqtSignal(object)
    new_pointer_direction = pyqtSignal(float)
    texture_pending = False

    def __init__(self, parent, photo_dir):
        super().__init__(parent)
        self.image = Image.new('RGB', (100, 50), color='gray')
        self.image_width, self.image_height = self.image.size
        self.yaw = 0
        self.pitch = 0
        self.image_roll = 0
        self.prev_dx = 0
        self.prev_dy = 0
        self.fov = 90
        self.moving = False
        self.main_window = parent
        self.photo_dir = photo_dir

    def load_image(self, image_path, image_yaw=0, image_pitch=0, image_roll=0):
        """Charge une nouvelle image panorama."""
        if image_path:
            try:
                self.image = Image.open(os.path.join(self.photo_dir, image_path))
                self.image_width, self.image_height = self.image.size
                if hasattr(self, 'texture'):
                    self.texture_pending = True
                self.model.setToIdentity()
                self.model.rotate(image_roll, 0, 0, 1)
                self.model.rotate(image_pitch, 1, 0, 0)
                self.model.rotate(image_yaw, 0, 1, 0)
                self.update()
                print(f"Loaded image: {image_path}")
                logger.info(f"Loaded image: {image_path}")
            except Exception as e:
                print(f"Error loading image {image_path}: {e}")
                logger.info(f"Error loading image {image_path}: {e}")
        else:
            self.image = Image.new('RGB', (100, 50), color='gray')
            self.image_width, self.image_height = self.image.size
            if hasattr(self, 'texture'):
                self.texture_pending = True
            self.yaw = 0
            self.model.setToIdentity()
            self.update()
            print("Loaded image: (none)")
            logger.info("Loaded image: (none)")

    def initializeGL(self):
        from OpenGL import GL
        print("OpenGL version:", glGetString(GL.GL_VERSION))
        logger.info("OpenGL version: %s", glGetString(GL.GL_VERSION))
        print("GLSL version:", glGetString(GL.GL_SHADING_LANGUAGE_VERSION))
        logger.info("GLSL version: %s", glGetString(GL.GL_SHADING_LANGUAGE_VERSION))

        self.program = QOpenGLShaderProgram(self)
        self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Vertex,
            "#version 450\n"
            "layout(location = 0) in vec3 position;\n"
            "layout(location = 1) in vec2 texcoord;\n"
            "uniform mat4 MVP;\n"
            "out vec2 vTex;\n"
            "void main() { vTex = texcoord; gl_Position = MVP * vec4(position, 1.0); }\n"
        )
        self.program.addShaderFromSourceCode(
            QOpenGLShader.ShaderTypeBit.Fragment,
            "#version 450\n"
            "in vec2 vTex;\n"
            "out vec4 fragColor;\n"
            "uniform sampler2D tex;\n"
            "void main() { fragColor = texture(tex, vTex); }\n"
        )
        self.program.link()
        self.mvp_loc = self.program.uniformLocation("MVP")

        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGB,
            self.image_width, self.image_height,
            0, GL_RGB, GL_UNSIGNED_BYTE,
            self.image.tobytes()
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        self.vao, self.vbo, self.vertex_count = self._create_sphere(100.0, 100, 100)
        self.model = QMatrix4x4()
        self.view = QMatrix4x4()
        self.projection = QMatrix4x4()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.view.setToIdentity()
        self.view.rotate(self.pitch, 1, 0, 0)
        self.view.rotate(self.yaw, 0, 1, 0)
        mvp = self.projection * self.view * self.model
        self.program.bind()
        self.program.setUniformValue(self.mvp_loc, mvp)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        if self.texture_pending:
            glTexImage2D(
                GL_TEXTURE_2D, 0, GL_RGB,
                self.image_width, self.image_height,
                0, GL_RGB, GL_UNSIGNED_BYTE,
                self.image.tobytes()
            )
            self.texture_pending = False
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.vertex_count)
        glBindVertexArray(0)
        self.program.release()

    def resizeGL(self, width, height):
        height = max(1, height)
        glViewport(0, 0, width, height)
        self.projection.setToIdentity()
        self.projection.perspective(self.fov, width / height, 0.1, 1000.0)

    def reset(self):
        self.yaw = 0
        self.pitch = 0
        self.image_roll = 0
        self.load_image(None)
        self.photo_dir = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._saved_cursor = self.cursor()
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            self.mouse_x, self.mouse_y = event.pos().x(), event.pos().y()
            self.moving = True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(getattr(self, '_saved_cursor', QCursor(Qt.CursorShape.ArrowCursor)))
            self.moving = False
            roll = math.radians(self.image_roll)
            pitch = math.radians(self.pitch)
            yaw = math.radians(self.yaw)
            camera_direction = np.array([
                math.cos(pitch) * math.sin(yaw),
                math.cos(pitch) * math.cos(yaw),
                -math.sin(pitch)
            ])
            self.new_camera_direction.emit(camera_direction)

    def mouseMoveEvent(self, event):
        if self.moving:
            dx = (event.pos().x() - self.mouse_x) * 0.1
            dy = (event.pos().y() - self.mouse_y) * 0.1
            self.yaw += dx
            self.pitch += dy
            self.pitch = min(max(self.pitch, -90), 90)
            self.mouse_x, self.mouse_y = event.pos().x(), event.pos().y()
            self.update()
            self.new_pointer_direction.emit(self.yaw)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self.fov -= delta * 0.1
        self.fov = max(30, min(self.fov, 90))
        self.projection.setToIdentity()
        self.projection.perspective(self.fov, self.width() / self.height(), 0.1, 1000.0)
        self.update()

    def _create_sphere(self, radius, rings, sectors):
        vertices = []
        for r in range(rings):
            for s in range(sectors):
                for dr, ds in [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]:
                    R = (r + dr) / rings
                    S = (s + ds) / sectors
                    theta = R * math.pi
                    phi = S * 2 * math.pi
                    x = radius * math.sin(theta) * math.cos(phi)
                    y = radius * math.cos(theta)
                    z = radius * math.sin(theta) * math.sin(phi)
                    vertices.extend([x, y, z, S, R])
        GLfloat = ctypes.c_float
        data = (GLfloat * len(vertices))(*vertices)
        stride = 5 * ctypes.sizeof(GLfloat)
        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, len(data) * ctypes.sizeof(GLfloat), data, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        glBindVertexArray(0)
        return vao, vbo, len(vertices) // 5
