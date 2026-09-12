def bar(a, b=None):
    return f"bar called with a={a}, b={b}"


def process_items(items, count):
    print(f"process_items called with {len(items)} items and count={count}")
    return True
