import mylib as ml


def compute():
    items = [1,2,3]
    # aliased import usage
    result = ml.foo(1, 2)
    ml.process_items(items, 5)
    print(result)

if __name__ == "__main__":
    compute()
