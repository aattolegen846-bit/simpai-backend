from concurrent.futures import ThreadPoolExecutor


_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="simpai-bg")


def dispatch_background_task(fn, *args, **kwargs) -> None:
    _executor.submit(fn, *args, **kwargs)
