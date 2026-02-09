import os
import sys
import csv
import json
import math
import subprocess
from collections import defaultdict

import numpy as np
from PIL import Image

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtOpenGL import QOpenGLShaderProgram, QOpenGLShader

from forest_view.forms import DataForm
from forest_view.io import (
    readCSV,
    CSV_to_dict,
    writeCSV,
    readJSON,
    writeJSON,
    export_photo_info_to_csv,
)
from forest_view.photo_pipeline import (
    get_valid_pairs,
    stitch_photos,
    get_photo_locations,
    quaternion_to_euler,
)
from forest_view.widgets import (
    GLWidget,
    CustomMapWidget,
    ProprietyWidget,
    PhotoPoint,
    TreePoint,
    Pointer,
)
