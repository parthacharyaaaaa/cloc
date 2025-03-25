import ctypes
import os

lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "line_parsing.so"))

class LineScanResult(ctypes.Structure):
    _fields_ = [("commentedBlock", ctypes.c_bool), ("isValid", ctypes.c_bool)]

lib.scanLine.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
lib.scanLine.restype = LineScanResult