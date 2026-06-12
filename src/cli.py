from blessed.keyboard import Keystroke

class CommandLineInterface:
    def __init__(self):
        self.is_active = False
        self.buffer = ""
        self.status_message = ""
        self._msg_timer = 0

    def process_key(self, key: Keystroke):
        """Procesa una tecla entrante si estamos activos o si es ':' para abrir."""
        # Limpiar mensajes temporales
        if self._msg_timer > 0:
            self._msg_timer -= 1
            if self._msg_timer <= 0:
                self.status_message = ""

        if not self.is_active:
            if key == ":":
                self.is_active = True
                self.buffer = ""
                self.status_message = ""
            return

        if key.is_sequence:
            if key.name == "KEY_ESCAPE":
                self.is_active = False
                self.buffer = ""
            elif key.name == "KEY_ENTER":
                self._execute_mock_command()
            elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
                self.buffer = self.buffer[:-1]
        else:
            if key.isprintable():
                self.buffer += key

    def _execute_mock_command(self):
        """Simula la ejecución devolviendo un error del mock."""
        if self.buffer.strip():
            self.status_message = f"Comando '{self.buffer}' no reconocido."
            self._msg_timer = 90  # Frames para mantener el mensaje en pantalla (~3 seg a 30 FPS)
        
        self.is_active = False
        self.buffer = ""

    def get_ui_bar(self, default_bar: str) -> str:
        """Devuelve el texto a renderizar para la parte inferior."""
        if self.is_active:
            return f"\n| MODO COMANDO: :{self.buffer}█"
        elif self.status_message:
            return f"\n| {self.status_message}"
        return default_bar