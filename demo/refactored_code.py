import mylib


def compute():
    items = [1,2,3]
    # updated to use mylib.bar and keyword arg for b
    result = mylib.bar(1, b=2)
    # convert count to string per new API
    mylib.process_items(items, "5")
    print(result)

if __name__ == "__main__":
    compute()
