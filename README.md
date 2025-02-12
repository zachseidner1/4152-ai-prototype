# CS 4152 AI Prototype

## Instructions

### Gameplay

Press `M` to toggle between "Tetromino Selection" mode and "main" mode. This allows you to select different Tetrominos
and place them on the
map. While placing Tetrominos, you can press `R` to rotate them 90 degrees. Once you are done preparation, press `Enter`
to start the level. Throughout the level you can continue placing
Tetrominos and defend. The enemies will spawn exponentially faster throughout the level.

By clicking on the grid, you can also draw patrol paths. Once you have a path selected you want to place, press `N` to
finalize it.

Press `/` to clear the gameboard (not `R` because I didn't want this to happen accidentally if you wanted to rotate
a Tetris piece)

Press `K` to clear a path you are currently in-progress of drawing.

### Level creation

While hovering over grid cells:

- Press `B` to place a barricade
- Press `T` to set the target for the enemies
- Press `W` to create a waypoint
    - Each enemy has a random chance to be required to hit a random waypoint when it spawns. Waypoints are marked by
      small yellow circles on the map and they can be used to vary the enemy paths.
- Press `V` to place a vent
    - Enemy spawn point
- Press `E` to export your level, which will save location of barricades, waypoints, target and vents to a JSON file,
  the file name is by default `level_export.json` but this can be modified by changing the `EXPORT_PATH` variable.
- Press `L` to load your level, which will by default load a level stored in `level.json`, but can be modified by
  changing the `LOAD_PATH` variable.

### Parameters to tune

The parameters to tune are listed at the top of `main.py`, you should have no problem changing those values to whatever
you want. Their names should explain themselves. Keep in mind you can change the grid size as well if you want to make
layouts for different grid sizes.