#!/usr/bin/env python

import yaml

with open("inputs.4e.yaml", 'r') as stream:
    print(yaml.load(stream))
