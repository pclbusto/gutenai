import os
os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"  # evita GBM/DMABUF
# opcional: forzar X11 en vez de Wayland
# os.environ["GDK_BACKEND"] = "x11"

import tkinter as tk
import webview
import pathlib

root = tk.Tk()
root.geometry("1000x700")
root.title("Tk + Webview")

# ruta local -> file://
html_path = pathlib.Path("test.html").resolve().as_uri()
wv = webview.create_window("Preview HTML", html_path)  # o html="<h1>hola</h1>"
webview.start(gui='tkinter')
