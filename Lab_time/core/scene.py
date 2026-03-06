class Scene:
    def handle_event(self, event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, screen):
        pass


class SceneManager:
    def __init__(self, start_scene: Scene):
        self.scene = start_scene

    def switch(self, new_scene: Scene):
        self.scene = new_scene
