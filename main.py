"""
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.properties import NumericProperty
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.core.audio import SoundLoader


def play_sound():
    sound = SoundLoader.load('beep.ogg')
    if sound:
        sound.play()


class GyroscopeInterface(BoxLayout):
    z_calib = NumericProperty(0)

    facade = ObjectProperty()

    def enable(self):
        self.facade.enable()
        Clock.schedule_interval(self.get_rotation, 1 / 10)

    def disable(self):
        self.facade.disable()
        Clock.unschedule(self.get_rotation)

    def get_rotation(self, dt):
        if self.facade.rotation != (None, None, None):
            x, y, z = self.facade.rotation
            self.z_calib = round(z, 2)
            if abs(self.z_calib) > 0.05:
                # play_sound()
                self.take_photos()
                Logger.info(f"Motion detected! - {self.z_calib}")


class GyroscopeTestApp(App):
    def build(self):
        return GyroscopeInterface()


if __name__ == "__main__":
    GyroscopeTestApp().run()
"""

import os

import PIL
from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ListProperty
from kivy.uix.anchorlayout import AnchorLayout
from kivy.utils import platform
from PIL import ImageOps
import time

MODULE_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

kv = """
#:import XCamera kivy.garden.xcamera.XCamera
<ZBarCam>:
    Widget:
        # invert width/height on rotated Android
        # https://stackoverflow.com/a/45192295/185510
        id: proxy
        XCamera:
            id: xcamera
            play: True
            resolution: root.resolution
            allow_stretch: True
            keep_ratio: True
            center: self.size and proxy.center
            size:
                (proxy.height, proxy.width) if root.is_android() \
                else (proxy.width, proxy.height)
            # Android camera rotation workaround, refs:
            # https://github.com/AndreMiras/garden.zbarcam/issues/3
            canvas.before:
                PushMatrix
                Rotate:
                    angle: -90 if root.is_android() else 0
                    origin: self.center
            canvas.after:
                PopMatrix
"""


class ZBarCam(AnchorLayout):
    """
    Widget that use the Camera and zbar to detect qrcode.
    When found, the `codes` will be updated.
    """
    resolution = ListProperty([640, 480])

    def __init__(self, **kwargs):
        self._request_android_permissions()
        # lazy loading the kv file rather than loading at module level,
        # that way the `XCamera` import doesn't happen too early
        super(ZBarCam, self).__init__(**kwargs)
        Builder.load_string(kv)
        Clock.schedule_once(lambda dt: self._setup())

    def _setup(self):
        """
        Postpones some setup tasks that require self.ids dictionary.
        """
        self._remove_shoot_button()
        self._enable_android_autofocus()
        self.xcamera._camera.bind(on_texture=self._on_texture)
        # self.add_widget(self.xcamera)

    def _remove_shoot_button(self):
        """
        Removes the "shoot button", see:
        https://github.com/kivy-garden/garden.xcamera/pull/3
        """
        xcamera = self.xcamera
        shoot_button = xcamera.children[0]
        xcamera.remove_widget(shoot_button)

    def _enable_android_autofocus(self):
        """
        Enables autofocus on Android.
        """
        if not self.is_android():
            return
        camera = self.xcamera._camera._android_camera
        params = camera.getParameters()
        params.setFocusMode('continuous-video')
        camera.setParameters(params)

    def _request_android_permissions(self):
        """
        Requests CAMERA permission on Android.
        """
        if not self.is_android():
            return
        from android.permissions import request_permission, Permission
        request_permission(Permission.CAMERA)

    @classmethod
    def _fix_android_image(cls, pil_image):
        """
        On Android, the image seems mirrored and rotated somehow, refs #32.
        """
        if not cls.is_android():
            return pil_image
        pil_image = pil_image.rotate(90)
        pil_image = ImageOps.mirror(pil_image)
        return pil_image

    def _on_texture(self, instance):
        texture = instance.texture
        image_data = texture.pixels
        size = texture.size
        fmt = texture.colorfmt.upper()
        # PIL doesn't support BGRA but IOS uses BGRA for the camera
        # if BGRA is detected it will switch to RGBA, color will be off
        # but we don't care as it's just looking for barcodes
        if self.is_ios() and fmt == 'BGRA':
            fmt = 'RGBA'
        pil_image = PIL.Image.frombytes(mode=fmt, size=size, data=image_data)
        pil_image = self._fix_android_image(pil_image)
        timestr = time.strftime("%Y%m%d_%H%M%S")
        pil_image.save(f"img_{timestr}.bmp")

    @property
    def xcamera(self):
        return self.ids['xcamera']

    def start(self):
        self.xcamera.play = True

    def stop(self):
        self.xcamera.play = False

    @staticmethod
    def is_android():
        return platform == 'android'

    @staticmethod
    def is_ios():
        return platform == 'ios'


DEMO_APP_KV_LANG = '''
BoxLayout:
    orientation: 'vertical'
    ZBarCam:
        id: zbarcam
    Label:
        size_hint: None, None
        size: self.texture_size[0], 50
'''


class DemoApp(App):

    def build(self):
        return Builder.load_string(DEMO_APP_KV_LANG)


if __name__ == '__main__':
    DemoApp().run()
