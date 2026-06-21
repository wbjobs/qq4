import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from simulator import HeatSimulator

app = Flask(__name__, static_folder='static', template_folder='templates')

simulator = HeatSimulator()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/state', methods=['GET'])
def get_state():
    state = simulator.get_state()
    include_grid = request.args.get('grid', 'true').lower() == 'true'
    if not include_grid:
        state.pop('grid', None)
    return jsonify(state)


@app.route('/api/grid', methods=['GET'])
def get_grid():
    grid = simulator.get_grid_data()
    return jsonify({
        'grid': grid.tolist(),
        'grid_size': grid.shape[0]
    })


@app.route('/api/start', methods=['POST'])
def start_sim():
    state = simulator.start()
    return jsonify(state)


@app.route('/api/pause', methods=['POST'])
def pause_sim():
    state = simulator.pause()
    return jsonify(state)


@app.route('/api/resume', methods=['POST'])
def resume_sim():
    state = simulator.resume()
    return jsonify(state)


@app.route('/api/reset', methods=['POST'])
def reset_sim():
    state = simulator.reset()
    return jsonify(state)


@app.route('/api/source', methods=['POST'])
def add_source():
    data = request.get_json()
    x = data.get('x', 50)
    y = data.get('y', 50)
    temperature = data.get('temperature', 100.0)
    radius = data.get('radius', 3)
    result = simulator.add_source(x, y, temperature, radius)
    return jsonify({'source': result, 'state': simulator.get_state()})


@app.route('/api/sources', methods=['PUT'])
def set_sources():
    data = request.get_json()
    sources = data.get('sources', [])
    result = simulator.set_sources(sources)
    return jsonify({'sources': result, 'state': simulator.get_state()})


@app.route('/api/sources', methods=['DELETE'])
def clear_sources():
    result = simulator.clear_sources()
    return jsonify({'sources': result, 'state': simulator.get_state()})


@app.route('/api/probe', methods=['POST'])
def add_probe():
    data = request.get_json()
    x = data.get('x', 50)
    y = data.get('y', 50)
    result = simulator.add_probe(x, y)
    return jsonify({'probe': result})


@app.route('/api/probe/<probe_id>', methods=['DELETE'])
def remove_probe(probe_id):
    success = simulator.remove_probe(probe_id)
    return jsonify({'success': success})


@app.route('/api/probes', methods=['GET'])
def get_probes():
    probes = simulator.get_probes()
    return jsonify({'probes': probes})


@app.route('/api/probes', methods=['DELETE'])
def clear_probes():
    result = simulator.clear_probes()
    return jsonify({'probes': result})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
