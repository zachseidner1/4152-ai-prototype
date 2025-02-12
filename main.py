import heapq
import math
import random
import sys
from collections import deque

import pygame

# Initialize Pygame
pygame.init()

# --------- Configuration Constants -----------
# Grid stuff
CELL_SIZE = 40  # size of one grid cell (in pixels)
GRID_COLS = 14  # number of columns in the grid
GRID_ROWS = 11  # number of rows in the grid
WIDTH, HEIGHT = CELL_SIZE * GRID_COLS, CELL_SIZE * GRID_ROWS  # window size in pixels
# Enemy attributes
ENEMY_RADIUS = CELL_SIZE // 2
DEFAULT_ENEMY_SPEED = 20
# Patrol attributes
PATROL_RADIUS = CELL_SIZE // 2
PATROL_SLEEP_TIME = 5.0
DEFAULT_PATROL_SPEED = 40
# Vents
vent_spawn_interval = 5.0  # seconds between spawns from vents

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
LIGHT_BLUE = (173, 216, 230)
LIGHT_GREEN = (200, 255, 200)
BROWN = (139, 69, 19)  # for barricades
VENT_COLOR = (255, 165, 0)  # orange for vents
YELLOW = (255, 255, 0)  # for waypoints

# --------- Set Up Display -----------
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("90° Patrol Paths with Tetromino Patrols")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

# --------- Global Game State -----------
current_patrol_path = []  # manually created patrol cells (if any)
patrols = []  # finalized Patrol objects
enemies = []  # enemy objects
barricades = set()  # grid cells (as (col, row)) that are barricaded
vents = set()  # grid cells that have vents
waypoints = []  # NEW: grid cells (as (col, row)) that have been marked as waypoints
time_since_spawn_decreased = 0

# --- New: Variables for vent enemy spawning ---
spawn_from_vents = False  # when True, enemies spawn periodically from vents
vent_spawn_timer = 0.0  # timer for vent enemy spawn interval

# --- New: Tetromino Purchasing State ---
# The game runs in one of three modes:
#   "main"            – the usual game screen,
#   "tetromino_select"– a screen that shows one tetromino plus two buttons,
#   "tetromino_place" – the main screen with the purchased tetromino following the mouse.
game_mode = "main"  # initial mode

# A list of tetromino “templates.” Each has a name, a list of cell coordinates (relative to an origin)
# and a color for drawing.
tetrominoes = [
    {"name": "I", "cells": [(0, 0), (1, 0), (2, 0), (3, 0)], "color": (0, 255, 255)},
    {"name": "O", "cells": [(0, 0), (1, 0), (0, 1), (1, 1)], "color": (255, 255, 0)},
    {"name": "T", "cells": [(1, 0), (0, 1), (1, 1), (2, 1)], "color": (128, 0, 128)},
    {"name": "S", "cells": [(1, 0), (2, 0), (0, 1), (1, 1)], "color": (0, 255, 0)},
    {"name": "Z", "cells": [(0, 0), (1, 0), (1, 1), (2, 1)], "color": (255, 0, 0)},
    {"name": "J", "cells": [(0, 0), (0, 1), (1, 1), (2, 1)], "color": (0, 0, 255)},
    {"name": "L", "cells": [(2, 0), (0, 1), (1, 1), (2, 1)], "color": (255, 165, 0)}
]
current_tetromino_index = 0  # which tetromino is currently shown
purchased_tetromino = None  # once “purchased” this holds the tetromino to be placed
target_cell = None


# --------- Helper: Convert grid cell to pixel center -----------
def cell_center(cell):
    col, row = cell
    return col * CELL_SIZE + CELL_SIZE // 2, row * CELL_SIZE + CELL_SIZE // 2


# --------- A* Pathfinding Function -----------
def a_star(start, goal):
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
            if neighbor in barricades:
                continue  # cannot pass through barricades!
            tentative_g = gscore[current] + 1
            if neighbor in close_set and tentative_g >= gscore.get(neighbor, 0):
                continue
            if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [item[1] for item in oheap]:
                came_from[neighbor] = current
                gscore[neighbor] = tentative_g
                fscore[neighbor] = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(oheap, (fscore[neighbor], neighbor))
    return None


