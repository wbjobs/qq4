import yaml
import numpy as np
import time
import matplotlib.pyplot as plt
from solver import initialize_grid, check_stability, compute_adaptive_dt
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
    dt_min = config.get('dt_min', 0.001)
    dt_max = config.get('dt_max', 0.5)
    total_time = config['total_time']
    visualize_interval = config['visualize_interval']
    initial_radius = config['initial_radius']
    initial_temp = config['initial_temp']
    boundary_temp = config['boundary_temp']
    num_processes = config['num_processes']
    adaptive_dt = config.get('adaptive_dt', True)
    safety_factor = config.get('stability_safety_factor', 0.9)

    stable, r_x, r_y = check_stability(alpha, dx, dy, dt)
    print(f'初始稳定性检查: r_x={r_x:.6f}, r_y={r_y:.6f}, r_x+r_y={r_x+r_y:.6f}')
    if not stable:
        print('警告: 初始dt不满足稳定条件 (r_x + r_y <= 0.5)!')
    print(f'自适应时间步长: {"启用" if adaptive_dt else "禁用"}')
    if adaptive_dt:
        print(f'dt范围: [{dt_min}, {dt_max}], 安全系数: {safety_factor}')

    grid = initialize_grid(grid_size, initial_radius, initial_temp, boundary_temp)
    print(f'网格大小: {grid_size}x{grid_size}')
    print(f'总仿真时间: {total_time}s')
    print(f'并行进程数: {num_processes}')

    viz = HeatVisualizer(grid_size, initial_temp, boundary_temp)
    viz.show()
    viz.update(grid, 0, 0.0)

    start_time = time.time()
    elapsed_sim_time = 0.0
    step = 0

    while elapsed_sim_time < total_time:
        step += 1

        if adaptive_dt:
            dt = compute_adaptive_dt(
                grid, alpha, dx, dy, dt, dt_min, dt_max, safety_factor
            )

        if elapsed_sim_time + dt > total_time:
            dt = total_time - elapsed_sim_time

        grid = parallel_step(grid, alpha, dx, dy, dt, num_processes, boundary_temp)
        elapsed_sim_time += dt

        if grid.max() > initial_temp + 1e-6 or grid.min() < boundary_temp - 1e-6:
            print(f'  ⚠ 数值异常: max={grid.max():.4f}, min={grid.min():.4f}')
            grid = np.clip(grid, boundary_temp, initial_temp)

        if step % visualize_interval == 0:
            viz.update(grid, step, elapsed_sim_time)
            real_elapsed = time.time() - start_time
            avg_time_per_step = real_elapsed / step
            remaining_time = total_time - elapsed_sim_time
            eta = remaining_time / (elapsed_sim_time / real_elapsed) if real_elapsed > 0 else 0
            print(
                f'Step {step:5d} | '
                f'SimTime: {elapsed_sim_time:6.2f}/{total_time:.1f}s | '
                f'dt: {dt:.4f}s | '
                f'RealTime: {real_elapsed:.2f}s | '
                f'ETA: {eta:.1f}s | '
                f'MaxTemp: {grid.max():.2f}°C'
            )

    total_real_time = time.time() - start_time
    print(f'\n模拟完成!')
    print(f'总仿真时间: {elapsed_sim_time:.2f}s')
    print(f'总计算时间: {total_real_time:.2f}s')
    print(f'总步数: {step}')
    print(f'平均每步耗时: {total_real_time/step:.4f}s')
    print(f'最终最大温度: {grid.max():.4f}°C')

    print('\n关闭窗口退出...')
    plt.show()
    viz.close()


if __name__ == '__main__':
    main()
