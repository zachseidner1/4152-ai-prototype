# CS 4152 AI Prototype

## Instructions

### Gameplay

Press `M` to enter the "Tetromino Selection" mode. This allows you to select different Tetrominos and place them on the
map. While placing Tetrominos, you can press `R` to rotate them 90 degrees. Once you are done preparation, press `Enter`
to start the level. Throughout the level you can continue placing
Tetrominos and defend. The enemies will spawn exponentially faster throughout the level.

By clicking on the grid, you can also draw patrol paths.

### Level creation

While hovering over grid cells:

- Press `B` to place a barricade
- Press `T` to set the target for the enemies
- Press `W` to create a waypoint
    - Each enemy has a random chance to be required to hit a random waypoint when it spawns. Waypoints are marked by
      small yellow circles on the map and they can be used to vary the enemy paths.
- Press `V` to place a vent
    - Enemy spawn point