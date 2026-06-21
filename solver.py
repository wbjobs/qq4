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


def compute_max_gradient(grid, dx, dy):
    grad_x = np.zeros_like(grid)
    grad_y = np.zeros_like(grid)
    grad_x[1:-1, 1:-1] = np.abs(grid[1:-1, 2:] - grid[1:-1, :-2]) / (2 * dx)
    grad_y[1:-1, 1:-1] = np.abs(grid[2:, 1:-1] - grid[:-2, 1:-1]) / (2 * dy)
    return max(grad_x.max(), grad_y.max())


def compute_adaptive_dt(grid, alpha, dx, dy, dt_current, dt_min, dt_max, safety_factor=0.9):
    max_grad = compute_max_gradient(grid, dx, dy)
    r_stable = 0.25
    dt_stable = r_stable * min(dx ** 2, dy ** 2) / alpha
    if max_grad > 1e-10:
        dt_gradient = safety_factor * 0.1 / (alpha * max_grad * (1 / dx ** 2 + 1 / dy ** 2))
        dt_new = min(dt_stable, dt_gradient)
    else:
        dt_new = dt_stable
    dt_new = max(dt_min, min(dt_max, dt_new * safety_factor))
    return dt_new


def step_explicit(grid, alpha, dx, dy, dt, boundary_temp):
    laplacian = compute_laplacian(grid, dx, dy)
    new_grid = grid + alpha * dt * laplacian
    new_grid = apply_boundary_conditions(new_grid, boundary_temp)
    return new_grid


def step_explicit_chunk(grid_chunk, alpha, dx, dy, dt,
                        top_row=None, bottom_row=None,
                        is_top_boundary=False, is_bottom_boundary=False,
                        boundary_temp=0.0):
    rows, cols = grid_chunk.shape
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

    if is_top_boundary:
        new_chunk[0, :] = boundary_temp
    if is_bottom_boundary:
        new_chunk[-1, :] = boundary_temp
    new_chunk[:, 0] = boundary_temp
    new_chunk[:, -1] = boundary_temp

    return new_chunk


def check_stability(alpha, dx, dy, dt):
    r_x = alpha * dt / dx ** 2
    r_y = alpha * dt / dy ** 2
    return (r_x + r_y) <= 0.5, r_x, r_y
