#!/usr/bin/env python3
"""Fetch one mesh's surface volume or ink maps from the eligible-scroll atlas.

Standalone: copy this file anywhere. Only the standard library is needed to download;
`zarr` is needed to open a surface volume as an array.

    python atlas.py list --scroll PHerc0813 --ink-pass
    python atlas.py get PHerc0813 z13088_w040 --out ./atlas
    python atlas.py ink PHerc0813 z13088_w040 --tag soup42_early3 --out ./atlas

    from atlas import meshes, fetch_surface_volume, open_surface
    row = [m for m in meshes() if m["ink_pass_v1"] == "True"][0]
    vol = open_surface(fetch_surface_volume(row["scroll"], row["mesh"], "./atlas"))
    vol.shape        # (31, H, W) uint8, plane 15 is the mesh surface
"""
import argparse, csv, io, json, os, pathlib, sys, tarfile, urllib.request

REPO = "rodriguescarson/eligible-scroll-atlas-renders"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main"
API = f"https://huggingface.co/api/datasets/{REPO}"
MANIFEST_URL = "https://raw.githubusercontent.com/rodriguescarson/eligible-scroll-atlas/main/data/manifest.csv"


def meshes(scroll=None, ink_pass=None):
    """All 340 published meshes with their gate values and model scores."""
    local = pathlib.Path(__file__).resolve().parent.parent / "data/manifest.csv"
    text = local.read_text() if local.exists() else _get(MANIFEST_URL).decode()
    rows = list(csv.DictReader(io.StringIO(text)))
    if scroll:
        rows = [r for r in rows if r["scroll"] == scroll]
    if ink_pass:
        rows = [r for r in rows if r["ink_pass_v1"] == "True"]
    return rows


def _get(url):
    with urllib.request.urlopen(url) as response:
        return response.read()


def _download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    with urllib.request.urlopen(url) as response, open(destination, "wb") as fh:
        while chunk := response.read(1 << 20):
            fh.write(chunk)
    return destination


def fetch_surface_volume(scroll, mesh, out="."):
    """Download and unpack one mesh's surface volume. Returns the .zarr path."""
    out = pathlib.Path(out) / scroll / mesh
    existing = sorted(out.glob("**/*.zarr"))
    if existing:
        return existing[0]
    tar = _download(f"{BASE}/{scroll}/{mesh}/surface-volumes.tar", out / "surface-volumes.tar")
    with tarfile.open(tar) as archive:
        archive.extractall(out)
    tar.unlink()
    return sorted(out.glob("**/*.zarr"))[0]


def open_surface(path):
    """Open a surface volume as a (31, H, W) uint8 array. Plane 15 is the mesh surface."""
    import zarr
    node = zarr.open(str(path), mode="r")
    return node["0"] if hasattr(node, "keys") and "0" in node else node


def ink_map_names(scroll, mesh):
    """Filenames in this mesh's ink-detection folder (the volume id varies by scroll).

    The few meshes that passed the pre-registered screens have their maps withheld: their
    imagery goes to the Scroll Prize team privately before any public statement. Their
    surface volumes and scores are public; see `maps_held` in data/manifest.csv.
    """
    url = f"{API}/tree/main/{scroll}/{mesh}/ink-detection"
    try:
        return [entry["path"].split("/")[-1] for entry in json.loads(_get(url)) if entry["type"] == "file"]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise FileNotFoundError(
                f"no published ink maps for {scroll}/{mesh}. Screen passers are held back under the "
                f"pre-registration (maps_held in data/manifest.csv); their surface volume and scores are public."
            ) from None
        raise


def fetch_ink_map(scroll, mesh, tag="soup42_early3", reverse=False, preview=False, out="."):
    """Download one raw ink_9um probability map (uint8 tif), or its ds8 jpg preview."""
    suffix = ("_reverse" if reverse else "") + ("-ds8.jpg" if preview else ".tif")
    wanted = [n for n in ink_map_names(scroll, mesh) if f"ink9um-{tag}" in n and n.endswith(suffix)]
    if not wanted:
        raise FileNotFoundError(f"no {tag}{suffix} for {scroll}/{mesh}")
    name = wanted[0]
    return _download(f"{BASE}/{scroll}/{mesh}/ink-detection/{name}", pathlib.Path(out) / scroll / mesh / name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    lst = sub.add_parser("list", help="print meshes as TSV")
    lst.add_argument("--scroll"); lst.add_argument("--ink-pass", action="store_true")
    for name, helptext in (("get", "download a surface volume"), ("ink", "download an ink map")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("scroll"); p.add_argument("mesh"); p.add_argument("--out", default=".")
        if name == "ink":
            p.add_argument("--tag", default="soup42_early3"); p.add_argument("--reverse", action="store_true")
            p.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "list":
        rows = meshes(args.scroll, args.ink_pass)
        print("scroll\tmesh\tarea_cm2\thecate_rank\tink_pass_v1")
        for r in rows:
            print(f"{r['scroll']}\t{r['mesh']}\t{r['area_cm2']}\t{r['hecate_rank']}\t{r['ink_pass_v1']}")
        print(f"# {len(rows)} meshes", file=sys.stderr)
    elif args.command == "get":
        print(fetch_surface_volume(args.scroll, args.mesh, args.out))
    else:
        print(fetch_ink_map(args.scroll, args.mesh, args.tag, args.reverse, args.preview, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
