import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sv.core.camera_controller import CameraController, snap_world_point


class DummyViewport:
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    @property
    def size(self):
        return self.width, self.height


class DummyCamera:
    def __init__(self, width: float, height: float, position=(0.0, 0.0), zoom: float = 1.0):
        self.viewport = DummyViewport(width, height)
        self.position = position
        self.zoom = zoom
        self.match_window_calls = 0

    def match_window(self):
        self.match_window_calls += 1


class CameraControllerTests(unittest.TestCase):
    def test_snap_world_point_uses_pixel_grid_for_zoom(self):
        snapped = snap_world_point(10.2, 5.49, 3.0)
        self.assertAlmostEqual(snapped[0] * 3.0, round(snapped[0] * 3.0))
        self.assertAlmostEqual(snapped[1] * 3.0, round(snapped[1] * 3.0))
        self.assertEqual(snapped, (10.333333333333334, 5.333333333333333))

    def test_camera_tracks_target_position_when_center_follow_is_active(self):
        camera = DummyCamera(200, 100, position=(200.0, 200.0), zoom=2.0)
        controller = CameraController(camera, world_width=1000, world_height=1000, initial_zoom=2.0)
        controller.smoothing = 1000.0

        controller.update((210.0, 205.0), 1.0)

        self.assertEqual(controller.logical_position, (210.0, 205.0))
        self.assertEqual(camera.position, (210.0, 205.0))

    def test_camera_can_follow_beyond_world_bounds(self):
        camera = DummyCamera(200, 100, position=(150.0, 150.0), zoom=1.0)
        controller = CameraController(camera, world_width=300, world_height=300, initial_zoom=1.0)
        controller.smoothing = 1000.0

        controller.update((1000.0, 1000.0), 1.0)

        self.assertEqual(controller.logical_position, (1000.0, 1000.0))
        self.assertEqual(camera.position, (1000.0, 1000.0))

    def test_camera_does_not_recenter_small_world(self):
        camera = DummyCamera(400, 300, position=(10.0, 10.0), zoom=1.0)
        controller = CameraController(camera, world_width=120, world_height=90, initial_zoom=1.0)

        self.assertEqual(controller.logical_position, (10.0, 10.0))
        self.assertEqual(camera.position, (10.0, 10.0))

        controller.on_resize(500, 350)

        self.assertEqual(controller.logical_position, (10.0, 10.0))
        self.assertEqual(camera.position, (10.0, 10.0))

    def test_zoom_switches_only_between_discrete_steps(self):
        camera = DummyCamera(200, 100, position=(200.0, 200.0), zoom=2.0)
        controller = CameraController(camera, world_width=1000, world_height=1000, initial_zoom=2.0)

        controller.zoom_in()
        self.assertEqual(controller.zoom, 3.0)
        controller.zoom_in()
        self.assertEqual(controller.zoom, 4.0)
        controller.zoom_in()
        self.assertEqual(controller.zoom, 4.0)

        controller.zoom_out()
        self.assertEqual(controller.zoom, 3.0)
        controller.zoom_out()
        self.assertEqual(controller.zoom, 2.0)
        controller.zoom_out()
        self.assertEqual(controller.zoom, 1.0)
        controller.zoom_out()
        self.assertEqual(controller.zoom, 1.0)


if __name__ == "__main__":
    unittest.main()
