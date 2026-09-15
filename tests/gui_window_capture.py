"""Capture a Tk window drawable on WSLg, whose root drawable is not readable."""
import ctypes as C
from PIL import Image
class XImage(C.Structure):
 _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong)]
def capture(widget,path):
 lib=C.CDLL('libX11.so.6');lib.XOpenDisplay.restype=C.c_void_p
 display=lib.XOpenDisplay(None)
 lib.XGetImage.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int];lib.XGetImage.restype=C.POINTER(XImage)
 image=lib.XGetImage(display,widget.winfo_id(),0,0,widget.winfo_width(),widget.winfo_height(),C.c_ulong(-1),2)
 if not image:raise RuntimeError('Cannot capture drawable')
 info=image.contents
 raw=C.string_at(info.data,info.bytes_per_line*info.height)
 Image.frombytes('RGB',(info.width,info.height),raw,'raw','BGRX',info.bytes_per_line,1).save(path)
 lib.XDestroyImage.argtypes=[C.POINTER(XImage)];lib.XDestroyImage(image)
 lib.XCloseDisplay.argtypes=[C.c_void_p];lib.XCloseDisplay(display)
