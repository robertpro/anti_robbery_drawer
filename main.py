from kivy.logger import Logger
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform
import time
import PIL
from PIL import ImageOps
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
        if gyroscope:
            gyroscope.enable()
            Clock.schedule_interval(self.get_rotation, 1 / 10)
        self.taking_photos = False

    def get_rotation(self, dt):
        if self.taking_photos:
            return
        if gyroscope.rotation != (None, None, None):
            x, y, z = gyroscope.rotation
            z = round(z, 2)
            if abs(z) > 0.05:
                Logger.info(f"Motion detected! - {z}")
                self.play()

    def play(self, dt=None):
        print(f"PLAY: {dt}")
        self.camera.play = True
        Clock.schedule_once(self.stop, 10)
        self.taking_photos = True

    def stop(self, dt=None):
        print(f"STOP: {dt}")
        self.camera.play = False
        self.taking_photos = False

    def is_android(self):
        return platform == 'android'

    def _fix_android_image(self, pil_image):
        """
        On Android, the image seems mirrored and rotated somehow, refs #32.
        """
        if not self.is_android():
            return pil_image
        pil_image = pil_image.rotate(180)
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

    def capture(self, instance=None):
        camera = instance or self.camera
        print(type(camera), camera)
        texture = camera.texture
        image_data = texture.pixels
        size = texture.size
        fmt = texture.colorfmt.upper()
        timestr = time.strftime("%Y%m%d_%H%M%S")
        pil_image = PIL.Image.frombytes(mode=fmt, size=size, data=image_data)
        pil_image = self._fix_android_image(pil_image)
        pil_image.save("IMG_{}.png".format(timestr))
        print("Captured")


class TestCamera(App):
    def build(self):
        return CameraClick()


if __name__ == '__main__':
    app = TestCamera()
    app.run()
