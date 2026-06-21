import yaml
import numpy as np
import time
import matplotlib.pyplot as plt
from solver import initialize_grid, check_stability
from parallel import parallel_step
from visualizer import HeatVisualizer


def load_config(config_path='config.yaml'):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    config = load_config()

    alpha = config['alpha']
    grid_size = config['grid_size']
    dx = config['dx']
    dy = config['dy']
    dt = config['dt']
    total_time = config['total_time']
    visualize_interval = config['visualize_interval']
    initial_radius = config['initial_radius']
    initial_temp = config['initial_temp']
    boundary_temp = config['boundary_temp']
    num_processes = config['num_processes']

    stable, r_x, r_y = check_stability(alpha, dx, dy, dt)
    print(f'稳定性检查: r_x={r_x:.6f}, r_y={r_y:.6f}, r_x+r_y={r_x+r_y:.6f}')
    if not stable:
        print('警告: 显式格式不满足稳定条件 (r_x + r_y <= 0.5)!')
        print('建议减小 dt 或增大 dx/dy。')
    else:
        print('显式格式满足稳定条件。')

    grid = initialize_grid(grid_size, initial_radius, initial_temp, boundary_temp)
    num_steps = int(total_time / dt)
    print(f'网格大小: {grid_size}x{grid_size}')
    print(f'总时间步数: {num_steps}')
    print(f'并行进程数: {num_processes}')

    viz = HeatVisualizer(grid_size, initial_temp, boundary_temp)
    viz.show()
    viz.update(grid, 0, 0.0)

    start_time = time.time()
    elapsed_sim_time = 0.0

    for step in range(1, num_steps + 1):
        grid = parallel_step(grid, alpha, dx, dy, dt, num_processes, boundary_temp)
        elapsed_sim_time += dt

        if step % visualize_interval == 0:
            viz.update(grid, step, elapsed_sim_time)
            real_elapsed = time.time() - start_time
            avg_time_per_step = real_elapsed / step
            remaining_steps = num_steps - step
            eta = remaining_steps * avg_time_per_step
            print(
                f'Step {step}/{num_steps} | '
                f'SimTime: {elapsed_sim_time:.2f}s | '
                f'RealTime: {real_elapsed:.2f}s | '
                f'ETA: {eta:.1f}s | '
                f'MaxTemp: {grid.max():.2f}°C'
            )

    total_real_time = time.time() - start_time
    print(f'\n模拟完成!')
    print(f'总仿真时间: {elapsed_sim_time:.2f}s')
    print(f'总计算时间: {total_real_time:.2f}s')
    print(f'平均每步耗时: {total_real_time/num_steps:.4f}s')

    print('\n按任意键关闭窗口...')
    plt.show()
    viz.close()


if __name__ == '__main__':
    main()
