
from mazegen.generator import MazeGenerator


def test():
    # Creamos un laberinto de 20x15 (suficiente para que quepa el 42)
    width, height = 15,15
    maze = MazeGenerator(width, height, seed=42)

    print(f"Generando laberinto {width}x{height} con DFS...")
    maze.generator(algorithm="dfs")

    # Comprobamos si las celdas del "42" siguen intactas (deben valer 15)
    all_ok = True
    for x, y in maze.reserve_cell:
        if maze.grid[y][x] != 15:
            all_ok = False
            print(f"Error: La celda del 42 en ({x}, {y}) fue modificada!")

    if all_ok and len(maze.reserve_cell) > 0:
        print("✅ ¡Éxito! Las celdas del '42' están intactas.")
    elif len(maze.reserve_cell) == 0:
        print("⚠️ El laberinto es demasiado pequeño para el '42'.")

    # Imprimimos una vista rápida en terminal (muy básica)
    for row in maze.grid:
        # Convertimos cada número a hexadecimal para ver cómo queda
        print(" ".join(f"{cell:x}" for cell in row))


if __name__ == "__main__":
    test()
