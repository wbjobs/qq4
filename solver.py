import numpy as np


def initialize_grid(grid_size, initial_radius, initial_temp, boundary_temp):
    grid = np.full((grid_size, grid_size), boundary_temp, dtype=np.float64)
    center = grid_size // 2
    y, x = np.ogrid[:grid_size, :grid_size]
    dist_from_center = np.sqrt((x - center) ** 2 + (y - center) ** 2)
    mask = dist_from_center <= initial_radius
    grid[mask] = initial_temp
    return grid


def apply_boundary_conditions(grid, boundary_temp):
    grid[0, :] = boundary_temp
    grid[-1, :] = boundary_temp
    grid[:, 0] = boundary_temp
    grid[:, -1] = boundary_temp
    return grid


def compute_laplacian(grid, dx, dy):
    laplacian = np.zeros_like(grid)
    laplacian[1:-1, 1:-1] = (
        (grid[2:, 1:-1] - 2 * grid[1:-1, 1:-1] + grid[:-2, 1:-1]) / dx ** 2
        + (grid[1:-1, 2:] - 2 * grid[1:-1, 1:-1] + grid[1:-1, :-2]) / dy ** 2
    )
    return laplacian


def step_explicit(grid, alpha, dx, dy, dt, boundary_temp):
    laplacian = compute_laplacian(grid, dx, dy)
    new_grid = grid + alpha * dt * laplacian
    new_grid = apply_boundary_conditions(new_grid, boundary_temp)
    return new_grid


def step_explicit_chunk(grid_chunk, alpha, dx, dy, dt, top_row=None, bottom_row=None):
    rows, cols = grid_chunk.shape
    new_chunk = np.copy(grid_chunk)
    if top_row is not None:
        if bottom_row is not None:
            extended = np.empty((rows + 2, cols), dtype=np.float64)
            extended[0, :] = top_row
            extended[1:-1, :] = grid_chunk
            extended[-1, :] = bottom_row
        else:
            extended = np.empty((rows + 1, cols), dtype=np.float64)
            extended[0, :] = top_row
            extended[1:, :] = grid_chunk
    else:
        if bottom_row is not None:
            extended = np.empty((rows + 1, cols), dtype=np.float64)
            extended[:-1, :] = grid_chunk
            extended[-1, :] = bottom_row
        else:
            extended = grid_chunk
    lap = np.zeros_like(extended)
    lap[1:-1, 1:-1] = (
        (extended[2:, 1:-1] - 2 * extended[1:-1, 1:-1] + extended[:-2, 1:-1]) / dx ** 2
        + (extended[1:-1, 2:] - 2 * extended[1:-1, 1:-1] + extended[1:-1, :-2]) / dy ** 2
    )
    if top_row is not None:
        if bottom_row is not None:
            new_chunk = grid_chunk + alpha * dt * lap[1:-1, :]
        else:
            new_chunk = grid_chunk + alpha * dt * lap[1:, :]
    else:
        if bottom_row is not None:
            new_chunk = grid_chunk + alpha * dt * lap[:-1, :]
        else:
            new_chunk = grid_chunk + alpha * dt * lap
    new_chunk = apply_boundary_conditions(new_chunk, 0.0)
    return new_chunk


def check_stability(alpha, dx, dy, dt):
    r_x = alpha * dt / dx ** 2
    r_y = alpha * dt / dy ** 2
    return (r_x + r_y) <= 0.5, r_x, r_y
