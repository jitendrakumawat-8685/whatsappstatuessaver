from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.video import Video
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.core.window import Window

import os
import shutil
from android.permissions import request_permissions, Permission, check_permission
from android.storage import primary_external_storage_path
from threading import Thread

# WhatsApp Status folder (Android 11+ path)
STATUS_FOLDER = os.path.join(primary_external_storage_path(), 'Android/media/com.whatsapp/WhatsApp/Media/.Statuses')
DOWNLOADS_FOLDER = os.path.join(primary_external_storage_path(), 'Download')

ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.mp4')

class StatusItem(BoxLayout):
    def __init__(self, filepath, **kwargs):
        super().__init__(orientation='vertical', size_hint_y=None, height=250, **kwargs)
        self.filepath = filepath
        self.selected = False

        ext = filepath.lower()
        ext = os.path.splitext(ext)[1]

        if ext in ('.jpg', '.jpeg', '.png'):
            img = AsyncImage(source=filepath, allow_stretch=True, keep_ratio=True)
            self.add_widget(img)
        elif ext == '.mp4':
            vid = Video(source=filepath, state='stop', options={'eos': 'stop'}, allow_stretch=True)
            self.add_widget(vid)
        else:
            self.add_widget(Label(text='Unknown format'))

        checkbox_layout = BoxLayout(size_hint_y=None, height=30)
        self.checkbox = CheckBox()
        self.checkbox.bind(active=self.on_checkbox_active)
        checkbox_layout.add_widget(self.checkbox)
        checkbox_layout.add_widget(Label(text="Select"))
        self.add_widget(checkbox_layout)

    def on_checkbox_active(self, checkbox, value):
        self.selected = value

class StatusDownloaderApp(App):
    def build(self):
        self.title = "WhatsApp Status Downloader"
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.status_grid = GridLayout(cols=2, spacing=10, size_hint_y=None)
        self.status_grid.bind(minimum_height=self.status_grid.setter('height'))

        scroll = ScrollView(size_hint=(1, 0.85))
        scroll.add_widget(self.status_grid)
        main_layout.add_widget(scroll)

        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        self.load_btn = Button(text="Load Statuses")
        self.load_btn.bind(on_release=self.load_statuses)
        btn_layout.add_widget(self.load_btn)

        self.download_btn = Button(text="Download Selected", disabled=True)
        self.download_btn.bind(on_release=self.download_selected)
        btn_layout.add_widget(self.download_btn)

        main_layout.add_widget(btn_layout)

        # Request storage permissions on app start
        self.check_permissions()

        return main_layout

    def check_permissions(self):
        def callback(permissions, grants):
            if all(grants):
                self.show_popup("Permission Granted", "Storage permissions granted!")
            else:
                self.show_popup("Permission Denied", "Storage permissions are required to run this app.")

        if not check_permission(Permission.READ_EXTERNAL_STORAGE) or not check_permission(Permission.WRITE_EXTERNAL_STORAGE):
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE], callback)
        else:
            pass  # Already have permissions

    def show_popup(self, title, message):
        popup = Popup(title=title,
                      content=Label(text=message),
                      size_hint=(0.8, 0.3))
        popup.open()

    def load_statuses(self, instance):
        self.status_grid.clear_widgets()
        if not os.path.exists(STATUS_FOLDER):
            self.show_popup("Error", "WhatsApp Status folder not found or no statuses available.")
            return

        files = [os.path.join(STATUS_FOLDER, f) for f in os.listdir(STATUS_FOLDER) if f.lower().endswith(ALLOWED_EXTENSIONS)]
        if not files:
            self.show_popup("Info", "No status files found.")
            return

        self.status_items = []
        for fpath in files:
            item = StatusItem(fpath)
            item.checkbox.bind(active=self.update_download_btn)
            self.status_grid.add_widget(item)
            self.status_items.append(item)

        self.update_download_btn()

    def update_download_btn(self, *args):
        any_selected = any(item.selected for item in getattr(self, 'status_items', []))
        self.download_btn.disabled = not any_selected

    def download_selected(self, instance):
        selected_items = [item for item in self.status_items if item.selected]
        if not selected_items:
            self.show_popup("Warning", "No files selected.")
            return

        # Download in background thread
        def do_download():
            for item in selected_items:
                filename = os.path.basename(item.filepath)
                dest = os.path.join(DOWNLOADS_FOLDER, filename)
                try:
                    shutil.copy2(item.filepath, dest)
                except Exception as e:
                    print(f"Error copying {filename}: {e}")

            self.show_popup("Success", f"Downloaded {len(selected_items)} files to Downloads.")

        Thread(target=do_download).start()

if __name__ == '__main__':
    StatusDownloaderApp().run()
