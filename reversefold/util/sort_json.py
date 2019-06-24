#!/usr/bin/env python
import collections
import json
import sys


def recursive_sorted(data):
    if isinstance(data, dict):
        return collections.OrderedDict(
            sorted(
                (k, recursive_sorted(v))
                for k, v in data.iteritems()
            )
        )
    elif isinstance(data, (list, tuple)):
        return sorted(recursive_sorted(v) for v in data)
    else:
        return data


def main():
    data = json.load(sys.stdin)
    print(json.dumps(recursive_sorted(data), indent=4))


if __name__ == '__main__':
    main()
