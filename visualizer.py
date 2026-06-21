import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class HeatVisualizer:
    def __init__(self, grid_size, initial_temp, boundary_temp):
        self.grid_size = grid_size
        self.initial_temp = initial_temp
        self.boundary_temp = boundary_temp
        self.fig, self.ax = plt.subplots(figsize=(8, 7))
        self.im = None
        self.cbar = None
        self.title = None
        self._init_plot()

    def _init_plot(self):
        empty_grid = np.zeros((self.grid_size, self.grid_size))
        self.im = self.ax.imshow(
            empty_grid,
            cmap='inferno',
            vmin=self.boundary_temp,
            vmax=self.initial_temp,
            origin='lower',
            extent=[0, self.grid_size, 0, self.grid_size]
        )
        self.cbar = self.fig.colorbar(self.im, ax=self.ax, label='Temperature (°C)')
        self.title = self.ax.set_title('2D Heat Conduction - Step 0')
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')

    def update(self, grid, step, elapsed_time):
        self.im.set_data(grid)
        self.title.set_text(
            f'2D Heat Conduction - Step {step} | Time: {elapsed_time:.2f}s'
        )
        self.fig.canvas.draw_idle()
        plt.pause(0.001)

    def show(self):
        plt.tight_layout()
        plt.show(block=False)

    def close(self):
        plt.close(self.fig)
