import threading
import requests

from decorators import measure_time

def fetch(url):
    requests.get(url)


@measure_time
def run_threads(url, times):
    threads = []
    for i in range(times):
        t = threading.Thread(target=fetch, args=(url,))
        threads.append(t)
        t.start()

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    URL = "https://en.wikipedia.org/wiki/Fibonacci_sequence"
    TIMES = 10
    run_threads(URL, TIMES)