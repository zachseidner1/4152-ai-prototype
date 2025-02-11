import heapq
import math
import sys

import pygame

# Initialize Pygame
pygame.init()

# --------- Configuration Constants -----------
WIDTH, HEIGHT = 800, 600  # window size in pixels
CELL_SIZE = 40  # size of one grid cell (in pixels)
GRID_COLS = 14  # number of columns in the grid
GRID_ROWS = 11  # number of rows in the grid
ENEMY_RADIUS = CELL_SIZE // 2
PATROL_RADIUS = CELL_SIZE // 2

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
LIGHT_BLUE = (173, 216, 230)
LIGHT_GREEN = (200, 255, 200)

# --------- Set Up Display -----------
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Multiple Patrol Paths and Enemies")
clock = pygame.time.Clock()

# --------- Global Game State -----------
current_patrol_path = []  # the cells (as (col, row)) being defined right now
patrols = []  # list of finalized Patrol objects
target_cell = None  # the cell marked as enemy target (blue)
enemies = []  # list to hold enemy objects


# --------- Helper: Convert grid cell to pixel center -----------
def cell_center(cell):
    col, row = cell
    return (col * CELL_SIZE + CELL_SIZE // 2, row * CELL_SIZE + CELL_SIZE // 2)


# --------- A* Pathfinding Function -----------
def a_star(start, goal):
    """Computes a path from start to goal on an open grid using A*.
       Returns a list of cells (each a (col, row) tuple)."""

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    close_set = set()
    came_from = {}
    gscore = {start: 0}
    fscore = {start: heuristic(start, goal)}
    oheap = []
    heapq.heappush(oheap, (fscore[start], start))

    while oheap:
        current = heapq.heappop(oheap)[1]
        if current == goal:
            # Reconstruct path:
            data = []
            while current in came_from:
                data.append(current)
                current = came_from[current]
            data.append(start)
            data.reverse()
            return data

        close_set.add(current)
        for dx, dy in neighbors:
            neighbor = (current[0] + dx, current[1] + dy)
            if not (0 <= neighbor[0] < GRID_COLS and 0 <= neighbor[1] < GRID_ROWS):
                continue  # out of bounds
            tentative_g = gscore[current] + 1
            if neighbor in close_set and tentative_g >= gscore.get(neighbor, 0):
                continue
            if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [item[1] for item in oheap]:
                came_from[neighbor] = current
                gscore[neighbor] = tentative_g
                fscore[neighbor] = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(oheap, (fscore[neighbor], neighbor))
    return None  # no path found


# --------- Patrol Class -----------
class Patrol:
    def __init__(self, path, speed=100):
        # 'path' is a list of grid cells (col, row)
        self.path = path[:]  # make a copy of the path
        self.speed = speed  # pixels per second
        self.index = 0  # current index in the path
        self.progress = 0.0  # progress (0-1) along the current segment
        self.direction = 1  # 1 = forward along the list, -1 = backward
        self.pos = cell_center(self.path[0])

    def update(self, dt):
        if len(self.path) < 2:
            return  # nothing to patrol if only one cell
        next_index = self.index + self.direction
        # Reverse direction if at either end:
        if next_index < 0 or next_index >= len(self.path):
            next_index = self.index - self.direction
            if next_index < 0 or next_index >= len(self.path):
                return
        start_pos = cell_center(self.path[self.index])
        end_pos = cell_center(self.path[next_index])
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        segment_length = math.hypot(dx, dy)
        if segment_length == 0:
            self.index = next_index
            self.progress = 0.0
            return
        # Increase progress along the segment:
        self.progress += self.speed * dt / segment_length
        if self.progress >= 1.0:
            self.index = next_index
            self.progress -= 1.0
            next_index = self.index + self.direction
            if next_index < 0 or next_index >= len(self.path):
                self.direction *= -1
                next_index = self.index + self.direction
                if next_index < 0 or next_index >= len(self.path):
                    print("ERROR")
                    self.progress = 0.0
                    self.pos = cell_center(self.path[self.index])
                    return
            start_pos = cell_center(self.path[self.index])
            end_pos = cell_center(self.path[next_index])
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
        # Update position by linear interpolation:
        self.pos = (start_pos[0] + dx * self.progress,
                    start_pos[1] + dy * self.progress)

    def draw(self, surface):
        # Optionally draw the patrol's complete path (as a green line)
        if len(self.path) > 1:
            points = [cell_center(cell) for cell in self.path]
            pygame.draw.lines(surface, GREEN, False, points, 3)
        # Draw the patrol itself as a red circle
        pygame.draw.circle(surface, RED, (int(self.pos[0]), int(self.pos[1])), PATROL_RADIUS)


# --------- Enemy Class -----------
class Enemy:
    def __init__(self, start_cell, target_cell, speed=80):
        self.start_cell = start_cell
        self.target_cell = target_cell
        self.speed = speed
        # Compute a route (list of grid cells) using A*
        self.path = a_star(start_cell, target_cell)
        if self.path is None or len(self.path) == 0:
            self.path = [start_cell]
        self.index = 0  # current index in the path
        self.progress = 0.0  # progress along the current segment
        self.pos = cell_center(self.path[0])

    def update(self, dt):
        if len(self.path) < 2:
            return  # no path or already at destination
        next_index = self.index + 1
        if next_index >= len(self.path):
            return  # reached destination; remain here.
        start_pos = cell_center(self.path[self.index])
        end_pos = cell_center(self.path[next_index])
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        segment_length = math.hypot(dx, dy)
        if segment_length == 0:
            self.index = next_index
            self.progress = 0.0
            return
        self.progress += self.speed * dt / segment_length
        if self.progress >= 1.0:
            self.index = next_index
            self.progress -= 1.0
            if self.index >= len(self.path) - 1:
                self.pos = end_pos
                return
            start_pos = cell_center(self.path[self.index])
            end_pos = cell_center(self.path[self.index + 1])
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
        self.pos = (start_pos[0] + dx * self.progress,
                    start_pos[1] + dy * self.progress)

    def draw(self, surface):
        pygame.draw.circle(surface, BLUE, (int(self.pos[0]), int(self.pos[1])), ENEMY_RADIUS)


# --------- Main Game Loop -----------
running = True
while running:
    dt = clock.tick(60) / 1000.0  # seconds elapsed since last frame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --- Keyboard Events ---
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                # Mark the target cell (blue) under the mouse cursor.
                mouse_x, mouse_y = pygame.mouse.get_pos()
                col = mouse_x // CELL_SIZE
                row = mouse_y // CELL_SIZE
                target_cell = (col, row)
            elif event.key == pygame.K_e:
                # Spawn an enemy at the cell under the mouse cursor (if a target has been marked).
                if target_cell is not None:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    enemy = Enemy((col, row), target_cell)
                    enemies.append(enemy)
            elif event.key == pygame.K_n:
                # Finalize the current patrol path (if it has any cells) and begin a new one.
                if current_patrol_path:
                    patrols.append(Patrol(current_patrol_path))
                    current_patrol_path = []  # reset for a new patrol path

        # --- Mouse Events ---
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left-click: add cell to the current patrol path
                mouse_x, mouse_y = event.pos
                col = mouse_x // CELL_SIZE
                row = mouse_y // CELL_SIZE
                cell = (col, row)
                in_patrol_path = False
                for patrol in patrols:
                    if math.hypot(mouse_x - patrol.pos[0], mouse_y - patrol.pos[1]) < PATROL_RADIUS * 1.5:
                        patrol.direction *= -1
                        # TODO a bit scuffed but it should work?
                        patrol.index -= patrol.direction
                        patrol.progress = 1 - patrol.progress
                        in_patrol_path = True
                        print("clicked")
                if cell not in current_patrol_path and not in_patrol_path:
                    current_patrol_path.append(cell)

                    # --- Update Game Objects ---
    for patrol in patrols:
        patrol.update(dt)
    for enemy in enemies:
        enemy.update(dt)

    # --- Check for Collisions between Patrols and Enemies ---
    # If any patrol (red circle) collides with an enemy (blue circle), remove that enemy.
    for patrol in patrols:
        for enemy in enemies[:]:
            dx = patrol.pos[0] - enemy.pos[0]
            dy = patrol.pos[1] - enemy.pos[1]
            if math.hypot(dx, dy) < PATROL_RADIUS + ENEMY_RADIUS:
                enemies.remove(enemy)

    # --- Draw Everything ---
    screen.fill(WHITE)

    # Draw grid lines
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(screen, GRAY, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(screen, GRAY, (0, y), (WIDTH, y))

    # Highlight the target cell (if set) with a light-blue rectangle.
    if target_cell is not None:
        target_rect = pygame.Rect(target_cell[0] * CELL_SIZE, target_cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, LIGHT_BLUE, target_rect)

    # Draw the cells that are part of the current (unfinalized) patrol path
    for cell in current_patrol_path:
        rect = pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, LIGHT_GREEN, rect)
    # Optionally, draw lines connecting the current patrol cells if there are at least 2.
    if len(current_patrol_path) > 1:
        points = [cell_center(cell) for cell in current_patrol_path]
        pygame.draw.lines(screen, LIGHT_GREEN, False, points, 3)

    # Draw all finalized patrols
    for patrol in patrols:
        patrol.draw(screen)

    # Draw all enemies
    for enemy in enemies:
        enemy.draw(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
