import threading
import time
import numpy as np
import yaml
from solver import (
    initialize_grid, apply_boundary_conditions,
    compute_adaptive_dt, step_explicit,
    HeatSource, TemperatureProbe, apply_heat_sources
)
from parallel import parallel_step


class HeatSimulator:
    def __init__(self, config_path='config.yaml'):
        self._lock = threading.Lock()
        self._thread = None
        self._running = False
        self._paused = False
        self._stop_requested = False

        self._load_config(config_path)
        self._reset_state()

    def _load_config(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.alpha = config['alpha']
        self.grid_size = config['grid_size']
        self.dx = config['dx']
        self.dy = config['dy']
        self.dt = config['dt']
        self.dt_min = config.get('dt_min', 0.001)
        self.dt_max = config.get('dt_max', 0.5)
        self.total_time = config['total_time']
        self.visualize_interval = config.get('visualize_interval', 10)
        self.initial_radius = config['initial_radius']
        self.initial_temp = config['initial_temp']
        self.boundary_temp = config['boundary_temp']
        self.num_processes = config['num_processes']
        self.adaptive_dt = config.get('adaptive_dt', True)
        self.safety_factor = config.get('stability_safety_factor', 0.9)

    def _reset_state(self):
        self.grid = initialize_grid(
            self.grid_size, self.initial_radius,
            self.initial_temp, self.boundary_temp
        )
        self.sources = []
        self.probes = {}
        self.probe_counter = 0
        self.step_count = 0
        self.elapsed_sim_time = 0.0
        self.start_wall_time = None
        self.elapsed_wall_time = 0.0
        self.status = 'idle'
        self.error = None

    def reset(self):
        with self._lock:
            self._stop_requested = True
            self._paused = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        with self._lock:
            self._reset_state()
            return self.get_state()

    def set_sources(self, sources_list):
        with self._lock:
            self.sources = [HeatSource.from_dict(s) for s in sources_list]
            self._apply_sources_to_grid()
            return [s.to_dict() for s in self.sources]

    def add_source(self, x, y, temperature, radius=3):
        with self._lock:
            src = HeatSource(x, y, temperature, radius)
            self.sources.append(src)
            self._apply_sources_to_grid()
            return src.to_dict()

    def clear_sources(self):
        with self._lock:
            self.sources.clear()
            return []

    def _apply_sources_to_grid(self):
        if self.sources:
            apply_heat_sources(self.grid, self.sources)

    def add_probe(self, x, y):
        with self._lock:
            self.probe_counter += 1
            probe_id = f'probe_{self.probe_counter}'
            probe = TemperatureProbe(probe_id, x, y)
            if self.elapsed_sim_time == 0:
                probe.record(0.0, self.grid)
            self.probes[probe_id] = probe
            return probe.to_dict()

    def remove_probe(self, probe_id):
        with self._lock:
            if probe_id in self.probes:
                del self.probes[probe_id]
                return True
            return False

    def clear_probes(self):
        with self._lock:
            self.probes.clear()
            self.probe_counter = 0
            return []

    def get_probes(self):
        with self._lock:
            return {pid: p.to_dict() for pid, p in self.probes.items()}

    def _record_probes(self):
        for probe in self.probes.values():
            probe.record(self.elapsed_sim_time, self.grid)

    def start(self):
        with self._lock:
            if self._running and not self._paused:
                return self.get_state()
            if self._paused:
                self._paused = False
                return self.get_state()

            self._stop_requested = False
            self._running = True
            self._paused = False
            self.status = 'running'
            self.start_wall_time = time.time() - self.elapsed_wall_time

        self._thread = threading.Thread(target=self._run_simulation, daemon=True)
        self._thread.start()
        return self.get_state()

    def pause(self):
        with self._lock:
            if not self._running:
                return self.get_state()
            self._paused = True
            self.status = 'paused'
            self.elapsed_wall_time = time.time() - self.start_wall_time
            return self.get_state()

    def resume(self):
        with self._lock:
            if not self._running or not self._paused:
                return self.get_state()
            self._paused = False
            self.status = 'running'
            self.start_wall_time = time.time() - self.elapsed_wall_time
            return self.get_state()

    def stop(self):
        with self._lock:
            self._stop_requested = True
            self._paused = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        with self._lock:
            if self.status == 'running':
                self.status = 'stopped'
            return self.get_state()

    def _run_simulation(self):
        try:
            while True:
                with self._lock:
                    if self._stop_requested:
                        self._running = False
                        self.status = 'stopped'
                        break
                    if self._paused:
                        time.sleep(0.05)
                        continue
                    if self.elapsed_sim_time >= self.total_time:
                        self._running = False
                        self.status = 'completed'
                        break

                with self._lock:
                    if self.adaptive_dt:
                        dt = compute_adaptive_dt(
                            self.grid, self.alpha, self.dx, self.dy,
                            self.dt, self.dt_min, self.dt_max, self.safety_factor
                        )
                    else:
                        dt = self.dt

                    if self.elapsed_sim_time + dt > self.total_time:
                        dt = self.total_time - self.elapsed_sim_time

                    grid_copy = self.grid.copy()

                if self.num_processes > 1:
                    new_grid = parallel_step(
                        grid_copy, self.alpha, self.dx, self.dy, dt,
                        self.num_processes, self.boundary_temp
                    )
                else:
                    new_grid = step_explicit(
                        grid_copy, self.alpha, self.dx, self.dy, dt,
                        self.boundary_temp
                    )

                with self._lock:
                    self.grid = new_grid
                    self.elapsed_sim_time += dt
                    self.step_count += 1

                    self._apply_sources_to_grid()

                    if self.probes and self.step_count % self.visualize_interval == 0:
                        self._record_probes()

                    max_temp = self.grid.max()
                    min_temp = self.grid.min()
                    if max_temp > self.initial_temp * 2 or min_temp < self.boundary_temp - 50:
                        self.grid = np.clip(self.grid, self.boundary_temp - 10, self.initial_temp * 2)

                    self.elapsed_wall_time = time.time() - self.start_wall_time

                time.sleep(0.001)

        except Exception as e:
            with self._lock:
                self._running = False
                self.status = 'error'
                self.error = str(e)

    def get_state(self):
        with self._lock:
            progress = (self.elapsed_sim_time / self.total_time * 100) if self.total_time > 0 else 0
            eta = 0.0
            if progress > 0 and self.status == 'running':
                eta = (self.elapsed_wall_time / progress) * (100 - progress)

            grid_list = self.grid.tolist()

            return {
                'status': self.status,
                'step': self.step_count,
                'sim_time': self.elapsed_sim_time,
                'total_time': self.total_time,
                'progress': min(progress, 100.0),
                'eta': eta,
                'wall_time': self.elapsed_wall_time,
                'max_temp': float(self.grid.max()),
                'min_temp': float(self.grid.min()),
                'dt': self.dt if not self.adaptive_dt else compute_adaptive_dt(
                    self.grid, self.alpha, self.dx, self.dy,
                    self.dt, self.dt_min, self.dt_max, self.safety_factor
                ),
                'grid_size': self.grid_size,
                'grid': grid_list,
                'sources': [s.to_dict() for s in self.sources],
                'probes': {pid: p.to_dict() for pid, p in self.probes.items()},
                'error': self.error
            }

    def get_grid_data(self):
        with self._lock:
            return self.grid.copy()
