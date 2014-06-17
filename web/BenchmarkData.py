import re
class BenchmarkData:
    def __init__(self, bench_id, redis_handler):
        if bench_id == 'latest':
          bench_id = redis_handler.get('latest_benchmark')
        self.bench_id = bench_id
        self.redis_handler = redis_handler

    def get_data(self):
        get_iter = re.compile('.*:(.+)$')
        iter1_target_ids = self.redis_handler.keys(self.bench_id + '_*:1')
        target_ids = [t.replace(self.bench_id+'_','').replace(':1','') for t in iter1_target_ids]
    
        target_data = { }
        for target in target_ids:
            last_iter = 0
            for target_iter in  self.redis_handler.keys(self.bench_id + '_' + target + ':*'):
                it = int(get_iter.split(target_iter)[1])
                if it > last_iter:
                    last_iter = it
            last_data = self.redis_handler.hgetall(self.bench_id + '_' + target + ':' + str(last_iter))
            target_data[target] = {
                    'last_iter' : last_iter,
                    'progress'  : last_data['completition']
                    
                }
        
        return {
        	'id'	:	self.bench_id,
        	'ntargets' : len(target_ids),
            'target_data'  : target_data

        }
