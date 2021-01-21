# Tools for converting detector mask

Two scripts for converting detector mask from HD5 to CrystFEL geometry file
and vice versa:

```bash
xwiz-mask-hd52geom <hd5_file> <geometry_file> [<optional arguments>]
xwiz-mask-geom2hd5 <geometry_file> <hd5_file> [<optional arguments>]
```

HD5 and geometry files are required positional arguments, and optional
arguments include:

```text
 -r, --replace                     Overwrite / comment out existing mask
 -a, --add                         Add converted mask to the existing
 -p <value>, --path-hd5 <value>    Path to the mask in HD5 file
 -e <value>, --entry-hd5 <value>   Mask entry number
 -i, --invert                      Invert the mask read from / written to HDF5
 -d <value>, --detector <value>    Name of the detector
 -t <value>, --type <value>        Type of the data
```

If \<detector\> and / or \<type\> option is skipped by the user - script will
try to estimate it from HD5 and / or geometry file.
