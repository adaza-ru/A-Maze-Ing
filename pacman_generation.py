import mazegenerator.mazegenerator as mg

# 1. Generar el laberinto
maze_gen = mg.MazeGenerator()
maze_gen.generate()

nombre_archivo = "pacman.txt"

# 2. Guardar convirtiendo a hexadecimal y pegando los caracteres
with open(nombre_archivo, "w") as f:
    for fila in maze_gen.maze:
        # {:x} convierte el número a hexadecimal
        # Ejemplo: 10 -> a, 11 -> b, 15 -> f
        linea_hex = "".join("{:X}".format(n) for n in fila)
        f.write(linea_hex + "\n")
    f.write(f"\n{maze_gen.maze_entry[0]},{maze_gen.maze_entry[1]}\n")
    f.write(f"{maze_gen.maze_exit[0]},{maze_gen.maze_exit[1]}\n")
    f.write(f"{maze_gen.shortest_path}\n\n")

print(f"¡Listo! Archivo '{nombre_archivo}' generado en formato hexadecimal.")
