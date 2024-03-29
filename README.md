# json-parser

A hilarious foray into the world of streaming parsers. I laughed, I cried, it took a day.

## Purpose

I wrote this so that I could parse chunky API responses on a memory-constrained ESP32 running Micropython.
I probably could've used one of the dozens of existing such libraries but that's not fun for me.
I recently [made my own AAA battery holder](https://photos.google.com/share/AF1QipPe44ojFa2bh5PcLL6LHTBP4V0Hmqc8Uv1vhxuDJGkwDnw3l-dGW8qsa5TYxH21OA/photo/AF1QipPfLvxKoX4zsl0mPSUMkvUw3w62IRvFTAYPhoad?key=VFY0OE95SjBJRjdBRUxrTFlmWmtvVGp4bHNtb0hR) out of laser-cut wood and bolts - I'm not about to start using "libraries" in my personal projects.

## Usage

1. Instantiate the `Parser` with a binary stream

```
from __init__ import Parser

fh = open('test_data/api_weather_gov_points.json', 'rb')
parser = Parser(fh)
```

2. Parse it

    #### The bad way

    Parse it all at once using `Parser.load()`:
    ```
    ...

    data = parser.load()
    ```

    #### The **GOOD** way

    Parse only the paths you want using `Parser.yield_paths()`:

    ```
    ...
    gen = parser.yield_paths((
        [ '@context', 0 ],
        [ '@context', 1, '@version' ]
    ))

    next(gen)
    # (['@context', 0], 'https://geojson.org/geojson-ld/geojson-context.jsonld')

    next(gen)
    # (['@context', 1, '@version'], '1.1')
    ```

## CLI

```
$ python3 __init__.py --help
usage: __init__.py [-h] [--file FILE | --string STRING] [--action {load,parse}]
                  [--path PATH]

optional arguments:
  -h, --help            show this help message and exit
  --file FILE
  --string STRING
  --action {load,parse}
  --path PATH           Dot-delimited path specifier with dots in keys escaped
                        as a double-dot
```

You must specify either `--file=<file-path>` or `--string='<some-json>'`, and the default action is `load`.

#### String loading example

```
python3 __init__.py --string='[1, 2, {"three": 4}]' --action=load
```
output:
```
[1, 2, {b'three': 4}]
```

#### String w/ specific path loading example

```
python3 __init__.py --string='[1, 2, {"three": 4}]' --path 2.three
```
output:
```
{
  "2.three": 4
}
```

#### String parsing example
```
python3 __init__.py --string='[1, 2, {"three": 4}]' --action=parse
```
output:
```
ARRAY_OPEN None
ARRAY_VALUE_NUMBER 1
ARRAY_VALUE_NUMBER 2
OBJECT_OPEN None
OBJECT_KEY b'three'
OBJECT_VALUE_NUMBER 4
OBJECT_CLOSE None
ARRAY_CLOSE None
```

## Parser Theater

Running `python3 theater.py` will launch a local web server/application that provides a UI for observing the parser in action. I can imagine many more features and am toying with the idea of turning this web server + app framework + visibility / control of instrumented Python object into its own project.

![parser-theater](https://user-images.githubusercontent.com/585182/103412551-a64eb480-4b43-11eb-977a-de483f0f7022.gif)
