from datetime import datetime

from PIL import Image
from PIL import ImageOps

from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform
from kivy.uix.camera import Camera

try:
    from plyer import gyroscope
except ModuleNotFoundError:
    gyroscope = None


class CameraClick(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._request_android_permissions()
        self.camera = Camera(play=False, resolution=(640, 480))
        self.camera._camera.bind(on_texture=self.capture)
        if self.is_android():
            gyroscope.enable()
            Clock.schedule_interval(self.get_rotation, 1 / 10)

    def get_rotation(self, dt):
        if self.camera.play:  # Already taking photos :)
            return
        if gyroscope.rotation != (None, None, None):
            x, y, z = gyroscope.rotation
            z = round(z, 2)
            if abs(z) > 0.05:
                Logger.info(f"Motion detected! - {z}")
                self.play()

    def play(self, dt=None):
        Logger.info(f"PLAY: {dt}")
        Clock.schedule_once(self.stop, 120)
        self.camera.play = True

    def stop(self, dt=None):
        Logger.info(f"STOP: {dt}")
        self.camera.play = False

    def is_android(self):
        return platform == 'android'

    def _fix_android_image(self, pil_image):
        """
        On Android, the image seems mirrored and rotated somehow, refs zbarcam #32.
        """
        if not self.is_android():
            return pil_image
        pil_image = pil_image.rotate(270)
        pil_image = ImageOps.mirror(pil_image)
        return pil_image

    def _request_android_permissions(self):
        """
        Requests CAMERA permission on Android.
        """
        if not self.is_android():
            return
        from android.permissions import request_permission, Permission
        request_permission(Permission.CAMERA)

    def photo(self, texture):
        image_data = texture.pixels
        size = texture.size
        fmt = texture.colorfmt.upper()

        time_str = datetime.now().strftime('%Y%m%d_%H:%M:%S.%f')[:-3]
        pil_image = Image.frombytes(mode=fmt, size=size, data=image_data)
        pil_image = self._fix_android_image(pil_image)
        pil_image.save("IMG_{}.png".format(time_str))
        Logger.info("Captured")

    def capture(self, instance):
        camera = instance
        self.photo(camera.texture)


class TestCamera(App):
    def build(self):
        return CameraClick()


if __name__ == '__main__':
    app = TestCamera()
    app.run()
