# dovwms

[![Release](https://img.shields.io/github/v/release/zawadzkim/dovwms)](https://img.shields.io/github/v/release/zawadzkim/dovwms)
[![Build status](https://img.shields.io/github/actions/workflow/status/zawadzkim/dovwms/main.yml?branch=main)](https://github.com/zawadzkim/dovwms/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/zawadzkim/dovwms/branch/main/graph/badge.svg)](https://codecov.io/gh/zawadzkim/dovwms)
[![Commit activity](https://img.shields.io/github/commit-activity/m/zawadzkim/dovwms)](https://img.shields.io/github/commit-activity/m/zawadzkim/dovwms)
[![License](https://img.shields.io/github/license/zawadzkim/dovwms)](https://img.shields.io/github/license/zawadzkim/dovwms)

Simple client for DOV WMS services.

Lightweight Python client to fetch soil texture and elevation data from
Belgian WMS services (DOV and Geopunt). The package provides convenience
clients for the two services and a small helper to fetch a soil profile at
a point location.

- Repository: <https://github.com/zawadzkim/dovwms/>
- Docs: <https://zawadzkim.github.io/dovwms/>

## Features

- Fetch clay/silt/sand fractions for standard depth layers from DOV WMS
- Fetch elevation from Geopunt WMS
- Small, testable API with helpers for convenience and easy mocking

## Installation

Requires Python 3.11+. Install from PyPI (when released):

```bash
pip install dovwms
```

For development from source (recommended):

```bash
git clone git@github.com:zawadzkim/dovwms.git
cd dovwms
make install   # installs dev dependencies (uses poetry or pip in Makefile)
```

You can also install the package in editable mode:

```bash
python -m pip install -e .
```

## Quickstart

Simple usage with the convenience function:

```python
from dovwms import get_profile_from_dov

# Coordinates in the default CRS (EPSG:31370 / Lambert72)
profile = get_profile_from_dov(247172.56, 204590.58, fetch_elevation=True)

if profile is None:
    print("Could not fetch profile")
else:
    # profile is a dict with keys 'layers' (list) and optional 'elevation'
    print("Elevation:", profile.get('elevation'))
    for layer in profile['layers']:
        print(layer['name'], layer['sand_content'], layer['silt_content'], layer['clay_content'])
```

Using the low-level clients:

```python
from dovwms import DOVClient, GeopuntClient
from shapely.geometry import Point

client = DOVClient()
pt = Point(247172.56, 204590.58)

# Fetch texture layers
profile = client.fetch_profile(pt, fetch_elevation=False)

# Fetch elevation directly
g = GeopuntClient()
elev = g.fetch_elevation(pt)
```

Notes

- `fetch_profile` returns a dict with a `layers` key (list of layer dicts).
- Use the module-level loggers to enable/inspect runtime information; the
  library does not configure logging handlers by default.

## Testing

Run the test suite with pytest. Development dependencies include pytest.

```bash
make test
# or
pytest -q
```

Integration tests that require network access are marked `integration` and
can be executed explicitly:

```bash
pytest -q -m integration
```

## Contributing

Contributions are welcome. Please open issues or pull requests. Follow the
project's code style and run tests before submitting changes.

## License

MIT

---

Repository scaffolded from fpgmaas/cookiecutter-poetry.