# --------- NEW: Compute an ordered patrol path that stays inside a shape using BFS ---------
def compute_patrol_path(cells):
    """
    Given a set (or list) of grid cells (each a tuple (col, row)) that form a contiguous shape,
    return an ordering (a list of cells) that covers the shape by moving only horizontally
    or vertically. This BFS finds a minimal route (allowing repeated visits) that covers all cells.
    """
    cells_set = frozenset(cells)
    queue = deque()
    # Start from each cell as a potential starting point.
    for start in cells:
        queue.append((start, frozenset({start}), [start]))
    visited_states = set()
    while queue:
        current, visited, path = queue.popleft()
        if visited == cells_set:
            return path
        state = (current, visited)
        if state in visited_states:
            continue
        visited_states.add(state)
        # Try all 4 cardinal moves.
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nxt = (current[0] + dx, current[1] + dy)
            if nxt in cells_set:
                new_visited = visited | {nxt}
                new_path = path + [nxt]
                queue.append((nxt, new_visited, new_path))
    # Fallback: just return the cells in arbitrary order.
    return list(cells)


# --------- NEW: Helper function to rotate tetromino cells by 90° clockwise ---------
def rotate_tetromino_cells(cells):
    """
    Rotate the list of (x,y) tuples 90° clockwise about the origin,
    then normalize so that the smallest x and y are 0.
    """
    # Rotation: (x, y) -> (y, -x)
    rotated = [(y, -x) for (x, y) in cells]
    min_x = min(x for (x, y) in rotated)
    min_y = min(y for (x, y) in rotated)
    normalized = [(x - min_x, y - min_y) for (x, y) in rotated]
    return normalized


# --------- Patrol Class -----------
class Patrol:
    def __init__(self, path, speed=DEFAULT_PATROL_SPEED):
        # The path is assumed to be an ordered list of grid cells in which consecutive cells
        # are connected by a horizontal or vertical move.
        self.path = path[:]
        self.speed = speed  # pixels per second
        self.index = 0  # current index in the path list
        self.progress = 0.0  # progress along the segment (0–1)
        self.direction = 1  # 1 = forward, -1 = backward
        self.pos = cell_center(self.path[0])
        self.sleep_timer = 0.0  # When > 0, the patrol is "asleep" and stops moving.

    def update(self, dt):
        # If asleep, decrement the sleep timer and do not update movement.
        if self.sleep_timer > 0:
            self.sleep_timer -= dt
            if self.sleep_timer < 0:
                self.sleep_timer = 0
            return

        if len(self.path) < 2:
            return
        next_index = self.index + self.direction
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
        self.progress += self.speed * dt / segment_length
        if self.progress >= 1.0:
            self.index = next_index
            self.progress -= 1.0
            next_index = self.index + self.direction
            if next_index < 0 or next_index >= len(self.path):
                self.direction *= -1
                next_index = self.index + self.direction
                if next_index < 0 or next_index >= len(self.path):
                    self.progress = 0.0
                    self.pos = cell_center(self.path[self.index])
                    return
            start_pos = cell_center(self.path[self.index])
            end_pos = cell_center(self.path[next_index])
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
        self.pos = (start_pos[0] + dx * self.progress,
                    start_pos[1] + dy * self.progress)

    def draw(self, surface):
        # Draw the entire path in green.
        if len(self.path) > 1:
            points = [cell_center(cell) for cell in self.path]
            pygame.draw.lines(surface, GREEN, False, points, 3)
        # Draw the patrol as a red circle. If asleep, draw it semi-transparent.
        if self.sleep_timer > 0:
            # Create a temporary surface with per-pixel alpha.
            temp_surf = pygame.Surface((PATROL_RADIUS * 2, PATROL_RADIUS * 2), pygame.SRCALPHA)
            pygame.draw.circle(temp_surf, (255, 0, 0, 128), (PATROL_RADIUS, PATROL_RADIUS), PATROL_RADIUS)
            surface.blit(temp_surf, (int(self.pos[0] - PATROL_RADIUS), int(self.pos[1] - PATROL_RADIUS)))
        else:
            pygame.draw.circle(surface, RED, (int(self.pos[0]), int(self.pos[1])), PATROL_RADIUS)


