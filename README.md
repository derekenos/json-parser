# jsonite

A hilarious foray into the world of streaming parsers. I laughed, I cried, it took a day.

## Purpose

I wrote this so that I could parse chunky API responses on a memory-constrained ESP32 running Micropython.
I probably could've used one of the dozens of existing such libraries but that's not fun for me.
I recently [made my own AAA battery holder](https://photos.google.com/share/AF1QipPe44ojFa2bh5PcLL6LHTBP4V0Hmqc8Uv1vhxuDJGkwDnw3l-dGW8qsa5TYxH21OA/photo/AF1QipPfLvxKoX4zsl0mPSUMkvUw3w62IRvFTAYPhoad?key=VFY0OE95SjBJRjdBRUxrTFlmWmtvVGp4bHNtb0hR) out of laser-cut wood and bolts - I'm not about to start using "libraries" in my personal projects.

## Usage

1. Instantiate the `Parser` with a binary stream

```
from jsonite import Parser

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
        [ b'@context', 0 ],
        [ b'@context', 1, b'@version' ]
    ))

    next(gen)
    # ([b'@context', 0], b'https://geojson.org/geojson-ld/geojson-context.jsonld')

    next(gen)
    # ([b'@context', 1, b'@version'], b'1.1')
    ```

## Deficiencies

- Deals entirely in byte strings / doesn't support any decoding
- `yield_paths()` only yields scalar values (i.e. strings, numbers, nulls) and not containers (i.e. arrays and objects)
- ... probably a ton of other things that are outside my current use-case ...
