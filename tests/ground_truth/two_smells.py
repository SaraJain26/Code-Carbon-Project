def process(items):
    output = []
    for item in items:
        output.append(list(items))
        print(open(item).read())
    return output