# --------- Enemy Class -----------
class Enemy:
    def __init__(self, start_cell, speed=DEFAULT_ENEMY_SPEED):
        global target_cell, waypoints
        self.start_cell = start_cell
        self.speed = speed
        # If a target is defined, sometimes (50% chance) choose a waypoint first.
        if target_cell is None:
            self.path = [start_cell]
        else:
            if waypoints and random.random() < 0.5:
                chosen_wp = random.choice(waypoints)
                path_to_wp = a_star(start_cell, chosen_wp)
                path_from_wp = a_star(chosen_wp, target_cell)
                if path_to_wp is not None and path_from_wp is not None:
                    # Avoid duplicating the waypoint cell.
                    self.path = path_to_wp[:-1] + path_from_wp
                else:
                    self.path = a_star(start_cell, target_cell)
            else:
                self.path = a_star(start_cell, target_cell)
        if self.path is None or len(self.path) == 0:
            self.path = [start_cell]
        self.index = 0
        self.progress = 0.0
        self.pos = cell_center(self.path[0])

    def update(self, dt):
        if len(self.path) < 2:
            return
        next_index = self.index + 1
        if next_index >= len(self.path):
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


# --------- Drawing Helper Functions -----------
def draw_grid(surface):
    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(surface, GRAY, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(surface, GRAY, (0, y), (WIDTH, y))


def draw_barricades(surface):
    for cell in barricades:
        rect = pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, BROWN, rect)


# --- NEW: Draw vents on the grid ---
def draw_vents(surface):
    for cell in vents:
        rect = pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(surface, VENT_COLOR, rect)
        pygame.draw.rect(surface, BLACK, rect, 2)


# --- NEW: Draw waypoints on the grid ---
def draw_waypoints(surface):
    for cell in waypoints:
        center = cell_center(cell)
        # Draw a small yellow circle (radius 5)
        pygame.draw.circle(surface, YELLOW, center, 5)


def draw_tetromino(tetromino, top_left, cell_size, surface):
    # Draw each cell of the tetromino relative to the given top_left position.
    for (dx, dy) in tetromino["cells"]:
        rect = pygame.Rect(top_left[0] + dx * cell_size,
                           top_left[1] + dy * cell_size,
                           cell_size, cell_size)
        pygame.draw.rect(surface, tetromino["color"], rect)
        pygame.draw.rect(surface, BLACK, rect, 2)


