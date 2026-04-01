import math


DEFAULT_ZOOM_LEVELS = (1.0, 2.0, 3.0, 4.0)


def snap_value_to_pixel_grid(value: float, zoom: float) -> float:
    """Snap a world-space coordinate to the screen pixel grid for the given zoom."""
    if zoom <= 0:
        return float(value)
    return round(float(value) * zoom) / zoom


def snap_world_point(x: float, y: float, zoom: float) -> tuple[float, float]:
    """Snap a world-space point to the screen pixel grid for the given zoom."""
    return (
        snap_value_to_pixel_grid(x, zoom),
        snap_value_to_pixel_grid(y, zoom),
    )


class CameraController:
    """Hybrid camera: centered follow with a pixel-snapped render position."""

    def __init__(
        self,
        camera,
        world_width: float,
        world_height: float,
        zoom_levels: tuple[float, ...] = DEFAULT_ZOOM_LEVELS,
        initial_zoom: float = 2.0,
    ):
        self.camera = camera
        self.world_width = float(world_width)
        self.world_height = float(world_height)
        self.zoom_levels = tuple(float(level) for level in zoom_levels)
        if not self.zoom_levels:
            raise ValueError("zoom_levels must not be empty")
        if any(level <= 0 for level in self.zoom_levels):
            raise ValueError("zoom_levels must contain only positive values")

        self.smoothing = 18.0
        self.zoom_index = self._find_zoom_index(initial_zoom)

        if hasattr(self.camera, "match_window"):
            self.camera.match_window()

        self.viewport_width, self.viewport_height = self._get_viewport_size()
        initial_position = getattr(self.camera, "position", (self.world_width / 2, self.world_height / 2))
        self.logical_position = (float(initial_position[0]), float(initial_position[1]))
        self._apply_camera_state()

    @property
    def zoom(self) -> float:
        return self.zoom_levels[self.zoom_index]

    def zoom_in(self) -> None:
        if self.zoom_index < len(self.zoom_levels) - 1:
            self.zoom_index += 1
        self._apply_camera_state()

    def zoom_out(self) -> None:
        if self.zoom_index > 0:
            self.zoom_index -= 1
        self._apply_camera_state()

    def on_resize(self, width: int, height: int) -> None:
        if hasattr(self.camera, "match_window"):
            self.camera.match_window()
        self.viewport_width = float(width)
        self.viewport_height = float(height)
        self._apply_camera_state()

    def update(self, target_pos: tuple[float, float], delta_time: float) -> None:
        desired_position = (float(target_pos[0]), float(target_pos[1]))
        alpha = 1.0 - math.exp(-self.smoothing * max(0.0, float(delta_time)))

        current_x, current_y = self.logical_position
        target_x, target_y = desired_position
        self.logical_position = (
            current_x + (target_x - current_x) * alpha,
            current_y + (target_y - current_y) * alpha,
        )
        self._apply_camera_state()

    def _find_zoom_index(self, initial_zoom: float) -> int:
        try:
            return self.zoom_levels.index(float(initial_zoom))
        except ValueError:
            return min(
                range(len(self.zoom_levels)),
                key=lambda idx: abs(self.zoom_levels[idx] - float(initial_zoom)),
            )

    def _get_viewport_size(self) -> tuple[float, float]:
        viewport = getattr(self.camera, "viewport", None)
        width = float(getattr(viewport, "width", 0.0) or 0.0)
        height = float(getattr(viewport, "height", 0.0) or 0.0)
        if width > 0 and height > 0:
            return width, height

        if hasattr(viewport, "size"):
            size = viewport.size
            if len(size) == 2:
                return float(size[0]), float(size[1])

        return self.world_width, self.world_height

    def _apply_camera_state(self) -> None:
        self.camera.zoom = self.zoom
        self.camera.position = snap_world_point(
            self.logical_position[0],
            self.logical_position[1],
            self.zoom,
        )
