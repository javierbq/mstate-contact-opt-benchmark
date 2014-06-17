from flask import Flask
from flask import render_template
from flask_bootstrap import Bootstrap

app = Flask(__name__,template_folder='templates')
Bootstrap(app)

from settings import DEFAULT_REDIS_HOST_PORT
from web.BenchmarkData import BenchmarkData

from redis import Redis

redis_handler = Redis(*DEFAULT_REDIS_HOST_PORT)

@app.route('/benchmark')
@app.route('/benchmark/<string:bench_id>')
def show_benchmark(bench_id='latest'):
  benchmark  = BenchmarkData(bench_id, redis_handler)
  return render_template('benchmark.html', bench_data=benchmark.get_data())


@app.route('/')
def main():
    latest_benchmark = redis_handler.get('latest_benchmark')
    old_benchmarks = redis_handler.lrange('old_benchmarks',0,-1)

    return render_template('main.html',latest_bench=latest_benchmark,old_benchs=old_benchmarks)

def main():
    app.debug = True
    app.run(host='0.0.0.0')
