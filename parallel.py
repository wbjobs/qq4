import numpy as np
import multiprocessing as mp
from solver import step_explicit_chunk, apply_boundary_conditions


def split_grid(grid, num_chunks):
    grid_size = grid.shape[0]
    chunk_size = grid_size // num_chunks
    remainder = grid_size % num_chunks
    chunks = []
    row_indices = []
    start = 0
    for i in range(num_chunks):
        size = chunk_size + (1 if i < remainder else 0)
        end = start + size
        chunks.append(grid[start:end, :].copy())
        row_indices.append((start, end))
        start = end
    return chunks, row_indices


def worker(args):
    chunk, alpha, dx, dy, dt, top_row, bottom_row, is_top, is_bottom, boundary_temp = args
    return step_explicit_chunk(
        chunk, alpha, dx, dy, dt, top_row, bottom_row, is_top, is_bottom, boundary_temp
    )


def parallel_step(grid, alpha, dx, dy, dt, num_processes, boundary_temp):
    grid_size = grid.shape[0]
    if num_processes <= 1 or grid_size < 10:
        from solver import step_explicit
        return step_explicit(grid, alpha, dx, dy, dt, boundary_temp)

    num_chunks = min(num_processes, grid_size // 4)
    chunks, row_indices = split_grid(grid, num_chunks)

    args_list = []
    for i in range(num_chunks):
        chunk = chunks[i]
        top_row = None if i == 0 else grid[row_indices[i - 1][1] - 1, :].copy()
        bottom_row = None if i == num_chunks - 1 else grid[row_indices[i + 1][0], :].copy()
        is_top_boundary = (i == 0)
        is_bottom_boundary = (i == num_chunks - 1)
        args_list.append((
            chunk, alpha, dx, dy, dt,
            top_row, bottom_row,
            is_top_boundary, is_bottom_boundary,
            boundary_temp
        ))

    with mp.Pool(processes=num_processes) as pool:
        new_chunks = pool.map(worker, args_list)

    new_grid = np.empty_like(grid)
    for i in range(num_chunks):
        start, end = row_indices[i]
        new_grid[start:end, :] = new_chunks[i]

    new_grid = apply_boundary_conditions(new_grid, boundary_temp)
    return new_grid
