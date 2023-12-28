#!/bin/python3
# _*_ coding:utf-8 _*_
#
# threads.py
# 多进程写法优化，单任务执行时间越长，多线程越有优势

import concurrent.futures
import os
import random
import time
from typing import List, Generator, Any


class ProcessPoolHelper(concurrent.futures.ProcessPoolExecutor):
    def __init__(self, max_workers=None, mp_context=None, initializer=None, initargs=()):
        super().__init__(max_workers, mp_context, initializer, initargs)
        self.__job_list: List[concurrent.futures.Future] = []

    def submit_super(self, fn, /, *args, **kwargs) -> concurrent.futures.Future:
        job = self.submit(fn, *args, **kwargs)
        self.__job_list.append(job)
        return job

    def result_yield(self) -> Generator[Any, None, None]:
        self.__job_list.reverse()
        while self.__job_list:
            yield self.__job_list.pop().result()

        self.__job_list = []


def __test_performance_func(min: int = 500, max: int = 600):
    # print(os.getpid(), 'test_normal_func running...')
    result = 0
    for i in range(random.randint(min, max)):
        for j in range(random.randint(min, max)):
            for k in range(random.randint(min, max)):
                result += i * j * k
    print(os.getpid(), 'test_normal_func result:', str(result))
    # print(os.getpid(), 'test_normal_func ending...')


def __test_return_func(min: int = 500, max: int = 600):
    result = 0
    for i in range(random.randint(min, max)):
        for j in range(random.randint(min, max)):
            for k in range(random.randint(min, max)):
                result += i * j * k
    print(os.getpid(), 'test_return_func result:', str(result))
    # 返回数据
    return result


if __name__ == '__main__':
    start_time = time.time()
    print('return:', __test_return_func(500, 550))
    print('run one times, total time(s):', time.time() - start_time)

    thr = ProcessPoolHelper(3)

    start_time = time.time()
    [thr.submit_super(__test_return_func, 500, 550) for i in range(10)]
    print('return:', [i for i in thr.result_yield()])
    print('total time(s):', time.time() - start_time)

    start_time = time.time()
    [thr.submit_super(__test_performance_func, 500, 550) for i in range(10)]
    print('return:', [i for i in thr.result_yield()])
    print('total time(s):', time.time() - start_time)
