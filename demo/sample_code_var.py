import mylib


def compute():
    items = [1,2,3]
    x = 5
    # variable passed instead of literal
    mylib.process_items(items, x)
    # still uses removed function
    result = mylib.foo(1, 2)
    print(result)

if __name__ == "__main__":
    compute()