# --- Define on-screen button rectangles for tetromino selection ---
checkmark_rect = pygame.Rect(WIDTH // 4 - 40, HEIGHT - 100, 80, 50)
x_button_rect = pygame.Rect(3 * WIDTH // 4 - 40, HEIGHT - 100, 80, 50)

# --------- Main Game Loop -----------
running = True
while running:
    dt = clock.tick(60) / 1000.0  # seconds elapsed since last frame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # === Mode-dependent event handling ===
        if game_mode == "main":
            # --- Main Game Events ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    # Mark the target cell (blue) under the mouse cursor.
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    target_cell = (col, row)
                elif event.key == pygame.K_m:
                    # Enter tetromino selection mode instead of marking a target.
                    game_mode = "tetromino_select"
                elif event.key == pygame.K_n:
                    if current_patrol_path:
                        # When finalizing a manually‐created patrol, fill in intermediate cells
                        # so the path moves only horizontally and vertically.
                        fixed_path = []
                        fixed_path.append(current_patrol_path[0])
                        for cell in current_patrol_path[1:]:
                            last = fixed_path[-1]
                            dx = cell[0] - last[0]
                            dy = cell[1] - last[1]
                            if abs(dx) + abs(dy) > 1:
                                # Fill in horizontal moves then vertical moves.
                                step_x = 1 if dx > 0 else -1 if dx < 0 else 0
                                cur = last
                                while cur[0] != cell[0]:
                                    cur = (cur[0] + step_x, cur[1])
                                    fixed_path.append(cur)
                                step_y = 1 if dy > 0 else -1 if dy < 0 else 0
                                while cur[1] != cell[1]:
                                    cur = (cur[0], cur[1] + step_y)
                                    fixed_path.append(cur)
                            else:
                                fixed_path.append(cell)
                        patrols.append(Patrol(fixed_path))
                        current_patrol_path = []
                elif event.key == pygame.K_b:
                    # Place a barricade at the cell under the mouse.
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    cell = (col, row)
                    if cell not in barricades:
                        barricades.add(cell)
                elif event.key == pygame.K_v:
                    # --- NEW: Add a vent at the mouse cursor ---
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    cell = (col, row)
                    if cell not in vents:
                        vents.add(cell)
                elif event.key == pygame.K_w:
                    # --- NEW: Place a waypoint at the cell under the mouse ---
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    cell = (col, row)
                    if cell not in waypoints:
                        waypoints.append(cell)
                elif event.key == pygame.K_RETURN:
                    # --- NEW: Pressing Enter starts periodic enemy spawns from vents ---
                    spawn_from_vents = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = event.pos
                    col = mouse_x // CELL_SIZE
                    row = mouse_y // CELL_SIZE
                    cell = (col, row)
                    in_patrol_path = False
                    # (If a patrol is clicked, reverse its direction.)
                    for patrol in patrols:
                        if math.hypot(mouse_x - patrol.pos[0], mouse_y - patrol.pos[1]) < PATROL_RADIUS * 1.5:
                            patrol.direction *= -1
                            patrol.index -= patrol.direction
                            patrol.progress = 1 - patrol.progress
                            in_patrol_path = True
                    if not in_patrol_path:
                        if current_patrol_path:
                            last = current_patrol_path[-1]
                            dx = cell[0] - last[0]
                            dy = cell[1] - last[1]
                            if abs(dx) + abs(dy) > 1:
                                # Automatically fill in the intermediate cells so the path moves
                                # only horizontally and vertically.
                                step_x = 1 if dx > 0 else -1 if dx < 0 else 0
                                cur = last
                                while cur[0] != cell[0]:
                                    cur = (cur[0] + step_x, cur[1])
                                    current_patrol_path.append(cur)
                                step_y = 1 if dy > 0 else -1 if dy < 0 else 0
                                while cur[1] != cell[1]:
                                    cur = (cur[0], cur[1] + step_y)
                                    current_patrol_path.append(cur)
                            else:
                                current_patrol_path.append(cell)
                        else:
                            current_patrol_path.append(cell)

        elif game_mode == "tetromino_select":
            # --- Tetromino Selection Screen ---
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if checkmark_rect.collidepoint(mouse_x, mouse_y):
                    # Purchase the tetromino: move to placement mode.
                    purchased_tetromino = tetrominoes[current_tetromino_index]
                    game_mode = "tetromino_place"
                elif x_button_rect.collidepoint(mouse_x, mouse_y):
                    # Cycle to the next tetromino.
                    prev_tetromino_index = current_tetromino_index
                    while prev_tetromino_index == current_tetromino_index:
                        current_tetromino_index = random.randint(0, len(tetrominoes) - 1)
        elif game_mode == "tetromino_place":
            # --- Tetromino Placement Mode ---
            # Allow rotation via the R key.
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and purchased_tetromino is not None:
                    purchased_tetromino["cells"] = rotate_tetromino_cells(purchased_tetromino["cells"])
            # Place the tetromino with the mouse.
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                origin_col = mouse_x // CELL_SIZE
                origin_row = mouse_y // CELL_SIZE
                tetromino_cells = []
                valid = True
                for (dx, dy) in purchased_tetromino["cells"]:
                    cell = (origin_col + dx, origin_row + dy)
                    for barricade in barricades:
                        if cell == barricade:
                            valid = False
                            break
                    if not (0 <= cell[0] < GRID_COLS and 0 <= cell[1] < GRID_ROWS) or not valid:
                        valid = False
                        break
                    tetromino_cells.append(cell)
                if valid:
                    # Instead of directly using the tetromino cells (which might be in an order that makes diagonal moves),
                    # compute a proper patrol ordering that stays within the tetromino.
                    ordered_path = compute_patrol_path(tetromino_cells)
                    # --- NEW: Remove any existing patrol that overlaps with the new tetromino cells ---
                    new_cells_set = set(tetromino_cells)
                    patrols[:] = [p for p in patrols if set(p.path).isdisjoint(new_cells_set)]
                    patrols.append(Patrol(ordered_path))
                    purchased_tetromino = None
                    game_mode = "main"

    # --- Update Game Objects (in all modes) ---
    if spawn_from_vents and vents:
        vent_spawn_timer += dt
        if vent_spawn_timer >= vent_spawn_interval:
            for vent in vents:
                enemy = Enemy(vent)
                enemies.append(enemy)
            vent_spawn_timer = 0.0

    # Update patrols and enemies.
    for patrol in patrols:
        patrol.update(dt)
    for enemy in enemies:
        enemy.update(dt)

    # --- NEW: Check for collisions between patrols and enemies.
    # Only register a collision if the patrol is not already asleep.
    for patrol in patrols:
        if patrol.sleep_timer > 0:
            continue
        for enemy in enemies[:]:
            dx = patrol.pos[0] - enemy.pos[0]
            dy = patrol.pos[1] - enemy.pos[1]
            if math.hypot(dx, dy) < PATROL_RADIUS + ENEMY_RADIUS:
                patrol.sleep_timer = PATROL_SLEEP_TIME  # Patrol stops moving for 3 seconds.
                enemies.remove(enemy)
                break

    # Update spawning rate
    time_since_spawn_decreased += dt
    if time_since_spawn_decreased > 10:
        time_since_spawn_decreased = 0
        vent_spawn_interval *= 0.9

    # --- Drawing ---
    if game_mode in ("main", "tetromino_place"):
        # Draw the main game screen.
        screen.fill(WHITE)
        draw_grid(screen)
        draw_barricades(screen)
        draw_vents(screen)  # --- Draw vents on the grid
        draw_waypoints(screen)  # --- Draw waypoints on the grid
        if target_cell:
            target_rect = pygame.Rect(target_cell[0] * CELL_SIZE, target_cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, LIGHT_BLUE, target_rect)

        # Draw any manually-created (unfinalized) patrol path cells.
        for cell in current_patrol_path:
            rect = pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, LIGHT_GREEN, rect)
        if len(current_patrol_path) > 1:
            points = [cell_center(cell) for cell in current_patrol_path]
            pygame.draw.lines(screen, LIGHT_GREEN, False, points, 3)
        for patrol in patrols:
            patrol.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)
        # If in tetromino placement mode, show the purchased tetromino following the mouse,
        # snapped to the grid.
        if game_mode == "tetromino_place" and purchased_tetromino is not None:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            origin_col = mouse_x // CELL_SIZE
            origin_row = mouse_y // CELL_SIZE
            top_left = (origin_col * CELL_SIZE, origin_row * CELL_SIZE)
            draw_tetromino(purchased_tetromino, top_left, CELL_SIZE, screen)
    elif game_mode == "tetromino_select":
        # Draw the tetromino selection screen.
        screen.fill(WHITE)
        preview_cell_size = 50
        tetromino = tetrominoes[current_tetromino_index]
        xs = [cell[0] for cell in tetromino["cells"]]
        ys = [cell[1] for cell in tetromino["cells"]]
        width_cells = max(xs) - min(xs) + 1
        height_cells = max(ys) - min(ys) + 1
        preview_width = width_cells * preview_cell_size
        preview_height = height_cells * preview_cell_size
        preview_top_left = ((WIDTH - preview_width) // 2 - min(xs) * preview_cell_size,
                            (HEIGHT - preview_height) // 2 - min(ys) * preview_cell_size)
        draw_tetromino(tetromino, preview_top_left, preview_cell_size, screen)
        pygame.draw.rect(screen, GREEN, checkmark_rect)
        check_text = font.render("OK", True, BLACK)
        text_rect = check_text.get_rect(center=checkmark_rect.center)
        screen.blit(check_text, text_rect)
        pygame.draw.rect(screen, RED, x_button_rect)
        x_text = font.render("X", True, BLACK)
        text_rect = x_text.get_rect(center=x_button_rect.center)
        screen.blit(x_text, text_rect)

    pygame.display.flip()

pygame.quit()
sys.exit()
